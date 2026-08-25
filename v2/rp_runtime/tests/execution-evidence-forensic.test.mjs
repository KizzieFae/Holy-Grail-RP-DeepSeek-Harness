import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { createHolyGrailRpContext } from '../src/bootstrap.mjs';
import { buildSemanticQaDecisionFields } from '../src/lib/execution-evidence/semantic-qa-patch.mjs';
import { directorDecisionPatch } from '../src/lib/execution-evidence/phase-decision.mjs';
import { createExecutionEvidenceRecorder } from '../src/lib/execution-evidence/recorder.mjs';
import { ExecutionEvidenceStore } from '../src/lib/execution-evidence/store.mjs';
import { runDirectorPhase } from '../src/plugins/hg-phase-executors/director-phase.mjs';
import {
  startDomainApi,
} from './helpers/domain-api.mjs';
import { findCharacterMoveAttempt } from './helpers/character-cognition-mock.mjs';

const VALID_MOVE = {
  move_schema_version: 2,
  beats: [{ type: 'action', action: 'nods thoughtfully' }],
  motivation: {
    goal: 'acknowledge',
    tactic: 'subtle gesture',
    emotional_driver: 'calm',
    risk_level: 'low',
  },
  semantic_evaluation: { decision: 'no_covered_change' },
};

const VALID_DIRECTOR = {
  next_actor: 'Alice',
  end_round: false,
  reason: 'Alice should speak next.',
  environment_event: '',
  tension_shift: '',
};

function makeTempDataEnv(t) {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-forensic-'));
  const sessionsDir = path.join(dataDir, 'sessions');
  fs.mkdirSync(sessionsDir, { recursive: true });
  const previous = {
    HG_DATA_DIR: process.env.HG_DATA_DIR,
    HG_EXECUTION_EVIDENCE: process.env.HG_EXECUTION_EVIDENCE,
    HG_EXECUTION_EVIDENCE_DIR: process.env.HG_EXECUTION_EVIDENCE_DIR,
  };
  process.env.HG_DATA_DIR = dataDir;
  process.env.HG_EXECUTION_EVIDENCE = 'on';
  delete process.env.HG_EXECUTION_EVIDENCE_DIR;
  t.after(() => {
    for (const [key, value] of Object.entries(previous)) {
      if (value === undefined) delete process.env[key];
      else process.env[key] = value;
    }
    fs.rmSync(dataDir, { recursive: true, force: true });
  });
  return { dataDir, sessionsDir };
}

function readAttempts(dataDir, hgSessionId) {
  const root = path.join(dataDir, 'execution_evidence', hgSessionId);
  const index = JSON.parse(fs.readFileSync(path.join(root, 'index.json'), 'utf8'));
  const attempts = (index.attempt_ids ?? []).map((evidenceId) => JSON.parse(
    fs.readFileSync(path.join(root, 'attempts', `${evidenceId}.json`), 'utf8'),
  ));
  return { index, attempts, root };
}

test('decision.semantic_qa is canonical and root semantic_qa is not written', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-qa-canonical-'));
  const store = new ExecutionEvidenceStore(root);
  const hgSessionId = 'sess-qa-canonical';
  store.writeAttempt({
    evidence_id: 'candidate-1',
    correlation: {
      hg_session_id: hgSessionId,
      hg_round_id: 'round-1',
      role: 'director',
      inference_id: 'inf-director-1',
    },
    request: {},
    response: {},
  });
  store.patchAttempt(hgSessionId, 'candidate-1', {
    decision: {
      role: 'director',
      outcome: 'semantic_rejected_soft',
      semantic_qa: buildSemanticQaDecisionFields({
        evaluationPassId: 'inf-director-1-qa-0',
        evaluationTargetRole: 'director',
        evaluatorEvidenceId: 'eval-1',
        policyAction: 'soft_regen',
        result: {
          overall_result: 'reject_soft',
          findings: [{ dimension: 'dir_reason_coherence', severity: 'soft' }],
        },
      }),
    },
  });
  const attempt = store.readAttempt(hgSessionId, 'candidate-1');
  assert.ok(attempt.decision.semantic_qa);
  assert.equal(attempt.decision.semantic_qa.policy_action, 'soft_regen');
  assert.equal(Object.hasOwn(attempt, 'semantic_qa'), false);
  const index = store.readIndex(hgSessionId);
  assert.ok(index.semantic.qa_by_target_role.director.includes('candidate-1'));
  assert.deepEqual(index.semantic.qa_pass_chains['inf-director-1'], [{
    candidate_evidence_id: 'candidate-1',
    evaluator_evidence_id: 'eval-1',
    evaluation_pass_id: 'inf-director-1-qa-0',
    policy_action: 'soft_regen',
  }]);
  fs.rmSync(root, { recursive: true, force: true });
});

