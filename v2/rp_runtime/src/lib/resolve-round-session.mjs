/**
 * Resolve durable Holy Grail session identity for round orchestration.
 *
 * @param {ReturnType<import('./domain-api-client.mjs').createDomainApiClient>} api
 * @param {{ session?: { mode: string, cast?: string[], location?: string, hg_session_id?: string } }} options
 */
export async function resolveRoundSession(api, options) {
  const session = options.session;
  if (!session?.mode) {
    throw new Error('runRound requires session: { mode: "create" | "open", ... }');
  }
  if (session.mode === 'create') {
    const created = await api.createSession({
      cast: session.cast ?? ['Alice', 'Bob'],
      location: session.location ?? 'Workshop',
      hg_session_id: session.hg_session_id,
    });
    return {
      hgSessionId: String(created.hg_session_id),
      hgSceneId: String(created.hg_scene_id),
      continuityVersion: Number(created.continuity_version ?? 0),
      turnCounter: Number(created.turn_counter ?? 0),
    };
  }
  if (session.mode === 'open') {
    const hgSessionId = session.hg_session_id;
    if (!hgSessionId) {
      throw new Error('session.mode "open" requires hg_session_id');
    }
    const opened = await api.openSession(hgSessionId);
    return {
      hgSessionId: String(opened.hg_session_id),
      hgSceneId: String(opened.hg_scene_id),
      continuityVersion: Number(opened.continuity_version ?? 0),
      turnCounter: Number(opened.turn_counter ?? 0),
    };
  }
  throw new Error(`unsupported session.mode: ${session.mode}`);
}
