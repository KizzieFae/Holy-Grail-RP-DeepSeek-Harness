import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

import { execSync } from 'node:child_process';

import { resolveCatalogApplicationTokenQuota, resolveCatalogProductionProfile, resolveCatalogReasoningPolicy } from '../src/application/llm-call-catalog-policy.mjs';
import { findCatalogEntry } from '../src/application/llm-call-catalog.mjs';
import { createHolyGrailRpContext } from '../src/bootstrap.mjs';
import { executionEvidenceRoot } from '../src/lib/execution-evidence/config.mjs';
import {
  aggregateCallCharacterizationSummary,
  characterizationRoot,
  normalizeAttemptForCharacterization,
  writeCharacterizationBatch,
} from '../src/lib/llm-characterization/aggregate.mjs';
import { getCharacterizationFixture, listPrimaryCharacterizationFixtures } from '../src/lib/llm-characterization/fixtures.mjs';
import {
  CHARACTERIZATION_BASELINE_ATTEMPTS,
  CHARACTERIZATION_MAX_ATTEMPTS,
  collectExpansionSignals,
  isValidNaturalCompletionAttempt,
  shouldExpandCharacterizationSampling,
  shouldStopCharacterizationSampling,
} from '../src/lib/llm-characterization/sampling.mjs';
import { HG_DEEPSEEK_DEFAULT_MODEL, HG_DEEPSEEK_PROVIDER } from '../src/lib/inference-profile.mjs';
import { createInferenceSubstrate } from '../src/plugins/hg-phase-executors/inference-substrate.mjs';
import { ExecutionEvidenceStore } from '../src/lib/execution-evidence/store.mjs';

/** Per-attempt safety timeout; generous for long env-cognition / plot paths (#152). */
export const CHARACTERIZATION_ATTEMPT_TIMEOUT_MS = 600_000;

function repositoryAnchor() {
  try {
    return execSync('git rev-parse HEAD', { encoding: 'utf8' }).trim();
  } catch {
    return null;
  }
}

function assertLiveInferenceAvailable() {
  if (!process.env.DEEPSEEK_API_KEY?.trim()) {
    throw new Error('DEEPSEEK_API_KEY not set; live characterization requires provider credentials');
  }
}

async function runAttemptWithTimeout(substrate, ctx, params, timeoutMs) {
  let timer = null;
  try {
    return await Promise.race([
      substrate.runEphemeralInference(ctx, params),
      new Promise((_, reject) => {
        timer = setTimeout(() => {
          reject(new Error(`characterization harness timeout after ${timeoutMs}ms`));
        }, timeoutMs);
      }),
    ]);
  } catch (error) {
    if (String(error?.message ?? '').includes('harness timeout')) {
      return {
        evidenceId: null,
        censored: true,
        censored_reason: 'harness_timeout',
        inferenceWallClockMs: timeoutMs,
      };
    }
    throw error;
  } finally {
    if (timer) clearTimeout(timer);
  }
}

async function runCallCharacterization(ctx, substrate, sessionId, callId, settings, options) {
  const fixture = getCharacterizationFixture(callId);
  const entry = findCatalogEntry(callId);
  const productionQuota = resolveCatalogApplicationTokenQuota(entry, settings, {});
  const profile = resolveCatalogProductionProfile(entry, settings, {});
  const reasoningPolicy = resolveCatalogReasoningPolicy(entry, settings);
  const attempts = [];
  let consecutiveNonNatural = 0;
  let failureSignature = null;
  let failureSignatureCount = 0;
  let samplingStopReason = null;

  while (attempts.length < CHARACTERIZATION_MAX_ATTEMPTS) {
    const inferenceId = `char-${callId}-${attempts.length}`;
    const run = await runAttemptWithTimeout(
      substrate,
      ctx,
      {
        inferenceId,
        prompt: fixture.prompt,
        manifest: fixture.manifest,
        mockResponses: options.inferenceMode === 'mock' ? fixture.mockResponses : [],
        modelProfile: profile,
        evidenceContext: {
          hgSessionId: sessionId,
          hgSceneId: sessionId,
          hgRoundId: `char-round-${callId}`,
          role: entry.role_agent,
          inferenceKind: fixture.inferenceKind,
          inferenceId,
          attemptIndex: attempts.length,
        },
      },
      options.attemptTimeoutMs ?? CHARACTERIZATION_ATTEMPT_TIMEOUT_MS,
    );

    let normalized;
    if (run.censored) {
      normalized = {
        evidence_id: null,
        finish_kind: 'harness_timeout',
        censored: true,
        censored_reason: run.censored_reason ?? 'harness_timeout',
        external_limit_hit: false,
        structured_failure: false,
        inference_wall_clock_ms: run.inferenceWallClockMs ?? null,
        timing_measurement: 'characterization_harness_timeout',
      };
    } else {
      const store = new ExecutionEvidenceStore(substrate.recorder.store.root);
      const attemptRecord = store.readAttempt(sessionId, run.evidenceId);
      normalized = normalizeAttemptForCharacterization(attemptRecord);
    }
    attempts.push(normalized);

    if (isValidNaturalCompletionAttempt(normalized)) {
      consecutiveNonNatural = 0;
    } else {
      consecutiveNonNatural += 1;
      const signature = `${normalized.finish_kind}:${normalized.censored_reason ?? 'none'}`;
      if (signature === failureSignature) failureSignatureCount += 1;
      else {
        failureSignature = signature;
        failureSignatureCount = 1;
      }
    }

    const validCount = attempts.filter((a) => isValidNaturalCompletionAttempt(a)).length;
    const stop = shouldStopCharacterizationSampling({
      totalAttempts: attempts.length,
      consecutiveNonNatural,
      failureSignatureCount,
    });
    if (stop.stop) {
      samplingStopReason = stop.reason;
      break;
    }
    if (validCount >= CHARACTERIZATION_BASELINE_ATTEMPTS) {
      const expand = shouldExpandCharacterizationSampling(
        validCount,
        attempts.length,
        collectExpansionSignals(attempts),
      );
      if (!expand) {
        samplingStopReason = 'baseline_met';
        break;
      }
    }
  }

  if (!samplingStopReason && attempts.length >= CHARACTERIZATION_MAX_ATTEMPTS) {
    samplingStopReason = 'max_attempts';
  }

  const comparisonNotes = [];
  if (callId === 'narrator_environment_cognition') {
    comparisonNotes.push(
      'Compare to capped motivating evidence c73d368c-7c33-4e53-b0e9-18aedc3c2c11 (8192 HG quota, max-tokens, empty structured output).',
    );
  }

  return aggregateCallCharacterizationSummary(callId, attempts, {
    inferenceMode: options.inferenceMode,
    configuredProductionQuota: productionQuota,
    comparisonNotes,
    samplingStopReason,
    productionReasoningPolicy: reasoningPolicy,
    modelProfile: {
      provider: profile?.provider ?? HG_DEEPSEEK_PROVIDER,
      model: profile?.model ?? HG_DEEPSEEK_DEFAULT_MODEL,
      reasoning_effort: profile?.reasoningEffort ?? reasoningPolicy,
    },
  });
}

