/**
 * Bounded live validation for Issue #110 — opening segmentation inference policy + OPENING contract.
 * Run from v2/rp_runtime: node scripts/issue110-live-validation.mjs
 */
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

import { HolyGrailApplicationClient } from '../src/application/hg-application-client.mjs';
import { createDomainApiClient } from '../src/lib/domain-api-client.mjs';
import { modelProfileForInferenceKind, resolveApplicationRoleProfiles } from '../src/application/application-settings.mjs';
import { HG_DEEPSEEK_DEFAULT_MODEL } from '../src/lib/inference-profile.mjs';

const CASES = [
  {
    id: 'ayame_household_entry_evaluation',
    sceneTemplateId: 'ayame_household_entry_evaluation',
    characters: ['ayame', 'kizzie'],
    roleAssignments: { ayame: 'host', kizzie: 'applicant' },
    description: 'ordinary control opener',
  },
  {
    id: 'marlene_willow_dorm_omega_misassignment',
    sceneTemplateId: 'marlene_willow_dorm_omega_misassignment',
    characters: ['marlene', 'willow', 'kizzie'],
    roleAssignments: {
      marlene: 'alpha_roommate_marlene',
      willow: 'alpha_roommate_willow',
      kizzie: 'misassigned_omega_student',
    },
    description: 'long stress opener',
  },
];

function summarizeAttempt(attempt) {
  const usage = attempt.response?.usage ?? {};
  return {
    evidence_id: attempt.evidence_id,
    attempt_index: attempt.correlation?.attempt_index ?? null,
    finish: attempt.response?.finish?.kind ?? null,
    output_tokens: usage.outputTokens ?? usage.output_tokens ?? null,
    reasoning_tokens: usage.reasoningTokens ?? usage.reasoning_tokens ?? null,
    effective_thinking: attempt.request?.effective_thinking ?? attempt.response?.effective_thinking ?? null,
    reasoning_effort: attempt.request?.reasoning_effort ?? null,
    assistant_len: String(attempt.response?.assistant_text ?? '').trim().length,
    assistant_prefix: String(attempt.response?.assistant_text ?? '').trim().slice(0, 120),
  };
}

function scopeSummary(units = []) {
  const scopes = new Set();
  const kinds = new Set();
  let speechWithoutBeat = 0;
  for (const unit of units) {
    kinds.add(unit.kind);
    scopes.add(unit.recipients?.scope ?? 'unknown');
    if (unit.kind === 'speech' && unit.source_provenance?.beat_index == null) {
      speechWithoutBeat += 1;
    }
  }
  return {
    unit_count: units.length,
    kinds: [...kinds],
    scopes: [...scopes],
    speech_without_beat_index: speechWithoutBeat,
  };
}

async function main() {
  const evidenceRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'issue110-live-evidence-'));
  const opening = resolveApplicationRoleProfiles({
    inferenceMode: 'live',
    roleRouting: 'simple',
    model: HG_DEEPSEEK_DEFAULT_MODEL,
  }).opening;
  const segmentationProfile = modelProfileForInferenceKind(opening, 'opening_segmentation');
  const profileCheck = {
    reasoningEffort: segmentationProfile.reasoningEffort,
    maxTokens: segmentationProfile.maxTokens,
  };

  const client = new HolyGrailApplicationClient({
    inferenceMode: 'live',
    inference: {
      executionEvidence: { enabled: true, root: evidenceRoot },
    },
  });
  await client.start();

  const results = [];
  try {
    for (const caseDef of CASES) {
      const openers = await client.listTemplateOpeners(caseDef.sceneTemplateId);
      const created = await client.createSession({
        characters: caseDef.characters,
        sceneTemplateId: caseDef.sceneTemplateId,
        roleAssignments: caseDef.roleAssignments,
        opening: { mode: 'template', opener_id: openers[0].opener_id },
      });

      const api = createDomainApiClient(client.supervisor.domainHostUrl);
      const history = await api.getSessionHistory(created.hg_session_id);
      const openingEntry = history.entries.find((entry) => entry.kind === 'opening');
      const units = openingEntry?.metadata?.perceptual_visibility?.units ?? [];

      const indexPath = path.join(evidenceRoot, created.hg_session_id, 'index.json');
      let attempts = [];
      if (fs.existsSync(indexPath)) {
        const index = JSON.parse(fs.readFileSync(indexPath, 'utf8'));
        attempts = (index.attempt_ids ?? [])
          .map((id) => JSON.parse(
            fs.readFileSync(path.join(evidenceRoot, created.hg_session_id, 'attempts', `${id}.json`), 'utf8'),
          ))
          .filter((attempt) => attempt.correlation?.role === 'opening_segmentation');
      }

      results.push({
        case: caseDef.id,
        description: caseDef.description,
        profile_check: profileCheck,
        wiring: attempts.map(summarizeAttempt),
        functional: {
          nvr_attached: units.length > 0,
          validation_status: openingEntry?.metadata?.perceptual_visibility?.validation_status ?? null,
          semantic: scopeSummary(units),
          canon_preserved: Boolean(openingEntry?.content?.length),
        },
      });
    }
  } finally {
    await client.stop();
  }

  const reportPath = path.join(evidenceRoot, 'issue110-live-report.json');
  fs.writeFileSync(reportPath, JSON.stringify({ profile_check: profileCheck, results }, null, 2));
  console.log(JSON.stringify({ evidenceRoot, reportPath, profile_check: profileCheck, results }, null, 2));
}

main().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});
