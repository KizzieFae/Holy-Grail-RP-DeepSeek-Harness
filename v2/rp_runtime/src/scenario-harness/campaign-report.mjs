import { describeResolvedProfiles, createLiveRuntimeConfig } from './live-config.mjs';

function usageTokens(usage = {}) {
  const input = Number(
    usage.inputTokens
    ?? usage.input_tokens
    ?? 0,
  );
  const output = Number(
    usage.outputTokens
    ?? usage.output_tokens
    ?? 0,
  );
  return { input, output };
}

export function buildCampaignReport({
  results,
  limits,
  hardBlockers,
  tranche = 2,
  schema = 'hg_storyteller_tranche2_report_v1',
}) {
  const profiles = describeResolvedProfiles(createLiveRuntimeConfig());
  const allLiveCalls = [];
  let totalTokensIn = 0;
  let totalTokensOut = 0;
  let hasUsage = false;
  for (const entry of results) {
    const summary = entry.result?.campaign?.live_inference_summary;
    if (summary?.calls) allLiveCalls.push(...summary.calls.filter((c) => c.live));
  }
  for (const call of allLiveCalls) {
    const { input, output } = usageTokens(call.usage ?? {});
    if (input) {
      totalTokensIn += input;
      hasUsage = true;
    }
    if (output) {
      totalTokensOut += output;
      hasUsage = true;
    }
  }
  return {
    schema,
    tranche,
    limits: limits.snapshot(),
    resolved_profiles: profiles,
    results,
    hard_blockers: hardBlockers,
    totals: {
      scenario_runs: results.length,
      live_inference_calls: allLiveCalls.length,
      by_kind: allLiveCalls.reduce((acc, call) => {
        const kind = call.inference_kind ?? 'unknown';
        acc[kind] = (acc[kind] ?? 0) + 1;
        return acc;
      }, {}),
      tokens: {
        input: hasUsage ? totalTokensIn : null,
        output: hasUsage ? totalTokensOut : null,
        total: hasUsage ? totalTokensIn + totalTokensOut : null,
        unavailable: !hasUsage,
      },
      latency_ms: {
        per_inference: allLiveCalls.map((c) => ({
          inference_id: c.inference_id,
          kind: c.inference_kind,
          duration_ms: c.duration_ms,
        })),
        per_scenario: results.map((r) => ({
          case_id: r.case_id,
          total_ms: r.result?.phase_durations_ms?.total ?? null,
        })),
      },
    },
  };
}
