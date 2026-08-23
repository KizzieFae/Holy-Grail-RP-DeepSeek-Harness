import {
  canApplyHardCorrection,
  canApplySoftChallenge,
  canGenerateCandidate,
  createCandidateBudgetState,
  recordGeneratedCandidate,
  recordHardCorrection,
  recordResidualSoftConcerns,
  recordSoftChallenge,
  setTerminalDisposition,
} from './character-candidate-budget.mjs';
import {
  buildCorrectionContextFromEvaluation,
  runSemanticEvaluation,
  summarizeCandidateForCorrection,
} from './character-semantic-evaluation.mjs';
import { characterDecisionPatch } from '../../lib/execution-evidence/phase-decision.mjs';
import { parseJsonObject } from '../../lib/inference-utils.mjs';
import { roleForCharacter } from './role-utils.mjs';

const CHAR_INFRA_RETRIES = 1;
const EVAL_INFRA_RETRIES = 1;

async function runCharacterInferenceWithInfraRetry({
  api,
  runEphemeralInference,
  scope,
  characterInferenceId,
  characterId,
  role,
  hgSceneId,
  hgRoundId,
  hgSessionId,
  attemptIndex,
  correctionContext,
  mockResponses,
  modelProfile,
  priorEvidenceId,
  prompt,
}) {
  let lastRun = null;
  for (let infraAttempt = 0; infraAttempt <= CHAR_INFRA_RETRIES; infraAttempt += 1) {
    const state = await api.getSceneState(hgSceneId);
    const expectedTurnIndex = Number(state.turn_counter ?? 0);
    const manifest = await api.prepareCharacterContext({
      hg_scene_id: hgSceneId,
      hg_round_id: hgRoundId,
      inference_id: characterInferenceId,
      character_id: characterId,
      role,
      turn_index: expectedTurnIndex,
      attempt_index: attemptIndex,
      correction_context: correctionContext ?? undefined,
    });
    const characterRun = await runEphemeralInference({
      inferenceId: `${characterInferenceId}-${attemptIndex}${infraAttempt ? '-infra-retry' : ''}`,
      prompt: prompt ?? 'Produce your character move as JSON only.',
      manifest,
      mockResponses: mockResponses.length ? [mockResponses[0]] : [],
      modelProfile,
      evidenceContext: {
        hgSessionId,
        hgSceneId,
        hgRoundId,
        role: 'character',
        characterId,
        inferenceId: characterInferenceId,
        attemptIndex,
        priorAttemptId: priorEvidenceId,
      },
    });
    lastRun = { characterRun, manifest, expectedTurnIndex };
    if (!characterRun.failed) {
      return { ok: true, ...lastRun, infraAttempt };
    }
  }
  return { ok: false, ...lastRun, infraAttempt: CHAR_INFRA_RETRIES };
}

