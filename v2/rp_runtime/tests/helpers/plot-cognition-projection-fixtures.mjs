import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';

import { createDomainApiClient } from '../../src/lib/domain-api-client.mjs';
import { attachCharacterCognitionApiStubs } from './character-cognition-mock.mjs';
import { makeTempSessionsDir, startDomainApi } from './domain-api.mjs';

export const REGENERATION_GUIDANCE = {
  schema: 'hg_regeneration_guidance_v1',
  violation_class: 'basis_leak',
  safe_constraints: ['Do not reveal hidden vault details.'],
  do_not_introduce: ['vault code'],
  affected_dimensions: ['knowledge_boundary'],
};

export function epistemicPass() {
  return JSON.stringify({
    schema: 'hg_epistemic_projection_eval_v1',
    verdict: 'pass',
    rationale: 'no leak detected',
    forensic_rationale: 'no leak detected',
    leak_indicators: [],
  });
}

export function epistemicWithhold() {
  return JSON.stringify({
    schema: 'hg_epistemic_projection_eval_v1',
    verdict: 'withhold',
    rationale: 'withhold advisory',
    forensic_rationale: 'withhold advisory',
    leak_indicators: ['basis_leak'],
  });
}

export function epistemicRewriteRequired() {
  return JSON.stringify({
    schema: 'hg_epistemic_projection_eval_v1',
    verdict: 'rewrite_required',
    rationale: 'rewrite needed',
    forensic_rationale: 'rewrite needed',
    leak_indicators: ['basis_leak'],
    regeneration_guidance: REGENERATION_GUIDANCE,
  });
}

export function epistemicMalformed() {
  return JSON.stringify({ schema: 'hg_epistemic_projection_eval_v1', verdict: 'not_a_real_verdict' });
}

