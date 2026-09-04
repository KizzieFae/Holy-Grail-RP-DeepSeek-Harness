/**
 * Bounded live validation for Issue #109 — player decomposition output contract.
 * Run from v2/rp_runtime: node scripts/issue109-live-validation.mjs
 */
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

import { createHolyGrailRpContext } from '../src/bootstrap.mjs';
import { createDomainApiClient } from '../src/lib/domain-api-client.mjs';
import { deepseekInferenceProfile } from '../src/lib/inference-profile.mjs';
import { parsePlayerDecompositionEnvelope } from '../src/lib/perceptual-visibility-parse.mjs';
import { runPlayerDecompositionPhase } from '../src/plugins/hg-phase-executors/player-decomposition-phase.mjs';
import { startDomainApi } from '../tests/helpers/domain-api.mjs';

const CASES = [
  {
    id: 'public_speech',
    content: '"Good evening," she said with a small bow.',
    description: 'short public speech',
  },
  {
    id: 'mixed_public_internal',
    content: 'She waved to Ayame. *No one else can know how nervous I am right now.*',
    description: 'mixed public action + internal cognition',
  },
  {
    id: 'action_and_speech',
    content: 'She set the tray down carefully. "I brought tea," she offered.',
    description: 'multi-span action + speech for source accounting',
  },
];

function summarizeEvidence(attempt) {
  const instruction = (attempt.request?.contributions ?? []).find(
    (item) => item.source_kind === 'inference_instruction',
  );
  return {
    evidence_id: attempt.evidence_id,
    manifest_id: attempt.correlation?.manifest_id ?? attempt.request?.manifest_id ?? null,
    attempt_index: attempt.correlation?.attempt_index ?? null,
    prior_attempt_id: attempt.correlation?.prior_attempt_id ?? null,
    instruction_present: Boolean(instruction),
    instruction_markers: {
      output_format: /OUTPUT FORMAT — return ONLY valid JSON/.test(instruction?.content ?? ''),
      perceptual_visibility: /"perceptual_visibility"/.test(instruction?.content ?? ''),
      source_accounting: /"source_accounting"/.test(instruction?.content ?? ''),
    },
    user_prompt_has_player_source: /PLAYER SOURCE:/.test(attempt.request?.user_instruction?.text ?? ''),
    finish: attempt.response?.finish?.kind ?? null,
    assistant_prefix: String(attempt.response?.assistant_text ?? '').trim().slice(0, 80),
  };
}

async function validateWithDomain(api, sessionId, content, decomposition) {
  const entry = await api.recordUserTurn({
    hg_session_id: sessionId,
    content,
    speaker: 'Kizzie',
    player_decomposition: decomposition,
  });
  const metadata = entry.metadata ?? {};
  const pvr = metadata.perceptual_visibility ?? {};
  const audit = metadata.validation_audit ?? {};
  return {
    validation_status: pvr.validation_status ?? null,
    accepted: Boolean(audit.accepted),
    failure_class: pvr.recovery?.failure_class ?? null,
    unit_count: Array.isArray(pvr.units) ? pvr.units.length : 0,
  };
}

async function main() {
  const evidenceRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'issue109-live-evidence-'));
  const port = 29810 + Math.floor(Math.random() * 100);
  const host = await startDomainApi(port, { withSession: true });
  const baseUrl = host.baseUrl;
  const api = createDomainApiClient(baseUrl);
  const { ctx, phaseExecutors } = await createHolyGrailRpContext({
    domainApi: { baseUrl },
    inference: {
      mountDeepSeek: true,
      executionEvidence: { enabled: true, root: evidenceRoot },
      defaultProfile: deepseekInferenceProfile(),
    },
  });

  const results = [];
  try {
    for (const caseDef of CASES) {
      const session = await api.createSession({
        cast: ['Ayame', 'Kizzie'],
        hg_session_id: `issue109-live-${caseDef.id}`,
      });
      const sessionId = session.hg_session_id;
      const inferenceId = `player-decomposition-live-${caseDef.id}`;
      const phaseResult = await runPlayerDecompositionPhase({
        api,
        runEphemeralInference: phaseExecutors.runEphemeralInference.bind(phaseExecutors),
        hgSessionId: sessionId,
        hgSceneId: sessionId,
        hgRoundId: `issue109-live-round-${caseDef.id}`,
        inferenceId,
        playerContent: caseDef.content,
        modelProfile: deepseekInferenceProfile(),
      });

      const parsed = phaseResult.playerDecomposition?.failure_class
        ? { parseError: phaseResult.playerDecomposition.failure_class }
        : parsePlayerDecompositionEnvelope(JSON.stringify({
          perceptual_visibility: phaseResult.playerDecomposition.perceptual_visibility,
          source_accounting: phaseResult.playerDecomposition.source_accounting,
        }));

      const domainResult = await validateWithDomain(
        api,
        sessionId,
        caseDef.content,
        phaseResult.playerDecomposition,
      );

      const indexPath = path.join(evidenceRoot, sessionId, 'index.json');
      let attempts = [];
      if (fs.existsSync(indexPath)) {
        const index = JSON.parse(fs.readFileSync(indexPath, 'utf8'));
        attempts = (index.attempt_ids ?? [])
          .map((id) => JSON.parse(fs.readFileSync(path.join(evidenceRoot, sessionId, 'attempts', `${id}.json`), 'utf8')))
          .filter((attempt) => attempt.correlation?.role === 'player_decomposition');
      }

      results.push({
        case: caseDef.id,
        description: caseDef.description,
        wiring: attempts.map(summarizeEvidence),
        functional: {
          phase_failure_class: phaseResult.playerDecomposition.failure_class ?? null,
          domain: domainResult,
          parse_ok: !parsed.parseError,
        },
      });
    }
  } finally {
    await ctx.fiber.dispose();
    await host.stop();
  }

  const reportPath = path.join(evidenceRoot, 'issue109-live-report.json');
  fs.writeFileSync(reportPath, JSON.stringify({ results }, null, 2));
  console.log(JSON.stringify({ evidenceRoot, reportPath, results }, null, 2));
}

main().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});
