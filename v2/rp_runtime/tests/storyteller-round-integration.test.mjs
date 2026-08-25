import assert from 'node:assert/strict';
import test from 'node:test';

import { createTestSession, startDomainApi } from './helpers/domain-api.mjs';
import { createHolyGrailRpContext } from '../src/bootstrap.mjs';
import { STORYTELLER_ASSESSMENT_SCHEMA } from '../src/lib/storyteller-assessment-envelope.mjs';
import { STORYTELLER_ORIENTATION_SCHEMA } from '../src/lib/storyteller-orientation-envelope.mjs';

const MOVE = {
  move_schema_version: 2,
  beats: [{ type: 'action', action: 'does something unrelated to the advisory hook' }],
  motivation: { goal: 'a', tactic: 'b', emotional_driver: 'c', risk_level: 'low' },
  semantic_evaluation: { decision: 'no_covered_change' },
};

const DIRECTOR_FOR = (name) => ({
  next_actor: name,
  end_round: false,
  reason: `${name} should speak next.`,
  environment_event: '',
  tension_shift: 'steady',
});

const MOCK_ORIENTATION = JSON.stringify({
  schema: STORYTELLER_ORIENTATION_SCHEMA,
  orientation_id: 'orient-live-1',
  turn_index: 0,
  trigger: 'round_start',
  information_gaps: ['What tensions are active for Alice?', 'Which relationships are under strain?'],
  temporal_focus: 'current',
  breadth_preference: 'broad',
});

const MOCK_ASSESSMENT = JSON.stringify({
  schema: STORYTELLER_ASSESSMENT_SCHEMA,
  assessment_id: 'assess-live-1',
  observations: [
    {
      text: 'Alice betrayal tension is thematically central.',
      evidence_refs: [{ ref_kind: 'bundle_entry', stable_ref: 'entry-alice', display_hint: 'Alice betrayal' }],
      confidence: 'likely',
    },
  ],
  active_tensions: [
    {
      label: 'Betrayal strain',
      interpretive_note: 'Alice may feel pressure without being required to confront it.',
      evidence_refs: [{ ref_kind: 'bundle_entry', stable_ref: 'entry-alice' }],
    },
  ],
  narrative_priorities: [
    {
      focus: 'Trust fracture',
      why_it_matters: 'Actors may attend to whether reconciliation or avoidance becomes meaningful.',
      evidence_refs: [{ ref_kind: 'bundle_entry', stable_ref: 'entry-alice' }],
    },
  ],
  progression_opportunities: [
    {
      opportunity_label: 'Alice reconciliation path',
      narrative_hook: 'Alice could seek clarity if she chooses.',
      evidence_refs: [{ ref_kind: 'bundle_entry', stable_ref: 'entry-alice' }],
    },
  ],
  unresolved_threads: [
    {
      thread_label: 'Broken treaty seal',
      neglect_risk: 'May fade if not referenced again.',
      evidence_refs: [{ ref_kind: 'bundle_entry', stable_ref: 'entry-alice' }],
    },
  ],
  uncertainty: [],
  information_gaps: [],
  evidence_refs: [{ ref_kind: 'bundle_entry', stable_ref: 'entry-alice' }],
});

test('storyteller round integration: cognition before director, invalidates after commit', async (t) => {
  const port = 42765 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port);
  const { baseUrl } = host;
  t.after(() => host.stop());

  const { ctx, orchestrator } = await createHolyGrailRpContext({ domainApi: { baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const result = await orchestrator.runRound({
    domainApi: { baseUrl },
    session: { mode: 'create', cast: ['Alice', 'Bob'] },
    mockDirectorResponses: [JSON.stringify(DIRECTOR_FOR('Bob'))],
    mockCharacterTurnResponses: [[JSON.stringify(MOVE)]],
    mockStorytellerOrientationResponse: MOCK_ORIENTATION,
    mockStorytellerAssessmentResponse: MOCK_ASSESSMENT,
  });

  const started = result.scene_events.find((event) => event.type === 'hg/storyteller-started');
  const completed = result.scene_events.find((event) => event.type === 'hg/storyteller-completed');
  assert.ok(started);
  assert.ok(completed);
  assert.equal(result.storyteller?.bound, true);
  assert.ok(result.storyteller?.package_id);

  const directorProposedIndex = result.scene_events.findIndex((event) => event.type === 'hg/director-proposed');
  const storytellerCompletedIndex = result.scene_events.findIndex(
    (event) => event.type === 'hg/storyteller-completed',
  );
  assert.ok(directorProposedIndex > storytellerCompletedIndex);

  assert.equal(result.actors_used_this_round[0], 'Bob');
  assert.equal(result.character_turn_count, 1);

  const invalidated = result.scene_events.find((event) => event.type === 'hg/storyteller-invalidated');
  assert.ok(invalidated);
  assert.equal(invalidated.data.invalidation_reason, 'authoritative_commit');
});

test('storyteller round integration: skipped cognition keeps baseline round', async (t) => {
  const port = 43765 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port);
  const { baseUrl } = host;
  t.after(() => host.stop());

  const { ctx, orchestrator } = await createHolyGrailRpContext({ domainApi: { baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const result = await orchestrator.runRound({
    domainApi: { baseUrl },
    session: { mode: 'create', cast: ['Alice'] },
    skipStorytellerCognition: true,
    mockDirectorResponses: [JSON.stringify(DIRECTOR_FOR('Alice'))],
    mockCharacterTurnResponses: [[JSON.stringify(MOVE)]],
  });

  assert.equal(result.storyteller, null);
  assert.equal(result.scene_events.some((event) => event.type === 'hg/storyteller-started'), false);
  assert.equal(result.character_turn_count, 1);
});
