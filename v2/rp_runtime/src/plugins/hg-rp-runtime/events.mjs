/** Holy Grail execution-event helpers (log-only; never imply canon). */

export const HG_EVENT_TYPES = [
  'hg/round-started',
  'hg/director-proposed',
  'hg/director-rejected',
  'hg/director-accepted',
  'hg/move-proposed',
  'hg/move-rejected',
  'hg/move-committed',
  'hg/narrator-started',
  'hg/narrator-completed',
  'hg/narrator-failed',
  'hg/round-completed',
];

export function appendHgEvent(session, type, data) {
  return session.append(type, data);
}

export function baseCorrelation(fields) {
  return {
    hg_scene_id: fields.hg_scene_id,
    hg_round_id: fields.hg_round_id,
    dsh_scene_session_id: fields.dsh_scene_session_id,
  };
}
