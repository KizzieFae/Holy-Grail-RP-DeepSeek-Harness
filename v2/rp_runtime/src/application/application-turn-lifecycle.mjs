import crypto from 'node:crypto';

export const APPLICATION_LIFECYCLE_ROLE = 'application_lifecycle';

export const LIFECYCLE_MILESTONES = {
  ROUND_BEGAN: 'round_began',
  ROUND_TERMINAL_SUCCEEDED: 'round_terminal_succeeded',
  ROUND_TERMINAL_FAILED: 'round_terminal_failed',
  CONCURRENT_SUBMIT_REJECTED: 'concurrent_submit_rejected',
  CLIENT_WAIT_EXPIRED: 'client_wait_expired',
  RECOVERY_STARTED: 'recovery_started',
  RECOVERY_TERMINAL: 'recovery_terminal',
};

export function createOperationId(input = {}) {
  const provided = input.clientOperationId ?? input.client_operation_id;
  if (provided && String(provided).trim()) {
    return String(provided).trim();
  }
  return crypto.randomUUID();
}

export function createConcurrentRoundError(kind) {
  const err = new Error(`round already in progress (${kind})`);
  err.name = 'ConcurrentRoundError';
  err.httpStatus = 409;
  err.failure = {
    category: 'concurrent_round',
    message: err.message,
    kind,
  };
  return err;
}

/**
 * @param {object} client HolyGrailApplicationClient instance fields
 */
export function buildApplicationHealthView(client) {
  const base = client.supervisor.getReadyState();
  const view = {
    ...base,
    application_status: client.status,
  };

  if (client.roundInProgress) {
    view.application_status = 'round_in_progress';
    if (client.activeRoundOperation) {
      view.active_round_operation = { ...client.activeRoundOperation };
    }
    return view;
  }

  if (client.lastRoundTerminal) {
    view.last_round_terminal = { ...client.lastRoundTerminal };
  }

  if (client.lastError) {
    view.application_status = 'error';
    view.last_error = client.lastError;
  }

  return view;
}

export function terminalMatchesOperation(terminal, operationId) {
  if (!terminal || !operationId) return false;
  return String(terminal.operation_id) === String(operationId);
}

export function buildTerminalOutcome({
  operationId,
  outcome,
  hgRoundId = null,
  failure = null,
}) {
  return {
    operation_id: operationId,
    outcome,
    hg_round_id: hgRoundId,
    completed_at: new Date().toISOString(),
    ...(failure ? { failure } : {}),
  };
}
