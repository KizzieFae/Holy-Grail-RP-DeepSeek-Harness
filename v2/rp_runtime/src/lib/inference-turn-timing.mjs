/**
 * DSH session turn-boundary timing for ephemeral inference (#158).
 */

export const DSH_SESSION_TURN_BOUNDARY = 'dsh_session_turn_boundary';

/**
 * @param {readonly object[]} events
 * @returns {number}
 */
export function baselineLastTurn(events) {
  const list = [...events];
  for (let i = list.length - 1; i >= 0; i -= 1) {
    const event = list[i];
    if (event?.type === 'turn/start' && Number.isFinite(Number(event.data?.turn))) {
      return Number(event.data.turn);
    }
  }
  return 0;
}

/**
 * @param {readonly object[]} events
 * @param {number} expectedTurn
 * @returns {object|null}
 */
export function findTurnStart(events, expectedTurn) {
  return [...events].find(
    (event) => event?.type === 'turn/start' && Number(event.data?.turn) === expectedTurn,
  ) ?? null;
}

/**
 * @param {readonly object[]} events
 * @param {number} expectedTurn
 * @returns {object|null}
 */
export function findTurnEnd(events, expectedTurn) {
  return [...events].find(
    (event) => event?.type === 'turn/end' && Number(event.data?.turn) === expectedTurn,
  ) ?? null;
}

/**
 * Wait for the next turn/start emitted after followup (or after optional snapshot length).
 * @param {object} agent
 * @param {{ afterEventCount?: number, pollMs?: number, timeoutMs?: number }} [options]
 */
export async function waitForTurnStart(agent, options = {}) {
  const pollMs = Number(options.pollMs ?? 10);
  const timeoutMs = Number(options.timeoutMs ?? 600_000);
  const afterEventCount = Number(options.afterEventCount ?? agent.session.events.length);
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const events = agent.session.events;
    for (let i = afterEventCount; i < events.length; i += 1) {
      const event = events[i];
      if (event?.type === 'turn/start' && Number.isFinite(Number(event.data?.turn))) {
        return Number(event.data.turn);
      }
    }
    await new Promise((resolve) => setTimeout(resolve, pollMs));
  }
  throw new Error(`turn/start not observed on agent ${agent.id}`);
}

/**
 * Wait until matching turn/end appears in the agent session log.
 * @param {object} agent
 * @param {number} expectedTurn
 * @param {{ pollMs?: number, timeoutMs?: number }} [options]
 */
export async function waitForTurnEnd(agent, expectedTurn, options = {}) {
  const pollMs = Number(options.pollMs ?? 10);
  const timeoutMs = Number(options.timeoutMs ?? 600_000);
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const endEvent = findTurnEnd(agent.session.events, expectedTurn);
    if (endEvent) return endEvent;
    await new Promise((resolve) => setTimeout(resolve, pollMs));
  }
  throw new Error(`turn/end not observed for turn ${expectedTurn} on agent ${agent.id}`);
}

/**
 * @param {readonly object[]} events
 * @param {number} expectedTurn
 * @param {string|null} [inferenceSessionId]
 * @returns {object}
 */
export function extractTurnBoundaryTiming(events, expectedTurn, inferenceSessionId = null) {
  const start = findTurnStart(events, expectedTurn);
  const end = findTurnEnd(events, expectedTurn);
  if (!start || !end) {
    return {
      timing_observed: false,
      measurement: DSH_SESSION_TURN_BOUNDARY,
      unavailable_reason: !start ? 'turn_start_not_observed' : 'turn_end_not_observed',
      dsh_turn: expectedTurn,
      dsh_inference_session_id: inferenceSessionId,
    };
  }
  const startMs = Number(start.time);
  const endMs = Number(end.time);
  const wallMs = Number.isFinite(startMs) && Number.isFinite(endMs) && endMs >= startMs
    ? endMs - startMs
    : null;
  if (wallMs == null) {
    return {
      timing_observed: false,
      measurement: DSH_SESSION_TURN_BOUNDARY,
      unavailable_reason: 'turn_event_time_invalid',
      dsh_turn: expectedTurn,
      dsh_inference_session_id: inferenceSessionId,
      turn_start_seq: start.seq ?? null,
      turn_end_seq: end.seq ?? null,
    };
  }
  return {
    timing_observed: true,
    measurement: DSH_SESSION_TURN_BOUNDARY,
    started_at: new Date(startMs).toISOString(),
    ended_at: new Date(endMs).toISOString(),
    inference_wall_clock_ms: wallMs,
    dsh_turn: expectedTurn,
    dsh_inference_session_id: inferenceSessionId,
    turn_start_seq: start.seq ?? null,
    turn_end_seq: end.seq ?? null,
  };
}

/**
 * Optional diagnostic only — not authoritative inference duration.
 * @param {number} idleBoundaryMs
 */
export function idleBoundaryDiagnostic(idleBoundaryMs) {
  if (!Number.isFinite(Number(idleBoundaryMs)) || Number(idleBoundaryMs) < 0) {
    return null;
  }
  return {
    idle_boundary_ms: Number(idleBoundaryMs),
    measurement: 'substrate_runEphemeralInference_idle_boundary',
    authoritative: false,
  };
}
