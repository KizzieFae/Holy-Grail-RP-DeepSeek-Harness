/**
 * Issue #136 bounded Character-only live structural validation (not Tier-2 campaign).
 */
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { createHolyGrailRpContext } from '../bootstrap.mjs';
import { createDomainApiClient } from '../lib/domain-api-client.mjs';
import { deepseekInferenceProfile } from '../lib/inference-profile.mjs';
import { LIVE_INFERENCE_TRANSPORT_PROMPT } from '../lib/live-inference-prompts.mjs';
import { parseJsonObject } from '../lib/inference-utils.mjs';
import { repoRoot } from '../lib/runtime-config.mjs';
import { installIssue136ValidationCards, loadIssue136TruthFixture } from './issue136-fixture-truth.mjs';
import { startHarnessRuntime } from './harness-runtime.mjs';
import { directorFor } from './inference-mocks.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = repoRoot;

function extractContractProvenance(manifest) {
  const structural = (manifest?.contributions ?? []).find(
    (c) => String(c.contribution_id ?? '').endsWith('-response-contract'),
  );
  const behavioral = (manifest?.contributions ?? []).find(
    (c) => String(c.contribution_id ?? '').endsWith('-instruction'),
  );
  return {
    structural_contribution_id: structural?.contribution_id ?? null,
    behavioral_contribution_id: behavioral?.contribution_id ?? null,
    response_contract_revision: structural?.provenance?.response_contract_revision ?? null,
    response_contract_digest: structural?.provenance?.response_contract_digest ?? null,
    contribution_ids: (manifest?.contributions ?? []).map((c) => c.contribution_id),
  };
}

function summarizeParsedMove(parsed) {
  const beats = Array.isArray(parsed?.beats) ? parsed.beats : [];
  return {
    move_schema_version_present: parsed?.move_schema_version === 2,
    beat_field_shapes: beats.map((beat) => Object.keys(beat ?? {})),
    motivation_keys: parsed?.motivation ? Object.keys(parsed.motivation) : [],
    semantic_evaluation_decision: parsed?.semantic_evaluation?.decision ?? null,
  };
}