export function seedEmptyOverlayStore(sessionsDir, scopeId) {
  const overlayDir = path.join(sessionsDir, '_plot_cognition_overlay');
  fs.mkdirSync(overlayDir, { recursive: true });
  const safe = scopeId.replace(/\//g, '_').replace(/\\/g, '_');
  const payload = {
    store_schema: 'hg_plot_cognition_overlay_store_v1',
    plot_cognition_scope_id: scopeId,
    store_revision: 1,
    assimilated_through_domain_commit_id: null,
    goals: {},
    pressures: {},
    active_frame: null,
  };
  fs.writeFileSync(path.join(overlayDir, `${safe}.json`), JSON.stringify(payload));
}

export function seedCharacterOverlayGoal(sessionsDir, scopeId, {
  characterId = 'Alice',
  direction = 'Find the key quietly.',
} = {}) {
  const overlayDir = path.join(sessionsDir, '_plot_cognition_overlay');
  fs.mkdirSync(overlayDir, { recursive: true });
  const safe = scopeId.replace(/\//g, '_').replace(/\\/g, '_');
  const goalId = `hg-plot-goal-${crypto.randomUUID()}`;
  const payload = {
    store_schema: 'hg_plot_cognition_overlay_store_v1',
    plot_cognition_scope_id: scopeId,
    store_revision: 1,
    assimilated_through_domain_commit_id: null,
    goals: {
      [goalId]: {
        schema: 'hg_plot_goal_v1',
        goal_id: goalId,
        intended_direction: direction,
        basis_note: null,
        basis_refs: [{ ref_kind: 'character_card', stable_ref: `${characterId.toLowerCase()}:goals` }],
        applicability: {
          applicability_kind: 'character',
          primary_character_id: characterId,
          involved_character_ids: [characterId],
        },
        planning_horizon: 'MEDIUM',
        creation_provenance: { source: 'storyteller' },
        lineage: {},
        activity_state: 'active',
      },
    },
    pressures: {},
    active_frame: null,
  };
  fs.writeFileSync(path.join(overlayDir, `${safe}.json`), JSON.stringify(payload));
}

export async function startProjectionDomainHost(t, options = {}) {
  const sessionsDir = options.sessionsDir ?? makeTempSessionsDir();
  const dataDir = options.dataDir ?? path.join(path.dirname(sessionsDir), 'data-root');
  const forensicsDir = options.forensicsDir ?? path.join(dataDir, 'plot_cognition_forensics');
  fs.mkdirSync(sessionsDir, { recursive: true });
  fs.mkdirSync(forensicsDir, { recursive: true });
  const port = options.port ?? (50765 + Math.floor(Math.random() * 1000));
  const hostEnv = {
    HG_DATA_DIR: dataDir,
    HG_SESSIONS_DIR: sessionsDir,
    HG_PLOT_COGNITION_FORENSICS_DIR: forensicsDir,
    ...(options.hostEnv ?? {}),
  };
  const host = await startDomainApi(port, { sessionsDir, hostEnv });
  const baseUrl = host.baseUrl;
  t.after(() => host.stop());
  const api = createDomainApiClient(baseUrl);
  return { host, baseUrl, api, sessionsDir, dataDir, forensicsDir, port, hostEnv };
}

export async function setupProjectionSession(api, sessionsDir, {
  cast = ['Alice', 'Bob'],
  scopeId = `scope-proj-${crypto.randomUUID()}`,
  withCharacterGoal = true,
  characterId = 'Alice',
} = {}) {
  const session = await api.createSession({ cast, memory_scope_id: scopeId });
  if (withCharacterGoal) {
    seedCharacterOverlayGoal(sessionsDir, scopeId, { characterId });
  } else {
    seedEmptyOverlayStore(sessionsDir, scopeId);
  }
  await api.finalizePlotCognitionReconciliation({ hg_scene_id: session.hg_scene_id });
  const round = await api.startRound({ hg_scene_id: session.hg_scene_id });
  return {
    session,
    scopeId,
    hgSceneId: session.hg_scene_id,
    hgRoundId: round.hg_round_id,
    turnIndex: Number(round.turn_index ?? 0),
  };
}

export function createTrackingInference(mockResponses = []) {
  const calls = [];
  async function runEphemeralInference({
    inferenceId,
    manifest,
    mockResponses: localMocks = [],
    evidenceContext = {},
    ...rest
  }) {
    const queue = localMocks.length ? localMocks : mockResponses;
    const raw = queue[calls.length] ?? queue.at(-1) ?? '';
    calls.push({
      inferenceId,
      inferenceKind: evidenceContext.inferenceKind ?? null,
      evaluationPassId: evidenceContext.evaluationPassId ?? null,
      regenerationPrepareId: evidenceContext.regenerationPrepareId ?? null,
      parentInferenceId: evidenceContext.parentInferenceId ?? null,
      manifestContributionCount: manifest?.contributions?.length ?? 0,
      ...rest,
    });
    return {
      failed: false,
      raw,
      evidenceId: `ev-${inferenceId}`,
      inferenceSessionId: `sess-${inferenceId}`,
      trace: {},
    };
  }
  return { runEphemeralInference, calls };
}

export function createFailingInference() {
  const calls = [];
  async function runEphemeralInference(args) {
    calls.push(args);
    return {
      failed: true,
      raw: '',
      evidenceId: `ev-fail-${args.inferenceId}`,
      inferenceSessionId: `sess-fail-${args.inferenceId}`,
      trace: {},
    };
  }
  return { runEphemeralInference, calls };
}

export function instrumentProjectionApi(api) {
  const order = [];
  const wrap = (name, fn) => async (...args) => {
    order.push(name);
    return fn(...args);
  };
  const instrumented = {
    ...api,
    _order: order,
    preparePlotCognitionProjection: wrap('prepare', api.preparePlotCognitionProjection.bind(api)),
    registerPlotCognitionProjectionSemanticResult: wrap(
      'register',
      api.registerPlotCognitionProjectionSemanticResult.bind(api),
    ),
    preparePlotCognitionProjectionRegeneration: wrap(
      'regen_prepare',
      api.preparePlotCognitionProjectionRegeneration.bind(api),
    ),
    finalizePlotCognitionProjectionRegeneration: wrap(
      'regen_finalize',
      api.finalizePlotCognitionProjectionRegeneration.bind(api),
    ),
    finalizePlotCognitionProjection: wrap('finalize', api.finalizePlotCognitionProjection.bind(api)),
    prepareCharacterContext: wrap('character_context', api.prepareCharacterContext.bind(api)),
  };
  return attachCharacterCognitionApiStubs(instrumented);
}

export function readForensicIndex(forensicsDir, scopeId) {
  const safe = scopeId.replace(/\//g, '_').replace(/\\/g, '_');
  const indexPath = path.join(forensicsDir, safe, 'index.json');
  if (!fs.existsSync(indexPath)) return null;
  return JSON.parse(fs.readFileSync(indexPath, 'utf8'));
}

export function readExecutionAttempts(dataDir, hgSessionId) {
  const root = path.join(dataDir, 'execution_evidence', hgSessionId);
  const indexPath = path.join(root, 'index.json');
  if (!fs.existsSync(indexPath)) return [];
  const index = JSON.parse(fs.readFileSync(indexPath, 'utf8'));
  return (index.attempt_ids ?? []).map((evidenceId) => JSON.parse(
    fs.readFileSync(path.join(root, 'attempts', `${evidenceId}.json`), 'utf8'),
  ));
}
