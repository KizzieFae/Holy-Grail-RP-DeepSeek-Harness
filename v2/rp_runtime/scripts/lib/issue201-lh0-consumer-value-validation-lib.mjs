/**
 * Issue #201 LH-0 — consumer-value deterministic validation (pre-live gates).
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { LH0_ARMS } from './issue201-lh0-arms.mjs';
import { loadLh0FixtureManifest } from './issue201-lh0-fixtures.mjs';
import { loadLh0Policy, sha256File } from './issue201-lh0-player-policy.mjs';
import { REPO_ROOT } from './issue201-lh0-fixtures.mjs';
import {
  buildLh0FinalizedProjection,
  obligationsForConsumer,
  classifyLh0ObligationStates,
} from './issue201-lh0-persistent-store.mjs';
import {
  buildInformationUniquenessReport,
  listDecisionForks,
  seedLh0ObligationFromFixture,
} from './issue201-lh0-semantic-content.mjs';
import { runLh0SemanticValidationSuite } from './issue201-lh0-semantic-validation-lib.mjs';
import { runLh0TimingValidationSuite } from './issue201-lh0-timing-validation-lib.mjs';
import {
  LH0_DIRECTIVE_MARKERS,
  LH0_GUEST_FACT_MARKERS,
  LH0_LEADING_QUESTION_MARKERS,
  LH0_NEUTRAL_GUEST_POLICY_QUESTION,
  LH0_PERSISTENT_GUEST_FACT,
} from './issue201-lh0-consumer-value-contract.mjs';

const LIVE_LIB_PATH = path.join(
  path.dirname(fileURLToPath(import.meta.url)),
  'issue201-lh0-live-lib.mjs',
);

function check(name, pass, detail = null) {
  return { name, pass, detail };
}

function guestFactInText(text) {
  const lower = String(text ?? '').toLowerCase();
  return LH0_GUEST_FACT_MARKERS.some((m) => lower.includes(m));
}

export function runLh0ConsumerValueValidationSuite() {
  const fixture = loadLh0FixtureManifest();
  const { policy } = loadLh0Policy('ayame_lh0_policy_v1');
  const checks = [];
  const t5 = policy.turns.find((t) => t.turn_index === 5);
  const deferred = fixture.obligations.find((o) => o.obligation_id === 'LH0-OBL-DEFERRED');
  const later = fixture.obligations.find((o) => o.obligation_id === 'LH0-OBL-LATER');

  const liveLibSource = fs.readFileSync(LIVE_LIB_PATH, 'utf8');
  checks.push(check(
    'lh0_calls_record_user_turn',
    liveLibSource.includes('recordUserTurn')
      && liveLibSource.includes('runPlayerPvrAndRecord'),
  ));
  checks.push(check(
    'no_raw_text_bypass',
    !liveLibSource.includes('injectPlayer')
      && !liveLibSource.includes('rawPlayerText')
      && !liveLibSource.includes('bypassPvr'),
  ));

  checks.push(check(
    'neutral_player_stimulus_frozen',
    t5?.realization?.includes(LH0_NEUTRAL_GUEST_POLICY_QUESTION) === true,
  ));
  checks.push(check(
    'player_question_not_leading',
    !LH0_LEADING_QUESTION_MARKERS.some((m) => (t5?.realization ?? '').toLowerCase().includes(m)),
  ));

  const persistentSemantics = [deferred, later]
    .map((o) => String(o?.semantic_content ?? '').toLowerCase());
  checks.push(check(
    'persistent_fact_only_no_directive',
    persistentSemantics.every((s) => !LH0_DIRECTIVE_MARKERS.some((d) => s.includes(d))),
  ));
  checks.push(check(
    'persistent_fact_semantic_present',
    persistentSemantics.every((s) => guestFactInText(s)),
  ));

  const timing = runLh0TimingValidationSuite();
  checks.push(check('turn_alignment_regressions', timing.all_pass === true));
  const semantic = runLh0SemanticValidationSuite();
  checks.push(check('semantic_regressions', semantic.all_pass === true));

  const store = {
    obligations: fixture.obligations
      .filter((o) => !o.negative_control)
      .map((o) => seedLh0ObligationFromFixture(o, { mechanism: 'fixture_seed', source: 'fixture_seed' })),
    events: [],
  };
  for (let turn = 1; turn <= 4; turn += 1) classifyLh0ObligationStates(store, turn);
  const t4Due = obligationsForConsumer(store, { turn: 4, consumer: 'character_move' });
  checks.push(check('t1_t4_deferred_withhold', t4Due.length === 0));

  const t5Due = obligationsForConsumer(store, { turn: 5, consumer: 'character_move' });
  checks.push(check('t5_projection_eligibility', t5Due.length >= 2));

  const projections = [LH0_ARMS.LH_B, LH0_ARMS.LH_C, LH0_ARMS.LH_D].map((arm) => (
    buildLh0FinalizedProjection(t5Due, {
      batchId: `cv-${arm}`,
      consumer: 'character_move',
      characterId: 'Ayame',
      hgRoundId: 'hg-round-cv',
      turnIndex: 4,
    })
  ));
  const payloads = projections.map((p) => p.contributions.map((c) => c.content).join(' '));
  checks.push(check(
    'b_c_d_identical_fact_payload',
    payloads.every((p) => p === payloads[0]),
  ));
  checks.push(check(
    'b_c_d_comparable_priority',
    projections.every((p) => p.contributions[0]?.priority === projections[0].contributions[0]?.priority),
  ));

  const uniqueness = buildInformationUniquenessReport({ manifestContributions: [] });
  checks.push(check('information_uniqueness_pre_run', uniqueness.all_unique === true));

  const guestFork = listDecisionForks(fixture).find((f) => f.fork_id === 'FORK-GUEST-POLICY');
  checks.push(check('guest_fork_turn_5', guestFork?.decision_turn === 5));
  checks.push(check('decision_classes_frozen', (guestFork?.with_obligation_choice_classes?.length ?? 0) > 0));

  const fixturePath = path.join(REPO_ROOT, 'governance/records/issue201-lh0-fixtures/lh0_fixture_manifest.json');
  const policyPath = path.join(REPO_ROOT, 'governance/records/issue201-lh0-policies/ayame_lh0_policy_v1.json');
  const allPass = checks.every((c) => c.pass);

  return {
    schema: 'issue201_lh0_consumer_value_validation_v1',
    all_pass: allPass,
    checks,
    frozen_contract: {
      neutral_player_stimulus: LH0_NEUTRAL_GUEST_POLICY_QUESTION,
      persistent_guest_fact: LH0_PERSISTENT_GUEST_FACT,
      fixture_hash: sha256File(fixturePath),
      policy_hash: sha256File(policyPath),
    },
    timing_validation: timing,
    semantic_validation: semantic,
    information_uniqueness: uniqueness,
    readiness_for_consumer_value_qualification: allPass,
  };
}