test('directorDecisionPatch includes eligibility on rejected attempts', () => {
  const patch = directorDecisionPatch({
    proposed: { next_actor: 'Zelda' },
    validation: {
      accepted: false,
      validation_class: 'invalid_actor',
      reason: 'Invalid next_actor',
      retryable: true,
    },
    outcome: 'rejected',
    eligibilitySnapshot: {
      eligibility_snapshot_id: 'snap-1',
      eligible_actors: ['Alice', 'Bob'],
      present_characters: ['Alice', 'Bob'],
    },
    participationContext: {
      eligibilitySnapshotId: 'snap-1',
      directorConstraintActor: 'Alice',
    },
    actorsUsedThisRound: [],
  });
  assert.deepEqual(patch.decision.director.eligibility.eligible_actors, ['Alice', 'Bob']);
  assert.equal(patch.decision.director.eligibility.director_constraint_actor, 'Alice');
  assert.equal(patch.decision.director.constraints, undefined);
});

test('participation record indexes and links to character attempt', async (t) => {
  const { dataDir, sessionsDir } = makeTempDataEnv(t);
  const port = 24700 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port, { sessionsDir });
  t.after(() => host.stop());

  const { ctx, orchestrator } = await createHolyGrailRpContext({ domainApi: { baseUrl: host.baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const result = await orchestrator.runRound({
    domainApi: { baseUrl: host.baseUrl },
    session: { mode: 'create', cast: ['Alice'] },
    forcedDesignation: 'Alice',
    mockDirectorResponses: [JSON.stringify({ ...VALID_DIRECTOR, next_actor: 'Bob' })],
    mockCharacterTurnResponses: [[JSON.stringify(VALID_MOVE)]],
  });

  const { index, attempts } = readAttempts(dataDir, result.hg_session_id);
  const participation = attempts.find((entry) => entry.correlation.role === 'participation');
  const character = findCharacterMoveAttempt(attempts);
  assert.ok(participation);
  assert.ok(character);
  assert.equal(attempts.some((entry) => entry.correlation.role === 'director'), false);
  assert.equal(participation.decision.participation.selection_mode, 'direct');
  assert.equal(participation.decision.participation.selected_actor, 'Alice');
  assert.equal(participation.associations.character_evidence_id, character.evidence_id);
  assert.equal(character.associations.participation_evidence_id, participation.evidence_id);
  assert.ok(index.participation_by_round[result.hg_round_id]?.includes(participation.evidence_id));
});

test('director semantic QA writes qa_pass_chains on regeneration path', async () => {
  const api = {
    async prepareDirectorContext() {
      return { manifest_id: 'manifest-director-1', contributions: [] };
    },
    async prepareDirectorSemanticQaContext() {
      return {
        manifest_id: 'manifest-director-qa-1',
        inference_id: 'inf-director-1',
        hg_scene_id: 'scene-1',
        hg_round_id: 'round-1',
        turn_index: 0,
        authority_references: [],
        contributions: [],
      };
    },
    async validateDirectorDecision({ proposed_decision: proposed }) {
      return {
        accepted: true,
        normalized_decision: proposed,
        selected_character_id: proposed?.next_actor ?? 'Alice',
        validation_class: 'accepted',
        reason: '',
        retryable: false,
      };
    },
  };

  const recorder = createExecutionEvidenceRecorder({
    enabled: true,
    root: fs.mkdtempSync(path.join(os.tmpdir(), 'hg-dir-qa-')),
  });
  const semanticResponses = [
    JSON.stringify({
      schema: 'hg_semantic_qa_result_v1',
      evaluation_target_role: 'director',
      evaluation_pass_id: 'inf-director-1-qa-0',
      overall_result: 'reject_soft',
      findings: [{ dimension: 'dir_reason_coherence', severity: 'soft', finding: 'thin', rationale: 'x' }],
    }),
    JSON.stringify({
      schema: 'hg_semantic_qa_result_v1',
      evaluation_target_role: 'director',
      evaluation_pass_id: 'inf-director-1-qa-1',
      overall_result: 'pass',
      findings: [],
    }),
  ];
  let call = 0;
  const result = await runDirectorPhase({
    api,
    trace: { emit() {} },
    sceneAgent: { session: {} },
    sceneSessionId: 'sess-1',
    hgSessionId: 'hg-session-1',
    hgSceneId: 'scene-1',
    hgRoundId: 'round-1',
    directorInferenceId: 'inf-director-1',
    directorAttemptSeed: 0,
    mockDirectorResponses: [
      JSON.stringify({ ...VALID_DIRECTOR, reason: 'first' }),
      JSON.stringify({ ...VALID_DIRECTOR, reason: 'second' }),
    ],
    mockDirectorSemanticQaResponses: semanticResponses,
    directorResponseIndex: 0,
    actorsUsedThisRound: [],
    turnIndex: 0,
    eligibilitySnapshot: { eligibility_snapshot_id: 'snap-1', eligible_actors: ['Alice'] },
    participationContext: {},
    recorder,
    runEphemeralInference: async (args) => {
      call += 1;
      const isEvaluator = args.evidenceContext?.role === 'semantic_evaluator';
      const evidenceId = isEvaluator ? `eval-${call}` : `director-${call}`;
      recorder.store.writeAttempt({
        evidence_id: evidenceId,
        correlation: {
          ...args.evidenceContext,
          hg_session_id: 'hg-session-1',
          hg_scene_id: 'scene-1',
          hg_round_id: 'round-1',
          evidence_id: evidenceId,
          role: args.evidenceContext?.role ?? 'director',
          inference_id: args.evidenceContext?.inferenceId ?? 'inf-director-1',
        },
        request: {},
        response: {},
      });
      if (isEvaluator) {
        const passId = args.evidenceContext.evaluationPassId;
        const index = passId.endsWith('-qa-0') ? 0 : 1;
        return {
          failed: false,
          raw: semanticResponses[index],
          evidenceId,
          inferenceSessionId: `eval-sess-${index}`,
          trace: {},
        };
      }
      return {
        failed: false,
        raw: JSON.stringify(VALID_DIRECTOR),
        evidenceId,
        inferenceSessionId: `dir-sess-${call}`,
        trace: {},
      };
    },
    liveMaxAttempts: 3,
    directorSemanticQaEnabled: true,
  });

  assert.equal(result.accepted, true);
  const index = recorder.readIndex('hg-session-1');
  const chain = index.semantic.qa_pass_chains['inf-director-1'];
  assert.equal(chain.length, 2);
  assert.equal(chain[0].policy_action, 'soft_regen');
  assert.equal(chain[1].policy_action, 'pass');
  const rejected = recorder.readAttempt('hg-session-1', chain[0].candidate_evidence_id);
  assert.ok(rejected.decision.director.eligibility);
  assert.equal(Object.hasOwn(rejected, 'semantic_qa'), false);
});

test('rebuildSemanticNavigationIndexes restores qa_pass_chains', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-rebuild-'));
  const store = new ExecutionEvidenceStore(root);
  const hgSessionId = 'sess-rebuild';
  store.writeAttempt({
    evidence_id: 'candidate-1',
    correlation: {
      hg_session_id: hgSessionId,
      hg_round_id: 'round-1',
      role: 'director',
      inference_id: 'inf-1',
    },
    request: {},
    response: {},
  });
  store.patchAttempt(hgSessionId, 'candidate-1', {
    decision: {
      semantic_qa: buildSemanticQaDecisionFields({
        evaluationPassId: 'pass-1',
        evaluationTargetRole: 'director',
        evaluatorEvidenceId: 'eval-1',
        policyAction: 'pass',
        result: { overall_result: 'pass', findings: [] },
      }),
    },
  });
  const index = store.readIndex(hgSessionId);
  index.semantic.qa_pass_chains = {};
  fs.writeFileSync(
    store.indexPath(hgSessionId),
    `${JSON.stringify(index, null, 2)}\n`,
    'utf8',
  );
  const rebuilt = store.rebuildSemanticNavigationIndexes(hgSessionId);
  assert.deepEqual(rebuilt.semantic.qa_pass_chains['inf-1'], [{
    candidate_evidence_id: 'candidate-1',
    evaluator_evidence_id: 'eval-1',
    evaluation_pass_id: 'pass-1',
    policy_action: 'pass',
  }]);
  fs.rmSync(root, { recursive: true, force: true });
});