export async function runIssue136CharacterLiveSlice({
  fixtureId = '136-T2-A-STABILITY',
  maxAttempts = 3,
  dataDir = null,
  candidateSha = null,
} = {}) {
  if (!process.env.DEEPSEEK_API_KEY?.trim()) {
    throw new Error('DEEPSEEK_API_KEY not set');
  }

  const rootDir = dataDir ?? path.join(
    REPO_ROOT,
    'data',
    'issue136_character_live_slice',
    new Date().toISOString().replace(/[:.]/g, '-'),
  );
  fs.mkdirSync(rootDir, { recursive: true });

  const runtime = await startHarnessRuntime({
    dataDir: rootDir,
    sessionsDir: path.join(rootDir, 'sessions'),
    forensicsDir: path.join(rootDir, 'forensics'),
    executionEvidence: true,
  });

  const rpBundle = await createHolyGrailRpContext({
    domainApi: { baseUrl: runtime.baseUrl },
    inference: {
      mountDeepSeek: true,
      executionEvidence: {
        enabled: true,
        root: path.join(rootDir, 'execution_evidence'),
      },
    },
  });

  const domainApi = createDomainApiClient(runtime.baseUrl);
  installIssue136ValidationCards(rootDir);
  const truth = loadIssue136TruthFixture(fixtureId);
  const characterId = truth.character_id;
  const role = 'guest';
  const directorDecision = JSON.parse(directorFor(characterId));
  const modelProfile = deepseekInferenceProfile({ reasoningEffort: 'low', maxTokens: 1024 });
  const inferenceId = `issue136-live-${crypto.randomUUID()}`;

  const attempts = [];
  let committed = false;
  let domainCommitId = null;
  let continuityTurnIndex = null;
  let providerFailure = null;
  let inferenceTrace = null;

  try {
    const session = await domainApi.createSession({
      characters: truth.character_cards,
      opening: { mode: 'custom', text: truth.scene_stimulus },
      location: 'Workshop',
      memory_scope_id: `issue136-live-${crypto.randomUUID()}`,
      plot_cognition_scope_id: `issue136-live-pc-${crypto.randomUUID()}`,
    });
    const round = await domainApi.startRound({ hg_scene_id: session.hg_scene_id });
    const beforeState = await domainApi.getSceneState(session.hg_scene_id);
    const expectedTurnIndex = Number(beforeState.turn_counter ?? 0);

    for (let attemptIndex = 0; attemptIndex < maxAttempts && !committed; attemptIndex += 1) {
      const manifest = await domainApi.prepareCharacterContext({
        hg_scene_id: session.hg_scene_id,
        hg_round_id: round.hg_round_id,
        inference_id: inferenceId,
        character_id: characterId,
        role,
        turn_index: expectedTurnIndex,
        attempt_index: attemptIndex,
        director_decision: directorDecision,
      });
      const provenance = extractContractProvenance(manifest);

      const inferenceRun = await rpBundle.phaseExecutors.runEphemeralInference({
        inferenceId: `${inferenceId}-${attemptIndex}`,
        prompt: LIVE_INFERENCE_TRANSPORT_PROMPT,
        manifest,
        modelProfile,
        evidenceContext: {
          hgSessionId: session.hg_session_id,
          hgSceneId: session.hg_scene_id,
          hgRoundId: round.hg_round_id,
          role: 'character',
          characterId,
          inferenceId,
          attemptIndex,
        },
      });
      inferenceTrace = inferenceRun.trace;

      if (inferenceRun.failed) {
        providerFailure = inferenceRun.failure;
        attempts.push({
          attempt_index: attemptIndex,
          ...provenance,
          provider: inferenceTrace?.provider ?? modelProfile.provider,
          model: inferenceTrace?.model ?? modelProfile.model,
          reasoning_effort: inferenceTrace?.reasoning_effort ?? modelProfile.reasoningEffort,
          ingress_accepted: false,
          ingress_reason: 'inference_failed',
          committed: false,
          raw_preview: String(inferenceRun.raw ?? '').slice(0, 500),
        });
        break;
      }

      let proposed;
      try {
        proposed = parseJsonObject(inferenceRun.raw);
      } catch (error) {
        proposed = { parse_error: String(error) };
      }

      const validation = await domainApi.validateMove({
        inference_id: inferenceId,
        hg_scene_id: session.hg_scene_id,
        hg_round_id: round.hg_round_id,
        character_id: characterId,
        role,
        turn_index: expectedTurnIndex,
        attempt_index: attemptIndex,
        proposed_move: proposed,
        raw_model_output: inferenceRun.raw,
      });

      const attemptRecord = {
        attempt_index: attemptIndex,
        ...provenance,
        provider: inferenceTrace?.provider ?? modelProfile.provider,
        model: inferenceTrace?.model ?? modelProfile.model,
        reasoning_effort: inferenceTrace?.reasoning_effort ?? modelProfile.reasoningEffort,
        ...summarizeParsedMove(proposed),
        ingress_accepted: validation.accepted === true,
        ingress_reason: validation.reason ?? null,
        committed: false,
        raw_preview: String(inferenceRun.raw ?? '').slice(0, 500),
      };

      if (!validation.accepted) {
        attempts.push(attemptRecord);
        continue;
      }

      const commit = await domainApi.commitMove({
        inference_id: inferenceId,
        hg_scene_id: session.hg_scene_id,
        hg_round_id: round.hg_round_id,
        character_id: characterId,
        validated_move: validation.normalized_move ?? proposed,
        director_decision: directorDecision,
        expected_turn_index: expectedTurnIndex,
      }).catch((error) => ({
        committed: false,
        reason: String(error?.message ?? error),
        commit_error: true,
      }));

      if (commit.committed) {
        committed = true;
        domainCommitId = commit.domain_commit_id ?? null;
        continuityTurnIndex = commit.continuity_turn_index ?? null;
        attemptRecord.committed = true;
      } else if (commit.commit_error) {
        attemptRecord.commit_error = commit.reason;
      }
      attempts.push(attemptRecord);
    }
  } finally {
    await rpBundle.ctx.fiber.dispose();
    await runtime.dispose();
  }

  const report = {
    schema: 'issue136_character_live_slice_v1',
    candidate_sha: candidateSha,
    fixture_id: fixtureId,
    character_id: characterId,
    provider: modelProfile.provider,
    model: modelProfile.model,
    reasoning_effort: modelProfile.reasoningEffort,
    transport_prompt: LIVE_INFERENCE_TRANSPORT_PROMPT,
    committed,
    attempts,
    slice_result: {
      domain_commit_id: domainCommitId,
      continuity_turn_index: continuityTurnIndex,
      provider_failure: providerFailure,
      inference_trace_manifest_id: inferenceTrace?.manifest_id ?? null,
    },
    data_dir: rootDir,
  };
  const reportPath = path.join(rootDir, 'character-live-slice-report.json');
  fs.writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`, 'utf8');
  return { ...report, report_path: reportPath };
}

if (process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1])) {
  const candidateSha = process.env.ISSUE136_CANDIDATE_SHA ?? null;
  runIssue136CharacterLiveSlice({ candidateSha })
    .then((report) => {
      process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
    })
    .catch((error) => {
      console.error(error);
      process.exitCode = 1;
    });
}
