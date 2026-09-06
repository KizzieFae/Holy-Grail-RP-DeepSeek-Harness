import assert from 'node:assert/strict';
import test from 'node:test';

import { CampaignLimits } from '../src/scenario-harness/campaign-limits.mjs';
import {
  CampaignRunState,
  classifyDeterministicInfrastructureFailure,
  DeterministicStopClass,
  evaluateExpansionGate,
  HISTORICAL_STORYTELLER_HTTP_400_SIGNATURE,
  Issue136CampaignStateMachine,
} from '../src/scenario-harness/issue136-campaign-state.mjs';

test('issue136 campaign state machine stops on safety guard exhaustion', () => {
  const limits = new CampaignLimits({ maxRuns: 1, maxInferences: 1 });
  const machine = new Issue136CampaignStateMachine(limits);
  limits.recordRun();
  limits.recordRun();
  const stopClass = classifyDeterministicInfrastructureFailure(
    new Error('campaign_run_limit_exceeded'),
  );
  assert.equal(stopClass, DeterministicStopClass.SAFETY_GUARD_EXHAUSTED);
  machine.stop(stopClass, 'campaign_run_limit_exceeded');
  assert.equal(machine.state, CampaignRunState.STOPPED);
  assert.equal(limits.stopped, true);
  assert.throws(() => limits.assertCanRun(), /campaign_stopped/);
});

test('issue136 campaign state machine stops on fixture authority install failure', () => {
  const limits = new CampaignLimits();
  const machine = new Issue136CampaignStateMachine(limits);
  const stopClass = classifyDeterministicInfrastructureFailure(
    new Error('missing_issue136_card:fixture-a'),
  );
  assert.equal(stopClass, DeterministicStopClass.FIXTURE_AUTHORITY_INSTALL_FAILURE);
  machine.stop(stopClass);
  assert.equal(machine.shouldScheduleMore(), false);
});

test('issue136 campaign state machine stops on host prepare failure', () => {
  const stopClass = classifyDeterministicInfrastructureFailure(
    new Error('context prepare failed for character_turn'),
  );
  assert.equal(stopClass, DeterministicStopClass.HOST_PREPARE_FAILURE);
});

test('issue136 campaign state machine stops on historical storyteller infrastructure signature', () => {
  const stopClass = classifyDeterministicInfrastructureFailure(
    new Error(`Storyteller finalize HTTP 400: ${HISTORICAL_STORYTELLER_HTTP_400_SIGNATURE}`),
  );
  assert.equal(stopClass, DeterministicStopClass.STORYTELLER_INFRASTRUCTURE_SIGNATURE);
});

test('issue136 stopped state prevents additional fixture scheduling', () => {
  const limits = new CampaignLimits();
  const machine = new Issue136CampaignStateMachine(limits);
  machine.stop(DeterministicStopClass.HOST_PREPARE_FAILURE, 'prepare failed');
  assert.equal(machine.shouldScheduleMore(), false);
  assert.equal(limits.stopReason, 'host_prepare_failure:prepare failed');
});

test('issue136 completed state only occurs after full authorized queue', () => {
  const limits = new CampaignLimits();
  const machine = new Issue136CampaignStateMachine(limits);
  assert.equal(machine.state, CampaignRunState.RUNNING);
  machine.complete();
  assert.equal(machine.state, CampaignRunState.COMPLETED);
  assert.equal(limits.stopped, false);
});

test('issue136 stochastic semantic failures do not trigger immediate deterministic stop', () => {
  const stopClass = classifyDeterministicInfrastructureFailure(
    new Error('unsupported softening detected in committed move'),
  );
  assert.equal(stopClass, null);
});

test('issue136 expansion gate stops after zero-commit schema-only fixture reps', () => {
  const fixtureResults = [
    {
      forensic: {
        character_turns: [{
          committed: false,
          qa_chain: [{
            accepted: false,
            outcome: 'ingress_rejected',
            candidate_text: '{"beats":[{"type":"action","description":"bad"}]}',
          }],
        }],
      },
    },
    {
      forensic: {
        character_turns: [{
          committed: false,
          qa_chain: [{
            accepted: false,
            outcome: 'schema_recoverable',
            semantic_evaluation: { error: 'unknown fields on action beat: description' },
          }],
        }],
      },
    },
  ];
  const gate = evaluateExpansionGate({
    fixtureId: '136-T2-A-STABILITY',
    fixtureResults,
    repetitions: 2,
  });
  assert.match(gate, /expansion_gate:fixture=136-T2-A-STABILITY:zero_commits_schema_only/);
});

test('issue136 expansion gate does not stop when a move commits', () => {
  const gate = evaluateExpansionGate({
    fixtureId: '136-T2-A-STABILITY',
    fixtureResults: [{
      forensic: {
        character_turns: [{
          committed: true,
          domain_commit_id: 'commit-1',
          qa_chain: [{ accepted: true }],
        }],
      },
    }],
    repetitions: 1,
  });
  assert.equal(gate, null);
});

test('issue136 limits.stop is invoked by state machine', () => {
  const limits = new CampaignLimits();
  const machine = new Issue136CampaignStateMachine(limits);
  machine.stop(DeterministicStopClass.SAFETY_GUARD_EXHAUSTED, 'max_runs');
  assert.equal(limits.stopped, true);
  assert.equal(limits.stopReason, 'safety_guard_exhausted:max_runs');
});
