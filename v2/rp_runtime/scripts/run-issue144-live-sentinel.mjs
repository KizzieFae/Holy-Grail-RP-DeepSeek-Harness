/**
 * Issue #144 bounded live Storyteller orientation sentinel (single attempt).
 */
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { createHolyGrailRpContext } from '../src/bootstrap.mjs';
import { deepseekInferenceProfile } from '../src/lib/inference-profile.mjs';
import { LIVE_INFERENCE_TRANSPORT_PROMPT } from '../src/lib/live-inference-prompts.mjs';
import { createDomainApiClient } from '../src/lib/domain-api-client.mjs';
import { startDomainApi } from '../tests/helpers/domain-api.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '../../..');
const CANDIDATE_SHA = process.env.ISSUE144_CANDIDATE_SHA ?? 'unknown';

async function main() {
  if (!process.env.DEEPSEEK_API_KEY?.trim()) {
    throw new Error('DEEPSEEK_API_KEY not set');
  }

  const gateRoot = path.join(
    REPO_ROOT,
    'data',
    'issue144_live_sentinel',
    new Date().toISOString().replace(/[:.]/g, '-'),
  );
  const sessionsDir = path.join(gateRoot, 'sessions');
  fs.mkdirSync(sessionsDir, { recursive: true });
  const previous = {
    HG_DATA_DIR: process.env.HG_DATA_DIR,
    HG_EXECUTION_EVIDENCE: process.env.HG_EXECUTION_EVIDENCE,
    HG_EXECUTION_EVIDENCE_DIR: process.env.HG_EXECUTION_EVIDENCE_DIR,
  };
  process.env.HG_DATA_DIR = gateRoot;
  process.env.HG_EXECUTION_EVIDENCE = 'on';
  process.env.HG_EXECUTION_EVIDENCE_DIR = path.join(gateRoot, 'execution_evidence');
  fs.mkdirSync(process.env.HG_EXECUTION_EVIDENCE_DIR, { recursive: true });

  const host = await startDomainApi(undefined, { sessionsDir });
  const api = createDomainApiClient(host.baseUrl);
  const { ctx, orchestrator } = await createHolyGrailRpContext({
    domainApi: { baseUrl: host.baseUrl },
    inference: {
      mountDeepSeek: true,
      defaultProfile: deepseekInferenceProfile({ reasoningEffort: 'low' }),
    },
  });

  const result = await orchestrator.runRound({
    domainApi: { baseUrl: host.baseUrl },
    session: { mode: 'create', cast: ['Mara', 'Jon'] },
    skipPlotCognitionOrchestration: true,
    storytellerAllowDeterministicFallback: false,
    roleProfiles: {
      storyteller: deepseekInferenceProfile({ reasoningEffort: 'low' }),
      director: deepseekInferenceProfile({ reasoningEffort: 'low' }),
    },
    mockDirectorResponses: [JSON.stringify({
      next_actor: 'Mara',
      end_round: true,
      reason: 'Stop after storyteller probe.',
      environment_event: '',
      tension_shift: 'steady',
    })],
  });

  await ctx.fiber.dispose();
  await host.stop();

  const storyteller = result.storyteller ?? {};
  const skipped = result.scene_events?.find((event) => event.type === 'hg/storyteller-skipped');
  const completed = result.scene_events?.find((event) => event.type === 'hg/storyteller-completed');

  let orientationEvidence = null;
  const evidenceRoot = process.env.HG_EXECUTION_EVIDENCE_DIR;
  const sessionId = result.hg_session_id;
  if (sessionId && fs.existsSync(path.join(evidenceRoot, sessionId, 'index.json'))) {
    const index = JSON.parse(
      fs.readFileSync(path.join(evidenceRoot, sessionId, 'index.json'), 'utf8'),
    );
    const orientationAttemptId = index.ni?.by_round?.[result.hg_round_id]
      ?.[`inf-storyteller-${result.hg_round_id}`]?.storyteller_orientation
      ?? (index.attempts ?? [])
        .find((item) => item.inference_kind === 'storyteller_orientation')?.evidence_id;
    if (orientationAttemptId) {
      const attemptPath = path.join(
        evidenceRoot,
        sessionId,
        'attempts',
        `${orientationAttemptId}.json`,
      );
      if (fs.existsSync(attemptPath)) {
        orientationEvidence = JSON.parse(fs.readFileSync(attemptPath, 'utf8'));
      }
    }
  }

  let prepareContract = null;
  try {
    const sceneId = result.hg_scene_id;
    const roundId = result.hg_round_id;
    if (sceneId && roundId) {
      const prepared = await api.prepareStorytellerOrientationContext({
        hg_scene_id: sceneId,
        hg_round_id: roundId,
        inference_id: 'inf-issue144-evidence',
      });
      const instructions = (prepared.contributions ?? []).filter(
        (item) => item.source_kind === 'inference_instruction',
      );
      const structural = instructions.find((item) =>
        String(item.contribution_id).includes('storyteller_orientation_response_contract'));
      prepareContract = {
        manifest_id: prepared.manifest_id,
        contribution_ids: instructions.map((item) => item.contribution_id),
        structural_provenance: structural?.provenance ?? null,
        structural_content_preview: String(structural?.content ?? '').slice(0, 1200),
      };
    }
  } catch {
    prepareContract = null;
  }

  const orientationAccepted = orientationEvidence?.decision?.storyteller_orientation?.accepted;
  const orientationReason = orientationEvidence?.decision?.storyteller_orientation?.reason;

  const report = {
    schema: 'issue144_live_sentinel_report_v1',
    candidate_sha: CANDIDATE_SHA,
    provider: 'deepseek-official',
    model: 'deepseek-v4-flash',
    reasoning: 'low',
    dsh_transport_prompt: LIVE_INFERENCE_TRANSPORT_PROMPT,
    prepare_contract: prepareContract,
    orientation_evidence_id: orientationEvidence?.evidence_id ?? null,
    raw_orientation_output: orientationEvidence?.raw_output ?? null,
    orientation_finalize: {
      accepted: orientationAccepted ?? null,
      reason: orientationReason ?? null,
    },
    storyteller_round: storyteller,
    skipped_event: skipped?.data ?? null,
    completed_event: completed?.data ?? null,
    success_gate: {
      orientation_accepted: orientationAccepted === true,
      storyteller_bound: storyteller.bound === true,
      passed: orientationAccepted === true && storyteller.bound === true,
    },
    gate_root: gateRoot,
    evidence_anchors: {
      hg_session_id: result.hg_session_id ?? null,
      hg_round_id: result.hg_round_id ?? null,
      orientation_evidence_id: orientationEvidence?.evidence_id ?? null,
      assessment_evidence_id: storyteller.assessment_evidence_id ?? null,
    },
  };

  const outPath = path.join(gateRoot, 'issue144-live-sentinel-report.json');
  fs.writeFileSync(outPath, `${JSON.stringify(report, null, 2)}\n`, 'utf8');
  fs.writeFileSync(
    path.join(gateRoot, 'round-result.json'),
    `${JSON.stringify(result, null, 2)}\n`,
    'utf8',
  );

  for (const [key, value] of Object.entries(previous)) {
    if (value === undefined) delete process.env[key];
    else process.env[key] = value;
  }

  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
  if (!report.success_gate.passed) {
    process.exitCode = 1;
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
