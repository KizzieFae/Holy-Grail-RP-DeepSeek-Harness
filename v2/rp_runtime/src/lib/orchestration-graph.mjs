export const ORCHESTRATION_GRAPH_SCHEMA = 'hg_orchestration_graph_v1';

/**
 * @param {object} params
 * @returns {object}
 */
export function buildOrchestrationGraph({
  nodeKind,
  graphId,
  lane = null,
  barrierIndex = null,
  predecessorSpanIds = [],
  joinMemberSpanIds = [],
  domainCommitId = null,
  characterTurnIndex = null,
}) {
  const graph = {
    schema: ORCHESTRATION_GRAPH_SCHEMA,
    node_kind: nodeKind,
    graph_id: graphId,
    predecessor_span_ids: [...(predecessorSpanIds ?? [])],
    join_member_span_ids: [...(joinMemberSpanIds ?? [])],
  };
  if (lane) graph.lane = lane;
  if (barrierIndex != null) graph.barrier_index = barrierIndex;
  if (domainCommitId) graph.domain_commit_id = domainCommitId;
  if (characterTurnIndex != null) graph.character_turn_index = characterTurnIndex;
  return graph;
}
