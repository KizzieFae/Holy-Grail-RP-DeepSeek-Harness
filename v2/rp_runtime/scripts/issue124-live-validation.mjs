/**
 * Bounded live validation for Issue #124 — semantic-only PVR with uncapped tokens.
 * Run from v2/rp_runtime: node scripts/issue124-live-validation.mjs
 */
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

import { createHolyGrailRpContext } from '../src/bootstrap.mjs';
import { createDomainApiClient } from '../src/lib/domain-api-client.mjs';
import { deepseekInferenceProfile } from '../src/lib/inference-profile.mjs';
import { modelProfileForInferenceKind } from '../src/application/application-settings.mjs';
import { runPlayerDecompositionPhase } from '../src/plugins/hg-phase-executors/player-decomposition-phase.mjs';
import { startDomainApi } from '../tests/helpers/domain-api.mjs';

const SEIZA_JAPAN_TURN =
  'Kizzie moved to the cushion, lowering to it, sitting in a formal sieza position. '
  + 'they were not in Japan, but hold habits died hard. '
  + '"A string of bad luck, if I am being honest-nothing that was my fault, mind you, but..." '
  + 'she hesittated, looking up. '
  + '"Have you ever had a time in your life when the entire road has been destroyed and you realized that there was another path, one you would not have even considered before? '
  + 'Some people see misfortune, I see an opportunity to reinvent."';

const MODEL_PROFILE = modelProfileForInferenceKind(
  deepseekInferenceProfile({ reasoningEffort: 'low' }),
  'player_decomposition',
  {},
  {},
);

async function main() {
  const evidenceRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'issue124-live-'));
  const domainApi = await startDomainApi();
  const ctx = await createHolyGrailRpContext({ evidenceRoot });
  const api = createDomainApiClient(domainApi.baseUrl);

  const created = await api.createSession({
    cast: ['Ayame', 'Kizzie', 'Harley', 'Celina'],
    user_persona_id: 'Kizzie',
  });
  const hgSessionId = created.hg_scene_id ?? created.hg_session_id;

  const inferenceId = 'issue124-live-complex-dense';
  const result = await runPlayerDecompositionPhase({
    api,
    runEphemeralInference: ctx.runEphemeralInference,
    hgSessionId,
    hgSceneId: hgSessionId,
    hgRoundId: 'issue124-live-round',
    inferenceId,
    playerContent: SEIZA_JAPAN_TURN,
    modelProfile: MODEL_PROFILE,
  });

  const decomposition = result.playerDecomposition ?? {};
  const accepted = Boolean(decomposition.perceptual_visibility?.units?.length);
  const report = {
    experiment: 'issue124_live_semantic_validation',
    generated_at: new Date().toISOString(),
    case_id: 'complex_dense_seiza_japan',
    inference_id: inferenceId,
    max_tokens: MODEL_PROFILE.maxTokens ?? null,
    attempt_count: (decomposition.generation?.attempt_index ?? 0) + 1,
    normalization_accepted: accepted,
    failure_class: decomposition.failure_class ?? null,
    unit_count: decomposition.perceptual_visibility?.units?.length ?? 0,
    normalization_audit: result.normalizationAudit ?? decomposition.generation?.normalization ?? null,
    evidence_id: result.evidenceId ?? null,
  };

  const fixturePath = path.join('tests', 'fixtures', 'issue124-live-validation-report.json');
  fs.writeFileSync(fixturePath, `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify(report, null, 2));
  await domainApi.close?.();
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
