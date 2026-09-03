/** Unified Character candidate budget (#19). */

import {
  LIVE_CANDIDATE_CEILING,
  clampLiveCandidateLimit,
} from '../../lib/phase-execution-policy.mjs';

export const CHARACTER_CANDIDATE_CEILING = LIVE_CANDIDATE_CEILING;

export function characterCandidateLimit(liveMaxAttempts = 3) {
  return clampLiveCandidateLimit(liveMaxAttempts);
}

export function createCandidateBudgetState(liveMaxAttempts = 3) {
  const limit = characterCandidateLimit(liveMaxAttempts);
  return {
    limit,
    generatedCount: 0,
    softChallengeUsed: false,
    hardCorrectionCount: 0,
    residualSoftConcerns: [],
    terminalDisposition: null,
  };
}

export function canGenerateCandidate(budget) {
  return budget.generatedCount < budget.limit;
}

export function recordGeneratedCandidate(budget) {
  budget.generatedCount += 1;
}

export function canApplyHardCorrection(budget) {
  return budget.hardCorrectionCount < 2 && canGenerateCandidate(budget);
}

export function recordHardCorrection(budget) {
  budget.hardCorrectionCount += 1;
}

export function canApplySoftChallenge(budget) {
  return !budget.softChallengeUsed;
}

export function recordSoftChallenge(budget) {
  budget.softChallengeUsed = true;
}

export function recordResidualSoftConcerns(budget, concerns) {
  budget.residualSoftConcerns = Array.isArray(concerns) ? [...concerns] : [];
}

export function setTerminalDisposition(budget, disposition) {
  budget.terminalDisposition = disposition;
}
