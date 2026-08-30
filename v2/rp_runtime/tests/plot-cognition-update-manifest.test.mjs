import assert from 'node:assert/strict';
import test from 'node:test';

import { manifestFromPlotCognitionUpdatePrepare } from '../src/lib/plot-cognition-update-envelope.mjs';
import {
  assertSemanticAuthorityInPrepare,
  buildInitializationObjectiveGates,
  evaluateSafeTranslationAchieved,
  initializationSourceRichness,
} from '../src/scenario-harness/production-capture.mjs';
import { loadTruthFixture } from '../src/scenario-harness/fixture-truth.mjs';

test('update manifest includes readable semantic authority excerpts', () => {
  const prepareResponse = {
    manifest_id: 'manifest-test',
    authority_source_fingerprint: 'fp-test',
    source_snapshot: {
      snapshot_id: 'snap-1',
      canonical_body: {
        continuity: {
          public_events: [{ event_id: 'evt-1', summary_digest: 'abc123' }],
        },
      },
      semantic_authority_excerpts: {
        schema: 'hg_plot_cognition_semantic_authority_excerpts_v1',
        public_events: [{
          event_id: 'evt-1',
          summary: 'The treaty is finished. Everyone here saw what happened.',
        }],
      },
      prior_operative_cognition: {
        schema: 'hg_plot_cognition_prior_operative_cognition_v1',
        store_revision: 2,
        goals: [{
          goal_id: 'goal-1',
          intended_direction: 'Pursue reconciliation with the northern houses.',
          planning_horizon: 'MEDIUM',
          grounding: 'Established at scene open.',
          applicability: { applicability_kind: 'global', primary_character_id: null, involved_character_ids: [] },
        }],
        pressures: [],
        global_plot_frame: null,
      },
    },
  };
  const manifest = manifestFromPlotCognitionUpdatePrepare(prepareResponse);
  const authorityContent = manifest.contributions[0].content;
  assert.ok(authorityContent.includes('semantic_authority_excerpts'));
  assert.ok(authorityContent.includes('prior_operative_cognition'));
  assert.ok(authorityContent.includes('The treaty is finished'));
  assert.ok(authorityContent.includes('summary_digest'));
  assert.ok(authorityContent.includes('Pursue reconciliation'));
  const priorContribution = manifest.contributions.find(
    (item) => item.contribution_id === 'manifest-test-prior-operative-cognition',
  );
  assert.ok(priorContribution);
  assert.equal(priorContribution.authority_class, 'advisory');
  assert.ok(priorContribution.content.includes('goal-1'));
});

test('assertSemanticAuthorityInPrepare detects readable treaty semantics', () => {
  const proof = assertSemanticAuthorityInPrepare({
    source_snapshot: {
      canonical_body: {},
      semantic_authority_excerpts: {
        public_events: [{ summary: 'The treaty is finished.' }],
      },
    },
  });
  assert.equal(proof.ok, true);
  assert.ok(proof.readable_texts.some((text) => text.includes('treaty')));
});

test('minimal initialization source does not require semantic richness gate', () => {
  const truth = loadTruthFixture('t1-01-init');
  assert.equal(initializationSourceRichness(truth), 'minimal');
  const gates = buildInitializationObjectiveGates({
    truth,
    plan: { operation: 'initialization' },
    lifecycle: { ok: true, initFinalize: { accepted: true } },
    overlay: { store_revision: 1, plot_cognition_scope_id: 'scope-1', goals: {}, pressures: {} },
    overlayRevisionBefore: 0,
    scopeId: 'scope-1',
    forensics: { chronicleKeys: [':init:'] },
    initRaw: { raw: '{}' },
  });
  assert.ok(gates.plan_initialization.pass);
  assert.ok(gates.overlay_persisted.pass);
  assert.equal(gates.initialization_semantic_richness, undefined);
});

test('rich initialization source requires semantic richness gate', () => {
  const truth = {
    source_richness: 'sufficient',
    expected_pressure_material: ['missing key tension'],
  };
  const gates = buildInitializationObjectiveGates({
    truth,
    plan: { operation: 'initialization' },
    lifecycle: { ok: true, initFinalize: { accepted: true } },
    overlay: { store_revision: 1, plot_cognition_scope_id: 'scope-1', goals: {}, pressures: {} },
    overlayRevisionBefore: 0,
    scopeId: 'scope-1',
    forensics: { chronicleKeys: [':init:'] },
    initRaw: { raw: '{}' },
  });
  assert.equal(gates.initialization_semantic_richness.pass, false);
});

test('safe translation withholding alone does not certify', () => {
  const truth = loadTruthFixture('t1-06-safe-translation');
  const result = evaluateSafeTranslationAchieved({
    truth,
    capture: {
      layer_b: { first: { verdict: 'withhold' }, second: null },
      character_storyteller_contributions: [],
    },
    storytellerCount: 0,
    targetCharacter: 'Alice',
  });
  assert.equal(result.pass, false);
  assert.equal(result.detail, 'no_useful_delivery');
});

test('safe translation delivery with pass verdict certifies', () => {
  const truth = loadTruthFixture('t1-06-safe-translation');
  const result = evaluateSafeTranslationAchieved({
    truth,
    capture: {
      layer_b: { first: { verdict: 'pass' }, second: null },
      character_storyteller_contributions: [{
        content: 'STORYTELLER CHARACTER ADVISORY:\nYou could check in with Bob discreetly.',
      }],
    },
    storytellerCount: 1,
    admittedTexts: ['STORYTELLER CHARACTER ADVISORY:\nYou could check in with Bob discreetly.'],
    targetCharacter: 'Alice',
  });
  assert.equal(result.pass, true);
  assert.equal(result.detail, 'safe_delivery');
});
