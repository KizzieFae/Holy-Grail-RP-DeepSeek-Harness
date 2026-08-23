import assert from 'node:assert/strict';
import test from 'node:test';

import { parseSemanticEvaluationResult } from '../src/plugins/hg-phase-executors/character-semantic-evaluation.mjs';

const PLAYER_AGENCY_GUARDRAIL_ID = 'guardrail:player_agency';

function parseScenario({ dimension, severity, finding, refId, authorityRefs }) {
  const raw = JSON.stringify({
    schema: 'hg_semantic_evaluation_result_v1',
    overall_result: severity === 'hard' ? 'reject_hard' : 'reject_soft',
    findings: [
      {
        dimension,
        severity,
        finding,
        rationale: `scenario:${dimension}`,
        authoritative_citation: refId ? { ref_id: refId } : null,
      },
    ],
  });
  return parseSemanticEvaluationResult(raw, authorityRefs);
}

const authorityRefs = [
  { ref_id: PLAYER_AGENCY_GUARDRAIL_ID },
  { ref_id: 'character_fact:Alice:identity' },
  { ref_id: 'continuity_fact:scene:location' },
  { ref_id: 'perception_fact:scene:present_characters' },
  { ref_id: 'binding_fact:turn:42' },
];

test('scenario R02b player agency hard with guardrail citation', () => {
  const parsed = parseScenario({
    dimension: 'R02b',
    severity: 'hard',
    finding: 'Character spoke for player',
    refId: PLAYER_AGENCY_GUARDRAIL_ID,
    authorityRefs,
  });
  assert.equal(parsed.result.findings[0].severity, 'hard');
});

test('scenario R11 repetition soft without authority requirement', () => {
  const parsed = parseScenario({
    dimension: 'R11',
    severity: 'soft',
    finding: 'Beat repeats prior turn phrasing',
    refId: null,
    authorityRefs,
  });
  assert.equal(parsed.result.overall_result, 'reject_soft');
  assert.equal(parsed.result.findings[0].severity, 'soft');
});

test('scenario R12 fidelity hard requires character_fact citation', () => {
  const parsed = parseScenario({
    dimension: 'R12',
    severity: 'hard',
    finding: 'Character name drift',
    refId: 'character_fact:Alice:identity',
    authorityRefs,
  });
  assert.equal(parsed.result.findings[0].severity, 'hard');
});

test('scenario R14 perception hard with perception_fact citation', () => {
  const parsed = parseScenario({
    dimension: 'R14',
    severity: 'hard',
    finding: 'Character references off-scene knowledge',
    refId: 'perception_fact:scene:present_characters',
    authorityRefs,
  });
  assert.equal(parsed.result.findings[0].severity, 'hard');
});

test('scenario R15 binding contradiction hard with binding_fact citation', () => {
  const parsed = parseScenario({
    dimension: 'R15',
    severity: 'hard',
    finding: 'Contradicts committed binding fact',
    refId: 'binding_fact:turn:42',
    authorityRefs,
  });
  assert.equal(parsed.result.findings[0].severity, 'hard');
});

test('scenario ambiguous soft should not hard-reject without authority', () => {
  const parsed = parseScenario({
    dimension: 'R11',
    severity: 'hard',
    finding: 'Maybe repetitive',
    refId: 'binding_fact:missing',
    authorityRefs,
  });
  assert.equal(parsed.result.findings[0].severity, 'soft');
});

test('scenario valid RP pass accepts empty findings', () => {
  const parsed = parseSemanticEvaluationResult(
    JSON.stringify({
      schema: 'hg_semantic_evaluation_result_v1',
      overall_result: 'pass',
      findings: [],
    }),
    authorityRefs,
  );
  assert.equal(parsed.ok, true);
  assert.equal(parsed.result.overall_result, 'pass');
});
