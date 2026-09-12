import crypto from 'node:crypto';

import { buildOrchestrationGraph } from './orchestration-graph.mjs';

function collectEvidenceIds(lane, result) {
  const ids = [];
  if (lane === 'narrator') {
    if (result?.narrator_evidence_id) ids.push(result.narrator_evidence_id);
  }
  if (lane === 'librarian') {
    const proposalId = result?.generationResult?.proposalEvidenceId
      ?? result?.generationResult?.inferRun?.evidenceId
      ?? null;
    if (proposalId) ids.push(proposalId);
  }
  if (lane === 'plot_cognition') {
    const plotId = result?.updateResult?.inferenceEvidenceId
      ?? result?.updateResult?.inferRun?.evidenceId
      ?? null;
    if (plotId) ids.push(plotId);
  }
  return ids;
}

/**
 * Coordinates post-commit parallel lanes and join barriers (#173).
 */
export class PostCommitSpanCoordinator {
  /**
   * @param {import('./execution-span-tracker.mjs').ExecutionSpanTracker|null} spanTracker
   * @param {object} scope
   */
  constructor(spanTracker, scope = {}) {
    this.tracker = spanTracker;
    this.graphId = crypto.randomUUID();
    this.roundGraphId = scope.roundGraphId ?? null;
    this.domainCommitId = scope.domainCommitId ?? null;
    this.characterTurnIndex = scope.characterTurnIndex ?? null;
    this.parentSpanId = scope.parentSpanId ?? null;
    this.predecessorSpanIds = [...(scope.predecessorSpanIds ?? [])];
    this.parallelGroupSpanId = null;
    this.laneSpanIds = {};
    this.lastJoinSpanId = null;
  }

  beginParallelSection() {
    if (!this.tracker) return;
    this.parallelGroupSpanId = this.tracker.beginSpan('post_commit_parallel_group', {
      parentSpanId: this.parentSpanId,
      orchestrationGraph: buildOrchestrationGraph({
        nodeKind: 'parallel_group',
        graphId: this.graphId,
        domainCommitId: this.domainCommitId,
        characterTurnIndex: this.characterTurnIndex,
        predecessorSpanIds: this.predecessorSpanIds,
      }),
    });
  }

  trackLane(lane, promise) {
    if (!this.tracker) return promise;
    const laneSpanId = this.tracker.beginSpan(`post_commit_lane_${lane}`, {
      parentSpanId: this.parallelGroupSpanId,
      orchestrationGraph: buildOrchestrationGraph({
        nodeKind: 'lane',
        graphId: this.graphId,
        lane,
        domainCommitId: this.domainCommitId,
        characterTurnIndex: this.characterTurnIndex,
        predecessorSpanIds: this.parallelGroupSpanId ? [this.parallelGroupSpanId] : [],
      }),
    });
    this.laneSpanIds[lane] = laneSpanId;
    return promise
      .then((result) => {
        const evidenceIds = collectEvidenceIds(lane, result);
        for (const evidenceId of evidenceIds) {
          this.tracker.linkInferenceEvidence(`post_commit_lane_${lane}_inference`, evidenceId, {
            parentSpanId: laneSpanId,
          });
        }
        this.tracker.endSpan(laneSpanId, { evidenceIds });
        return result;
      })
      .catch((err) => {
        this.tracker.endSpan(laneSpanId);
        throw err;
      });
  }

  async joinBarrier(barrierIndex, awaitedLane, promise) {
    if (!this.tracker) return promise;
    const memberSpanIds = Object.values(this.laneSpanIds).filter(Boolean);
    const joinSpanId = this.tracker.beginSpan(`post_commit_join_${awaitedLane}`, {
      orchestrationGraph: buildOrchestrationGraph({
        nodeKind: 'join_barrier',
        graphId: this.graphId,
        lane: awaitedLane,
        barrierIndex,
        domainCommitId: this.domainCommitId,
        characterTurnIndex: this.characterTurnIndex,
        joinMemberSpanIds: memberSpanIds,
        predecessorSpanIds: barrierIndex === 1 && this.parallelGroupSpanId
          ? [this.parallelGroupSpanId]
          : (this.lastJoinSpanId ? [this.lastJoinSpanId] : []),
      }),
    });
    try {
      const result = await promise;
      if (joinSpanId) {
        this.tracker.endSpan(joinSpanId);
        this.lastJoinSpanId = joinSpanId;
      }
      return result;
    } catch (err) {
      if (joinSpanId) this.tracker.endSpan(joinSpanId);
      throw err;
    }
  }

  endParallelSection() {
    if (this.tracker && this.parallelGroupSpanId) {
      this.tracker.endSpan(this.parallelGroupSpanId);
      this.parallelGroupSpanId = null;
    }
  }

  /**
   * @param {object} params
   */
  async run({
    librarianJoinPromise,
    plotCognitionJoinPromise,
    narratorPromise,
  }) {
    this.beginParallelSection();
    const librarianTracked = this.trackLane('librarian', librarianJoinPromise);
    const plotTracked = this.trackLane('plot_cognition', plotCognitionJoinPromise);
    const narratorTracked = this.trackLane('narrator', narratorPromise);

    const narratorResult = await this.joinBarrier(1, 'narrator', narratorTracked);
    const librarianResult = await this.joinBarrier(2, 'librarian', librarianTracked);
    const plotCognitionResult = await this.joinBarrier(3, 'plot_cognition', plotTracked);
    this.endParallelSection();
    return {
      narratorResult,
      librarianResult,
      plotCognitionResult,
      terminalSpanId: this.lastJoinSpanId,
    };
  }
}
