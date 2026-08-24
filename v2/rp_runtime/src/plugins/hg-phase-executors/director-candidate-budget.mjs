/** Director selection attempt budget (#26). */

export const DIRECTOR_SELECTION_CEILING = 3;

export function directorSelectionLimit(liveMaxAttempts = 3) {
  const configured = Number(liveMaxAttempts ?? DIRECTOR_SELECTION_CEILING);
  if (!Number.isFinite(configured) || configured < 1) {
    return 1;
  }
  return Math.min(configured, DIRECTOR_SELECTION_CEILING);
}

export function createDirectorSelectionBudget(liveMaxAttempts = 3) {
  const limit = directorSelectionLimit(liveMaxAttempts);
  return {
    limit,
    attemptsUsed: 0,
    softRegenerationUsed: false,
    retentionEligibleCandidate: null,
    residualSoftConcerns: [],
    terminalDisposition: null,
  };
}

export function canContinueSelection(budget) {
  return budget.attemptsUsed < budget.limit;
}

export function recordDirectorAttempt(budget) {
  budget.attemptsUsed += 1;
}

export function canApplySoftRegeneration(budget) {
  return !budget.softRegenerationUsed && canContinueSelection(budget);
}

export function recordSoftRegeneration(budget) {
  budget.softRegenerationUsed = true;
}

export function setRetentionEligible(budget, candidate) {
  budget.retentionEligibleCandidate = candidate ?? null;
}

export function clearRetention(budget, { evidenceId = null } = {}) {
  if (!budget.retentionEligibleCandidate) return;
  if (!evidenceId || budget.retentionEligibleCandidate.evidenceId === evidenceId) {
    budget.retentionEligibleCandidate = null;
  }
}

export function recordResidualSoftConcerns(budget, concerns) {
  budget.residualSoftConcerns = Array.isArray(concerns) ? [...concerns] : [];
}

export function setTerminalDisposition(budget, disposition) {
  budget.terminalDisposition = disposition;
}
