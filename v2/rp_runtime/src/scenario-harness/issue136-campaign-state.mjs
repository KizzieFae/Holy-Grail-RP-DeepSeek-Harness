/**
 * Issue #136 Tier-2 campaign stop-state machine (validation tooling only).
 */

export const CampaignRunState = {
  RUNNING: 'running',
  STOPPED: 'stopped',
  COMPLETED: 'completed',
};

export const DeterministicStopClass = {
  SAFETY_GUARD_EXHAUSTED: 'safety_guard_exhausted',
  FIXTURE_AUTHORITY_INSTALL_FAILURE: 'fixture_authority_install_failure',
  HOST_PREPARE_FAILURE: 'host_prepare_failure',
  STORYTELLER_INFRASTRUCTURE_SIGNATURE: 'storyteller_infrastructure_signature',
  SENTINEL_HOST_FAILURE: 'sentinel_host_failure',
  EXPANSION_GATE: 'expansion_gate',
};

/** Historical pre-#142 Storyteller finalize signature (defensive regression detection). */
export const HISTORICAL_STORYTELLER_HTTP_400_SIGNATURE = 'dict(string)';

const HOST_PREPARE_MARKERS = [
  'context prepare',
  'prepare_character',
  'host_prepare',
  'context_prepare_failed',
];

const SCHEMA_ONLY_MARKERS = [
  'move_schema_version',
  'unknown fields on',
  'invalid beat type',
  'prohibited root key',
  'beats must be a non-empty array',
  'semantic_evaluation.decision must be',
  '"description"',
  '"key"',
];

export function classifyDeterministicInfrastructureFailure(error) {
  const message = String(error?.message ?? error ?? '');
  const lower = message.toLowerCase();

  if (
    lower.includes('campaign_run_limit_exceeded')
    || lower.includes('campaign_inference_limit_exceeded')
    || lower.includes('campaign_stopped:')
  ) {
    return DeterministicStopClass.SAFETY_GUARD_EXHAUSTED;
  }
  if (
    lower.includes('fixture_authority')
    || lower.includes('missing_issue136_card')
    || lower.includes('install_issue136')
  ) {
    return DeterministicStopClass.FIXTURE_AUTHORITY_INSTALL_FAILURE;
  }
  if (HOST_PREPARE_MARKERS.some((marker) => lower.includes(marker))) {
    return DeterministicStopClass.HOST_PREPARE_FAILURE;
  }
  if (
    message.includes(HISTORICAL_STORYTELLER_HTTP_400_SIGNATURE)
    || (lower.includes('storyteller') && lower.includes('http 400'))
  ) {
    return DeterministicStopClass.STORYTELLER_INFRASTRUCTURE_SIGNATURE;
  }
  if (lower.includes('issue136-sentinel') && lower.includes('host')) {
    return DeterministicStopClass.SENTINEL_HOST_FAILURE;
  }
  return null;
}

function characterTurnCommitted(turn) {
  return turn?.committed === true || Boolean(turn?.domain_commit_id);
}

function attemptLooksSchemaOnly(attempt) {
  const text = [
    attempt?.outcome,
    attempt?.semantic_evaluation?.error,
    attempt?.semantic_evaluation?.evaluator_error,
    attempt?.candidate_text,
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();
  if (!text) return false;
  return SCHEMA_ONLY_MARKERS.some((marker) => text.includes(marker));
}

/**
 * Post-run expansion gate: stop when all reps for a fixture complete with zero
 * commits and only schema/ingress signatures (not arbitrary semantic counts).
 */
export function evaluateExpansionGate({ fixtureId, fixtureResults, repetitions }) {
  if (!Array.isArray(fixtureResults) || fixtureResults.length < repetitions) {
    return null;
  }
  let anyCommit = false;
  let sawFailure = false;
  let onlySchemaFailures = true;

  for (const run of fixtureResults) {
    const turns = run?.forensic?.character_turns ?? [];
    for (const turn of turns) {
      if (characterTurnCommitted(turn)) {
        anyCommit = true;
      }
      const qaChain = turn?.qa_chain ?? [];
      for (const attempt of qaChain) {
        if (attempt?.accepted === true) {
          anyCommit = true;
        }
        if (attempt?.accepted === false || attempt?.outcome) {
          sawFailure = true;
          if (!attemptLooksSchemaOnly(attempt)) {
            onlySchemaFailures = false;
          }
        }
      }
    }
  }

  if (!anyCommit && sawFailure && onlySchemaFailures) {
    return `${DeterministicStopClass.EXPANSION_GATE}:fixture=${fixtureId}:zero_commits_schema_only`;
  }
  return null;
}

export class Issue136CampaignStateMachine {
  constructor(campaignLimits) {
    this.limits = campaignLimits;
    this.state = CampaignRunState.RUNNING;
    this.stopReason = null;
    this.stopClass = null;
  }

  stop(stopClass, detail = null) {
    if (this.state !== CampaignRunState.RUNNING) return;
    this.state = CampaignRunState.STOPPED;
    this.stopClass = stopClass;
    this.stopReason = detail ? `${stopClass}:${detail}` : stopClass;
    this.limits?.stop?.(this.stopReason);
  }

  complete() {
    if (this.state === CampaignRunState.RUNNING) {
      this.state = CampaignRunState.COMPLETED;
    }
  }

  shouldScheduleMore() {
    return this.state === CampaignRunState.RUNNING && !this.limits?.stopped;
  }

  snapshot() {
    return {
      state: this.state,
      stop_reason: this.stopReason,
      stop_class: this.stopClass,
      limits: this.limits?.snapshot?.() ?? null,
    };
  }
}
