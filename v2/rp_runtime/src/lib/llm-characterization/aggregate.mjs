import fs from 'node:fs';
import path from 'node:path';

import {
  classifyCharacterizationStability,
  isValidNaturalCompletionAttempt,
} from './sampling.mjs';

export const CHARACTERIZATION_INDEX_SCHEMA = 'hg_llm_characterization_index_v1';
export const CHARACTERIZATION_BATCH_SCHEMA = 'hg_llm_characterization_batch_v1';
export const CHARACTERIZATION_SUMMARY_SCHEMA = 'hg_llm_characterization_summary_v1';

function percentile(sorted, p) {
  if (!sorted.length) return null;
  const idx = Math.min(sorted.length - 1, Math.max(0, Math.ceil(p * sorted.length) - 1));
  return sorted[idx];
}

function summarizeNumeric(values) {
  const nums = values.filter((v) => Number.isFinite(v)).sort((a, b) => a - b);
  if (!nums.length) {
    return { min: null, median: null, max: null, p95: null, sample_count: 0 };
  }
  const mid = nums[Math.floor(nums.length / 2)];
  return {
    min: nums[0],
    median: mid,
    max: nums[nums.length - 1],
    p95: percentile(nums, 0.95),
    sample_count: nums.length,
  };
}

export function aggregateCallCharacterizationSummary(callId, attempts, options = {}) {
  const validNatural = attempts.filter((a) => isValidNaturalCompletionAttempt(a));
  const censored = attempts.filter((a) => a.censored === true);
  const externalLimit = attempts.filter((a) => a.external_limit_hit === true);
  const finishCounts = {};
  for (const attempt of attempts) {
    const key = String(attempt.finish_kind ?? 'unknown');
    finishCounts[key] = (finishCounts[key] ?? 0) + 1;
  }

  const stabilityClass = classifyCharacterizationStability({
    validNaturalAttempts: validNatural,
    censoredAttempts: censored.length,
    externalLimitAttempts: externalLimit.length,
    pathologicalSignal: options.pathologicalSignal === true,
  });

  return {
    schema: CHARACTERIZATION_SUMMARY_SCHEMA,
    call_id: callId,
    inference_mode: options.inferenceMode ?? null,
    valid_natural_attempt_count: validNatural.length,
    censored_attempt_count: censored.length,
    external_limit_attempt_count: externalLimit.length,
    total_attempt_count: attempts.length,
    sampling_stop_reason: options.samplingStopReason ?? null,
    token_use: {
      input_tokens: summarizeNumeric(validNatural.map((a) => a.input_tokens)),
      reasoning_tokens: summarizeNumeric(validNatural.map((a) => a.reasoning_tokens)),
      output_tokens: summarizeNumeric(validNatural.map((a) => a.output_tokens)),
      total_tokens: summarizeNumeric(validNatural.map((a) => a.total_tokens)),
    },
    wall_clock_latency_ms: summarizeNumeric(
      validNatural.map((a) => a.inference_wall_clock_ms),
    ),
    wall_clock_measurement: validNatural.find((a) => a.timing_measurement)?.timing_measurement
      ?? 'substrate_runEphemeralInference_idle_boundary',
    finish_distribution: finishCounts,
    structured_output_success_rate: options.structuredOutputSuccessRate ?? null,
    retry_rate: options.retryRate ?? null,
    stability_class: stabilityClass,
    evidence_anchors: attempts.map((a) => a.evidence_id).filter(Boolean),
    characterization_mode: true,
    configured_production_quota: options.configuredProductionQuota ?? null,
    configured_production_reasoning: options.productionReasoningPolicy ?? null,
    model_profile: options.modelProfile ?? null,
    comparison_notes: options.comparisonNotes ?? [],
  };
}

export function characterizationRoot(rootOverride = null) {
  const envRoot = process.env.HG_DATA_DIR
    ? path.join(process.env.HG_DATA_DIR, 'llm_characterization')
    : path.resolve(process.cwd(), '..', '..', 'data', 'llm_characterization');
  return rootOverride ?? envRoot;
}

export function writeCharacterizationBatch({ batchId, manifest, summaries, root = null }) {
  const base = path.join(characterizationRoot(root), 'batches', batchId);
  fs.mkdirSync(path.join(base, 'summaries'), { recursive: true });
  fs.writeFileSync(
    path.join(base, 'manifest.json'),
    `${JSON.stringify({ schema: CHARACTERIZATION_BATCH_SCHEMA, ...manifest }, null, 2)}\n`,
  );
  for (const [callId, summary] of Object.entries(summaries)) {
    fs.writeFileSync(
      path.join(base, 'summaries', `${callId}.json`),
      `${JSON.stringify(summary, null, 2)}\n`,
    );
  }
  const indexPath = path.join(characterizationRoot(root), 'index.json');
  const index = fs.existsSync(indexPath)
    ? JSON.parse(fs.readFileSync(indexPath, 'utf8'))
    : { schema: CHARACTERIZATION_INDEX_SCHEMA, batches: {}, call_latest: {} };
  index.batches[batchId] = {
    manifest_path: path.join('batches', batchId, 'manifest.json'),
    anchor: manifest.repository_anchor ?? null,
    inference_mode: manifest.inference_mode ?? null,
    completed_at: manifest.completed_at ?? null,
  };
  for (const callId of Object.keys(summaries)) {
    const summary = summaries[callId];
    const prior = index.call_latest[callId];
    const priorMode = prior?.inference_mode ?? null;
    const nextMode = summary.inference_mode ?? manifest.inference_mode ?? null;
    const shouldReplace = !prior
      || (nextMode === 'live' && priorMode !== 'live')
      || (nextMode === priorMode);
    if (shouldReplace) {
      index.call_latest[callId] = {
        batch_id: batchId,
        inference_mode: nextMode,
        summary_path: path.join('batches', batchId, 'summaries', `${callId}.json`),
        stability_class: summary.stability_class,
      };
    }
  }
  fs.mkdirSync(path.dirname(indexPath), { recursive: true });
  fs.writeFileSync(indexPath, `${JSON.stringify(index, null, 2)}\n`);
  return { base, indexPath };
}

export function normalizeAttemptForCharacterization(attempt) {
  const health = attempt.inference_health ?? {};
  const usage = health.usage ?? attempt.response?.usage ?? {};
  const finish = health.finish_kind_raw ?? attempt.response?.finish?.kind ?? null;
  const finishClass = health.finish_class ?? null;
  const censoredReason = attempt.correlation?.censored_reason ?? attempt.censored_reason ?? null;
  const externalLimit = finishClass === 'output_limit'
    || finish === 'max-tokens'
    || finish === 'length'
    || finish === 'max_tokens';
  return {
    evidence_id: attempt.evidence_id,
    finish_kind: finish,
    finish_class: finishClass,
    input_tokens: usage.input_tokens ?? null,
    output_tokens: usage.output_tokens ?? null,
    reasoning_tokens: usage.reasoning_tokens ?? null,
    total_tokens: usage.total_tokens ?? null,
    inference_wall_clock_ms: health.timing?.inference_wall_clock_ms ?? null,
    timing_measurement: health.timing?.measurement ?? null,
    censored: Boolean(censoredReason),
    censored_reason: censoredReason,
    external_limit_hit: externalLimit,
    structured_failure: health.structural_valid === false,
    characterization_mode: health.characterization_mode === true,
    configured_max_tokens: health.configured_max_tokens ?? null,
  };
}
