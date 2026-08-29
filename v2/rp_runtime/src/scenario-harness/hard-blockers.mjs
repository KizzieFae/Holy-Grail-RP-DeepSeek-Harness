import { OBJECTIVE_STATUS } from './scenario-result.mjs';

export const HARD_BLOCKER_CODES = {
  EPISTEMIC_LEAK: 'epistemic_leak',
  STALE_ADMITTED: 'stale_cognition_admitted',
  AUTHORITY_CORRUPTION: 'authority_state_corruption',
  FORBIDDEN_FALLBACK: 'forbidden_semantic_fallback',
  REGEN_EXCEEDED: 'regeneration_budget_exceeded',
  EVAL_EXCEEDED: 'evaluation_budget_exceeded',
  CORRECTION_EXCEEDED: 'contract_correction_budget_exceeded',
  INFERENCE_CHAIN_EXCEEDED: 'inference_chain_exceeded',
  MISSING_EVIDENCE: 'missing_execution_evidence',
  MISSING_CHRONICLE: 'missing_chronicle_evidence',
  OBJECTIVE_FAILURE: 'objective_gate_failure',
  HARNESS_DEFECT: 'harness_evaluator_defect',
};

const LAYER_B_EVAL_KIND = 'plot_cognition_epistemic_eval';
const LAYER_B_CORRECTION_KIND = 'plot_cognition_epistemic_eval_contract_correction';
const LAYER_B_REGEN_KIND = 'character_advisory_generation';

const LAYER_B_CHAIN_KINDS = new Set([
  LAYER_B_EVAL_KIND,
  LAYER_B_CORRECTION_KIND,
  LAYER_B_REGEN_KIND,
]);

export const LAYER_B_CHAIN_CEILING = 5;
export const LAYER_B_EVAL_CEILING = 2;
export const LAYER_B_REGEN_CEILING = 1;
export const LAYER_B_CORRECTION_CEILING = 2;

export function detectForbiddenLeaks(text, truth, targetCharacter) {
  const haystack = String(text ?? '').toLowerCase();
  const leaks = [];
  const forbidden = truth?.forbidden_leaks_to?.[targetCharacter] ?? [];
  for (const token of forbidden) {
    if (haystack.includes(String(token).toLowerCase())) {
      leaks.push({ token, target_character: targetCharacter });
    }
  }
  for (const fact of truth?.private_facts ?? []) {
    if (fact.owner && fact.owner !== targetCharacter && fact.value) {
      const value = String(fact.value).toLowerCase();
      if (value && haystack.includes(value)) {
        leaks.push({ token: fact.value, owner: fact.owner, target_character: targetCharacter });
      }
    }
  }
  return leaks;
}

export function analyzeLayerBAccounting(liveCalls) {
  const evalCount = liveCalls.filter((c) => c.inference_kind === LAYER_B_EVAL_KIND).length;
  const correctionCount = liveCalls.filter((c) => c.inference_kind === LAYER_B_CORRECTION_KIND).length;
  const regenCount = liveCalls.filter((c) => c.inference_kind === LAYER_B_REGEN_KIND).length;
  const layerBCount = liveCalls.filter((c) => LAYER_B_CHAIN_KINDS.has(c.inference_kind)).length;
  const violations = [];
  if (evalCount > LAYER_B_EVAL_CEILING) {
    violations.push({ code: HARD_BLOCKER_CODES.EVAL_EXCEEDED, evalCount });
  }
  if (correctionCount > LAYER_B_CORRECTION_CEILING) {
    violations.push({ code: HARD_BLOCKER_CODES.CORRECTION_EXCEEDED, correctionCount });
  }
  if (regenCount > LAYER_B_REGEN_CEILING) {
    violations.push({ code: HARD_BLOCKER_CODES.REGEN_EXCEEDED, regenCount });
  }
  if (layerBCount > LAYER_B_CHAIN_CEILING) {
    violations.push({ code: HARD_BLOCKER_CODES.INFERENCE_CHAIN_EXCEEDED, layerBCount });
  }
  return { evalCount, correctionCount, regenCount, layerBCount, violations };
}

export function analyzeHardBlockers({
  scenarioResult,
  truth = null,
  consumerTexts = [],
  targetCharacter = null,
  liveCalls = [],
  requireEvidence = true,
  requireChronicle = false,
} = {}) {
  const blockers = [];

  if (scenarioResult?.objective_status === OBJECTIVE_STATUS.BLOCKED) {
    blockers.push({ code: HARD_BLOCKER_CODES.OBJECTIVE_FAILURE, detail: 'objective_status_blocked' });
  }

  if (requireEvidence) {
    const liveWithEvidence = liveCalls.filter((c) => c.live);
    for (const call of liveWithEvidence) {
      if (!call.evidence_id) {
        blockers.push({
          code: HARD_BLOCKER_CODES.MISSING_EVIDENCE,
          detail: { inference_id: call.inference_id, kind: call.inference_kind },
        });
      }
    }
  }

  if (requireChronicle && !(scenarioResult?.chronicle_keys ?? []).length) {
    blockers.push({ code: HARD_BLOCKER_CODES.MISSING_CHRONICLE });
  }

  const accounting = analyzeLayerBAccounting(liveCalls);
  for (const violation of accounting.violations) {
    blockers.push(violation);
  }

  if (truth && targetCharacter) {
    for (const text of consumerTexts) {
      const leaks = detectForbiddenLeaks(text, truth, targetCharacter);
      for (const leak of leaks) {
        blockers.push({ code: HARD_BLOCKER_CODES.EPISTEMIC_LEAK, detail: leak, text_excerpt: String(text).slice(0, 240) });
      }
    }
  }

  return {
    has_blocker: blockers.length > 0,
    blockers,
    layer_b_accounting: accounting,
  };
}