export async function runCharacterPhase({
  runEphemeralInference,
  recorder,
  trace,
  api,
  sceneAgent,
  sceneSessionId,
  hgSessionId,
  hgSceneId,
  hgRoundId,
  characterId,
  directorDecision,
  characterInferenceId,
  mockResponses,
  mockSemanticEvaluatorResponses = [],
  characterTurnIndex,
  characterRole,
  modelProfile,
  semanticEvaluatorProfile,
  liveMaxAttempts,
  prompt,
  semanticEvaluationEnabled = true,
}) {
  const role = characterRole ?? roleForCharacter(characterId);
  let committed = false;
  let continuityTurnIndex = null;
  let domainCommitId = null;
  let characterManifestId = '';
  let characterInferenceSessionId = null;
  let characterInferenceTrace = null;
  let priorEvidenceId = null;
  let correctionContext = null;
  let semanticEvalPassIndex = 0;
  const budget = createCandidateBudgetState(liveMaxAttempts);
  const scope = { hgSessionId, hgSceneId, hgRoundId, sceneSessionId };
  const evaluatorProfile = semanticEvaluatorProfile ?? modelProfile;

  while (!committed && canGenerateCandidate(budget)) {
    const candidateSlotIndex = budget.generatedCount;
    const inferenceAttempt = await runCharacterInferenceWithInfraRetry({
      api,
      runEphemeralInference,
      scope,
      characterInferenceId,
      characterId,
      role,
      hgSceneId,
      hgRoundId,
      hgSessionId,
      attemptIndex: candidateSlotIndex,
      correctionContext,
      mockResponses: mockResponses.length ? [mockResponses[candidateSlotIndex]] : [],
      modelProfile,
      priorEvidenceId,
      prompt,
    });

    if (!inferenceAttempt.ok || !inferenceAttempt.characterRun) {
      recorder?.patchDecision(
        inferenceAttempt.characterRun?.evidenceId,
        hgSessionId,
        characterDecisionPatch({ proposed: null, outcome: 'inference_failed' }),
      );
      priorEvidenceId = inferenceAttempt.characterRun?.evidenceId ?? priorEvidenceId;
      setTerminalDisposition(budget, 'character_inference_failed');
      break;
    }

    const { characterRun, manifest, expectedTurnIndex } = inferenceAttempt;
    recordGeneratedCandidate(budget);
    characterManifestId = String(manifest.manifest_id);
    characterInferenceSessionId = characterRun.inferenceSessionId;
    characterInferenceTrace = characterRun.trace;

    let proposed;
    let parseError = null;
    try {
      proposed = parseJsonObject(characterRun.raw);
    } catch (error) {
      parseError = String(error);
      proposed = { parse_error: parseError };
    }

    trace.emit(sceneAgent.session, 'hg/move-proposed', scope, {
      inference_id: characterInferenceId,
      character_inference_session_id: characterInferenceSessionId,
      role: 'character',
      character_id: characterId,
      character_turn_index: characterTurnIndex,
      attempt_index: candidateSlotIndex,
      manifest_id: characterManifestId,
      proposed_move: proposed,
      raw_model_output: characterRun.raw,
      inference_trace: characterInferenceTrace,
    });

    const validation = await api.validateMove({
      inference_id: characterInferenceId,
      hg_scene_id: hgSceneId,
      hg_round_id: hgRoundId,
      character_id: characterId,
      role,
      turn_index: expectedTurnIndex,
      attempt_index: candidateSlotIndex,
      proposed_move: proposed,
      raw_model_output: characterRun.raw,
    });

    if (!validation.accepted) {
      recorder?.patchDecision(
        characterRun.evidenceId,
        hgSessionId,
        characterDecisionPatch({
          proposed,
          parseError,
          validation,
          outcome: 'rejected',
        }),
      );
      priorEvidenceId = characterRun.evidenceId ?? priorEvidenceId;
      trace.emit(sceneAgent.session, 'hg/move-rejected', scope, {
        inference_id: characterInferenceId,
        character_inference_session_id: characterInferenceSessionId,
        role: 'character',
        character_id: characterId,
        character_turn_index: characterTurnIndex,
        attempt_index: candidateSlotIndex,
        validation_class: String(validation.validation_class ?? 'unknown'),
        reason: String(validation.reason ?? ''),
        retryable: Boolean(validation.retryable),
      });
      if (!validation.retryable) {
        setTerminalDisposition(budget, 'objective_validation_terminal');
        break;
      }
      correctionContext = {
        source: 'objective_validation',
        validation_class: validation.validation_class,
        reason: validation.reason,
      };
      continue;
    }

    const normalizedMove = validation.normalized_move ?? proposed;
    let semanticEvalRecord = null;

    if (semanticEvaluationEnabled) {
      const evaluationPassId = `${characterInferenceId}-eval-${semanticEvalPassIndex}`;
      semanticEvalPassIndex += 1;
      let evalOutcome = null;
      for (let evalInfra = 0; evalInfra <= EVAL_INFRA_RETRIES; evalInfra += 1) {
        evalOutcome = await runSemanticEvaluation({
          api,
          runEphemeralInference,
          recorder,
          scope,
          characterInferenceId,
          characterId,
          role,
          hgSceneId,
          hgRoundId,
          hgSessionId,
          turnIndex: expectedTurnIndex,
          evaluationPassId,
          candidateMove: normalizedMove,
          rawModelOutput: characterRun.raw,
          semanticEvaluatorProfile: evaluatorProfile,
          mockSemanticResponse: mockSemanticEvaluatorResponses[candidateSlotIndex]
            ?? mockSemanticEvaluatorResponses[semanticEvalPassIndex - 1]
            ?? null,
          parentCharacterEvidenceId: characterRun.evidenceId,
          infrastructureAttempt: evalInfra,
        });
        if (!evalOutcome.infrastructureFailure) break;
      }

      if (!evalOutcome || evalOutcome.infrastructureFailure) {
        recorder?.patchDecision(
          characterRun.evidenceId,
          hgSessionId,
          characterDecisionPatch({
            proposed,
            parseError,
            validation,
            outcome: 'semantic_evaluator_failed',
            semanticEvaluation: {
              evaluator_error: evalOutcome?.evaluatorError ?? 'unknown',
            },
          }),
        );
        setTerminalDisposition(budget, 'semantic_evaluator_failed');
        break;
      }

      semanticEvalRecord = evalOutcome.result;
      const overall = String(semanticEvalRecord.overall_result ?? 'pass');
      const isHard = overall === 'reject_hard'
        || semanticEvalRecord.findings?.some((f) => f.severity === 'hard');
      const isSoft = !isHard && (
        overall === 'reject_soft'
        || semanticEvalRecord.findings?.some((f) => f.severity === 'soft')
      );

      recorder?.patchDecision(
        characterRun.evidenceId,
        hgSessionId,
        characterDecisionPatch({
          proposed,
          parseError,
          validation,
          outcome: isHard ? 'semantic_rejected_hard' : (isSoft ? 'semantic_rejected_soft' : 'semantic_passed'),
          semanticEvaluation: {
            evaluation_pass_id: evaluationPassId,
            evaluator_evidence_id: evalOutcome.evidenceId,
            result: semanticEvalRecord,
            raw_evaluator_output: evalOutcome.raw,
          },
        }),
      );

      trace.emit(sceneAgent.session, 'hg/semantic-evaluation', scope, {
        inference_id: characterInferenceId,
        evaluation_pass_id: evaluationPassId,
        character_id: characterId,
        attempt_index: candidateSlotIndex,
        overall_result: semanticEvalRecord.overall_result,
        findings: semanticEvalRecord.findings,
      });

      if (isHard) {
        if (!canApplyHardCorrection(budget) || !canGenerateCandidate(budget)) {
          setTerminalDisposition(budget, 'hard_exhausted');
          break;
        }
        recordHardCorrection(budget);
        correctionContext = buildCorrectionContextFromEvaluation(semanticEvalRecord, {
          evaluationPassId,
          priorCandidateSummary: summarizeCandidateForCorrection(normalizedMove, characterRun.raw),
        });
        priorEvidenceId = characterRun.evidenceId ?? priorEvidenceId;
        continue;
      }

      if (isSoft) {
        if (canApplySoftChallenge(budget)) {
          recordSoftChallenge(budget);
          correctionContext = buildCorrectionContextFromEvaluation(semanticEvalRecord, {
            evaluationPassId,
            priorCandidateSummary: summarizeCandidateForCorrection(normalizedMove, characterRun.raw),
          });
          priorEvidenceId = characterRun.evidenceId ?? priorEvidenceId;
          continue;
        }
        recordResidualSoftConcerns(budget, semanticEvalRecord.findings ?? []);
      }
    }

    const commit = await api.commitMove({
      inference_id: characterInferenceId,
      hg_scene_id: hgSceneId,
      hg_round_id: hgRoundId,
      character_id: characterId,
      validated_move: normalizedMove,
      director_decision: directorDecision,
      expected_turn_index: expectedTurnIndex,
    });

    if (!commit.committed) {
      const reason = String(commit.reason ?? 'commit rejected');
      const isAnchorMismatch = reason.toLowerCase().includes('turn')
        || reason.toLowerCase().includes('anchor')
        || reason.toLowerCase().includes('counter');
      recorder?.patchDecision(
        characterRun.evidenceId,
        hgSessionId,
        characterDecisionPatch({
          proposed,
          parseError,
          validation,
          outcome: 'commit_rejected',
          commit,
          semanticEvaluation: semanticEvalRecord ? { result: semanticEvalRecord } : null,
        }),
      );
      priorEvidenceId = characterRun.evidenceId ?? priorEvidenceId;
      trace.emit(sceneAgent.session, 'hg/move-rejected', scope, {
        inference_id: characterInferenceId,
        character_inference_session_id: characterInferenceSessionId,
        role: 'character',
        character_id: characterId,
        character_turn_index: characterTurnIndex,
        attempt_index: candidateSlotIndex,
        validation_class: 'continuity_anchor',
        reason,
        retryable: false,
      });
      if (isAnchorMismatch) {
        correctionContext = null;
        if (!canGenerateCandidate(budget)) {
          setTerminalDisposition(budget, 'anchor_mismatch_exhausted');
          break;
        }
        continue;
      }
      setTerminalDisposition(budget, 'commit_rejected');
      break;
    }

    committed = true;
    continuityTurnIndex = Number(commit.continuity_turn_index);
    domainCommitId = String(commit.domain_commit_id ?? '');
    recorder?.patchDecision(
      characterRun.evidenceId,
      hgSessionId,
      characterDecisionPatch({
        proposed,
        parseError,
        validation,
        outcome: 'accepted',
        commit,
        semanticEvaluation: semanticEvalRecord ? { result: semanticEvalRecord } : null,
        residualSoftConcerns: budget.residualSoftConcerns,
        terminalDisposition: 'accepted',
      }),
    );
    trace.emit(sceneAgent.session, 'hg/move-committed', scope, {
      inference_id: characterInferenceId,
      character_inference_session_id: characterInferenceSessionId,
      role: 'character',
      character_id: characterId,
      character_turn_index: characterTurnIndex,
      attempt_index: candidateSlotIndex,
      domain_commit_id: domainCommitId,
      continuity_turn_index: continuityTurnIndex,
      residual_soft_concerns: budget.residualSoftConcerns,
    });
  }

  if (!committed && !budget.terminalDisposition) {
    setTerminalDisposition(budget, 'candidate_budget_exhausted');
  }

  return {
    committed,
    continuityTurnIndex,
    domainCommitId,
    characterId,
    characterInferenceSessionId,
    characterInferenceTrace,
    characterManifestId,
    terminalDisposition: budget.terminalDisposition,
    generatedCandidateCount: budget.generatedCount,
    residualSoftConcerns: budget.residualSoftConcerns,
  };
}