export async function runCharacterizationBatch(options = {}) {
  const inferenceMode = options.inferenceMode ?? (process.argv.includes('--live') ? 'live' : 'mock');
  if (inferenceMode === 'live') {
    assertLiveInferenceAvailable();
  }

  const prevChar = process.env.HG_INFERENCE_CHARACTERIZATION;
  const prevCal = process.env.HG_INFERENCE_CALIBRATION;
  process.env.HG_INFERENCE_CHARACTERIZATION = '1';
  delete process.env.HG_INFERENCE_CALIBRATION;

  const batchId = options.batchId ?? `batch-${crypto.randomUUID()}`;
  const sessionId = options.sessionId ?? `hg-session-char-${crypto.randomUUID()}`;
  const evidenceRoot = options.evidenceRoot ?? executionEvidenceRoot();
  const charRoot = options.characterizationRoot ?? characterizationRoot(options.characterizationRoot);
  const callIds = options.callIds ?? listPrimaryCharacterizationFixtures();

  const settings = { inferenceMode, roleRouting: 'simple' };

  const { ctx } = await createHolyGrailRpContext(
    inferenceMode === 'live' ? { inference: { mountDeepSeek: true } } : {},
  );
  const substrate = createInferenceSubstrate({
    inferenceMode,
    inferenceCharacterization: true,
    executionEvidence: { enabled: true, root: evidenceRoot },
  });

  try {
    const summaries = {};
    for (const callId of callIds) {
      process.stderr.write(`[characterization:${inferenceMode}] ${callId} (${callIds.indexOf(callId) + 1}/${callIds.length})\n`);
      summaries[callId] = await runCallCharacterization(
        ctx,
        substrate,
        sessionId,
        callId,
        settings,
        { inferenceMode, attemptTimeoutMs: options.attemptTimeoutMs },
      );
    }

    const manifest = {
      batch_id: batchId,
      repository_anchor: options.repositoryAnchor ?? repositoryAnchor(),
      characterization_mode: 'HG_INFERENCE_CHARACTERIZATION=1',
      inference_mode: inferenceMode,
      model_provider: inferenceMode === 'live' ? HG_DEEPSEEK_PROVIDER : 'hg-mock',
      default_model: inferenceMode === 'live' ? HG_DEEPSEEK_DEFAULT_MODEL : 'deterministic-v2',
      production_policy_authority: 'v2/rp_runtime/src/application/application-settings.mjs',
      execution_evidence_session_id: sessionId,
      execution_evidence_root: evidenceRoot,
      execution_evidence_session_path: path.join(evidenceRoot, sessionId),
      attempt_timeout_ms: options.attemptTimeoutMs ?? CHARACTERIZATION_ATTEMPT_TIMEOUT_MS,
      wall_clock_measurement: 'substrate_runEphemeralInference_idle_boundary',
      call_coverage: callIds,
      completed_at: new Date().toISOString(),
    };
    writeCharacterizationBatch({
      batchId,
      manifest,
      summaries,
      root: charRoot,
    });
    return { batchId, summaries, manifest, evidenceRoot, characterizationRoot: charRoot };
  } finally {
    await ctx.fiber.dispose();
    if (prevChar === undefined) delete process.env.HG_INFERENCE_CHARACTERIZATION;
    else process.env.HG_INFERENCE_CHARACTERIZATION = prevChar;
    if (prevCal === undefined) delete process.env.HG_INFERENCE_CALIBRATION;
    else process.env.HG_INFERENCE_CALIBRATION = prevCal;
  }
}

const isMain = process.argv[1] && import.meta.url.endsWith(process.argv[1].replace(/\\/g, '/'));
if (isMain || (process.argv[1] && process.argv[1].includes('run-llm-characterization-batch.mjs'))) {
  runCharacterizationBatch({ inferenceMode: process.argv.includes('--live') ? 'live' : 'mock' })
    .then((result) => {
      console.log(JSON.stringify({
        batch_id: result.batchId,
        inference_mode: result.manifest.inference_mode,
        characterization_root: result.characterizationRoot,
        execution_evidence_session_id: result.manifest.execution_evidence_session_id,
        call_count: Object.keys(result.summaries).length,
      }, null, 2));
    })
    .catch((error) => {
      console.error(error);
      process.exitCode = 1;
    });
}
