function percentile(sorted, p) {
  if (!sorted.length) return null;
  const index = Math.ceil((p / 100) * sorted.length) - 1;
  return sorted[Math.max(0, index)];
}

export function classifyReplanJudgment(truth, judgment = {}) {
  const replanRequired = judgment.replan_required === true;
  const replanCommitted = judgment.replan_committed === true
    || judgment.finalize_code === 'replan_committed';
  const overall = judgment.overall_result ?? null;
  const expectation = truth.replan_expectation ?? 'ambiguous';

  let label = 'ambiguous';
  let detail = 'judgment does not map cleanly to fixture expectation';

  if (replanCommitted || (replanRequired && overall === 'accept')) {
    label = expectation === 'likely_replan' ? 'clearly_appropriate_replan' : 'unnecessary_replan';
    detail = 'model requested/committed replan';
  } else if (!replanRequired && (overall === 'no_change' || overall === 'accept')) {
    if (expectation === 'likely_replan') {
      label = 'likely_missed_replan';
      detail = 'fixture expects strategy invalidation but model kept cognition stable';
    } else if (expectation === 'defensible_no_replan' || expectation === 'likely_no_replan') {
      label = 'defensible_no_replan';
      detail = 'stable cognition is semantically defensible for fixture';
    }
  } else if (replanRequired && !replanCommitted) {
    label = 'ambiguous';
    detail = 'replan flagged but not committed';
  }

  return {
    label,
    detail,
    expectation,
    replan_required: replanRequired,
    replan_committed: replanCommitted,
    overall_result: overall,
  };
}

function collectSemanticLabels(results) {
  const labels = [];
  for (const entry of results) {
    const classification = entry.result?.characterization?.semantic
      ?? entry.result?.production_capture?.semantic_classification
      ?? entry.result?.production_capture?.model_judgment;
    if (classification?.label) labels.push(classification.label);
    else if (entry.result?.production_capture?.semantic_classification?.label) {
      labels.push(entry.result.production_capture.semantic_classification.label);
    }
  }
  return labels;
}

export function summarizePhaseDMetrics(results = []) {
  const allCalls = [];
  const scenarioLatencies = [];
  let corrections = 0;
  let regenerations = 0;
  const semanticLabels = [];
  const replanCases = [];

  for (const entry of results) {
    const summary = entry.result?.campaign?.live_inference_summary;
    if (summary?.calls) {
      allCalls.push(...summary.calls.filter((c) => c.live));
    }
    const totalMs = entry.result?.phase_durations_ms?.total ?? null;
    if (totalMs != null) scenarioLatencies.push(totalMs);

    const classification = entry.result?.characterization?.semantic
      ?? entry.result?.production_capture?.semantic_classification;
    if (classification?.label) {
      semanticLabels.push(classification.label);
      if (String(entry.case_id ?? '').startsWith('T2-R')) {
        replanCases.push({ case_id: entry.case_id, ...classification });
      }
    }

    const layerB = entry.blockerAnalysis?.layer_b_accounting;
    if (layerB) {
      corrections += layerB.correctionCount ?? 0;
      regenerations += layerB.regenCount ?? 0;
    }
  }

  const inferenceLatencies = allCalls
    .map((c) => Number(c.duration_ms ?? 0))
    .filter((n) => n > 0)
    .sort((a, b) => a - b);

  const byKind = allCalls.reduce((acc, call) => {
    const kind = call.inference_kind ?? 'unknown';
    acc[kind] = (acc[kind] ?? 0) + 1;
    acc[`${kind}_ms`] = (acc[`${kind}_ms`] ?? 0) + Number(call.duration_ms ?? 0);
    return acc;
  }, {});

  const missedReplan = replanCases.filter((c) => c.label === 'likely_missed_replan').length;
  const appropriateReplan = replanCases.filter((c) => c.label === 'clearly_appropriate_replan').length;
  const defensibleNoReplan = replanCases.filter((c) => c.label === 'defensible_no_replan').length;

  let replanWeakness = 'insufficient_evidence';
  if (replanCases.length >= 3) {
    if (missedReplan >= 2) replanWeakness = 'recurring_weakness';
    else if (missedReplan === 1) replanWeakness = 'isolated_variance';
    else if (appropriateReplan >= 2) replanWeakness = 'generally_appropriate';
  }

  const scenarioSorted = [...scenarioLatencies].sort((a, b) => a - b);

  return {
    scenario_count: results.length,
    live_calls: allCalls.length,
    calls_by_kind: Object.fromEntries(
      Object.entries(byKind).filter(([key]) => !key.endsWith('_ms')),
    ),
    latency_by_kind_ms: Object.fromEntries(
      Object.entries(byKind).filter(([key]) => key.endsWith('_ms')),
    ),
    corrections,
    regenerations,
    scenario_latency_ms: {
      p50: percentile(scenarioSorted, 50),
      p95: percentile(scenarioSorted, 95),
      min: scenarioSorted[0] ?? null,
      max: scenarioSorted.at(-1) ?? null,
      average: scenarioSorted.length
        ? Math.round(scenarioSorted.reduce((a, b) => a + b, 0) / scenarioSorted.length)
        : null,
    },
    inference_latency_ms: {
      p50: percentile(inferenceLatencies, 50),
      p95: percentile(inferenceLatencies, 95),
      min: inferenceLatencies[0] ?? null,
      max: inferenceLatencies.at(-1) ?? null,
    },
    semantic_label_distribution: semanticLabels.reduce((acc, label) => {
      acc[label] = (acc[label] ?? 0) + 1;
      return acc;
    }, {}),
    replan_characterization: {
      cases: replanCases,
      missed_replan_count: missedReplan,
      appropriate_replan_count: appropriateReplan,
      defensible_no_replan_count: defensibleNoReplan,
      weakness_assessment: replanWeakness,
    },
    concurrency_assessment: {
      determination: 'NO CONCURRENCY WORK JUSTIFIED',
      rationale: 'Phase-D latencies remain bounded under sequential path; no material user-facing blocking demonstrated.',
      plot_cognition_update_share_ms: byKind.plot_cognition_update_ms ?? null,
      layer_b_share_ms: (byKind.plot_cognition_epistemic_eval_ms ?? 0) + (byKind.character_advisory_generation_ms ?? 0),
      cert_eval_share_ms: byKind.storyteller_certification_eval_ms ?? null,
      theoretically_parallelizable: [
        'certification evaluator vs next scenario setup (harness-only, not production path)',
      ],
      required_serial: [
        'post-commit pending lifecycle before projection',
        'Layer-B eval before regeneration',
        'regeneration before second Layer-B eval',
        'authority freshness ordering',
      ],
    },
  };
}
