import crypto from 'node:crypto';

import { buildOrchestrationGraph } from './orchestration-graph.mjs';
import { PostCommitSpanCoordinator } from './post-commit-span-coordinator.mjs';
import {
  collectCharacterPrepEvidenceIds,
  collectDirectorEvidenceIds,
} from './orchestration-evidence-collectors.mjs';

function linkEvidenceIds(tracker, phaseId, evidenceIds, parentSpanId) {
  if (!tracker) return;
  for (const evidenceId of evidenceIds) {
    tracker.linkInferenceEvidence(phaseId, evidenceId, { parentSpanId });
  }
}

/**
 * Serial pre-commit + post-commit causal graph for one Character turn (#173).
 */
export class CharacterTurnSpanCoordinator {
  /**
   * @param {import('./execution-span-tracker.mjs').ExecutionSpanTracker|null} tracker
   * @param {object} scope
   */
  constructor(tracker, scope = {}) {
    this.tracker = tracker;
    this.roundGraphId = scope.roundGraphId ?? null;
    this.characterTurnIndex = scope.characterTurnIndex ?? null;
    this.turnEntryPredecessorSpanIds = [...(scope.turnEntryPredecessorSpanIds ?? [])];
    this.characterTurnSerialSpanId = null;
    this.directorPhaseSpanId = null;
    this.characterPrepSpanId = null;
    this.commitBoundarySpanId = null;
    this.lastSerialSpanId = null;
    this.postCommitTerminalSpanId = null;
    this.graphId = crypto.randomUUID();
  }

  beginTurn() {
    if (!this.tracker) return;
    this.characterTurnSerialSpanId = this.tracker.beginSpan('character_turn_serial', {
      orchestrationGraph: buildOrchestrationGraph({
        nodeKind: 'serial_phase',
        graphId: this.graphId,
        characterTurnIndex: this.characterTurnIndex,
        predecessorSpanIds: this.turnEntryPredecessorSpanIds,
      }),
    });
    this.lastSerialSpanId = this.characterTurnSerialSpanId;
  }

  /**
   * @template T
   * @param {() => Promise<T>|T} fn
   * @returns {Promise<T>}
   */
  async measureDirectorPhase(fn) {
    if (!this.tracker) return fn();
    const predecessorSpanIds = this.lastSerialSpanId
      ? [this.lastSerialSpanId]
      : [...this.turnEntryPredecessorSpanIds];
    this.directorPhaseSpanId = this.tracker.beginSpan('director_phase', {
      parentSpanId: this.characterTurnSerialSpanId,
      orchestrationGraph: buildOrchestrationGraph({
        nodeKind: 'serial_phase',
        graphId: this.graphId,
        characterTurnIndex: this.characterTurnIndex,
        predecessorSpanIds,
      }),
    });
    const result = await fn();
    linkEvidenceIds(
      this.tracker,
      'director_phase_inference',
      collectDirectorEvidenceIds(result),
      this.directorPhaseSpanId,
    );
    this.tracker.endSpan(this.directorPhaseSpanId);
    this.lastSerialSpanId = this.directorPhaseSpanId;
    return result;
  }

  /**
   * @template T
   * @param {() => Promise<T>|T} fn
   * @returns {Promise<T>}
   */
  async measureCharacterPrepPhase(fn) {
    if (!this.tracker) return fn();
    const predecessorSpanIds = this.lastSerialSpanId ? [this.lastSerialSpanId] : [];
    this.characterPrepSpanId = this.tracker.beginSpan('character_prep_phase', {
      parentSpanId: this.characterTurnSerialSpanId,
      orchestrationGraph: buildOrchestrationGraph({
        nodeKind: 'serial_phase',
        graphId: this.graphId,
        characterTurnIndex: this.characterTurnIndex,
        predecessorSpanIds,
      }),
    });
    const result = await fn();
    linkEvidenceIds(
      this.tracker,
      'character_prep_inference',
      collectCharacterPrepEvidenceIds(result),
      this.characterPrepSpanId,
    );
    this.tracker.endSpan(this.characterPrepSpanId);
    this.lastSerialSpanId = this.characterPrepSpanId;
    return result;
  }

  measureCommitBoundary(domainCommitId) {
    if (!this.tracker) return null;
    const predecessorSpanIds = this.lastSerialSpanId ? [this.lastSerialSpanId] : [];
    this.commitBoundarySpanId = this.tracker.beginSpan('domain_commit_boundary', {
      parentSpanId: this.characterTurnSerialSpanId,
      orchestrationGraph: buildOrchestrationGraph({
        nodeKind: 'serial_phase',
        graphId: this.graphId,
        domainCommitId,
        characterTurnIndex: this.characterTurnIndex,
        predecessorSpanIds,
      }),
    });
    this.tracker.endSpan(this.commitBoundarySpanId);
    this.lastSerialSpanId = this.commitBoundarySpanId;
    return this.commitBoundarySpanId;
  }

  /**
   * @param {object} scope
   * @returns {PostCommitSpanCoordinator}
   */
  createPostCommitCoordinator(scope) {
    const coordinator = new PostCommitSpanCoordinator(this.tracker, {
      ...scope,
      roundGraphId: this.roundGraphId,
      parentSpanId: this.characterTurnSerialSpanId,
      predecessorSpanIds: this.lastSerialSpanId ? [this.lastSerialSpanId] : [],
    });
    return coordinator;
  }

  /**
   * @param {string|null} postCommitTerminalSpanId
   */
  endTurn(postCommitTerminalSpanId = null) {
    this.postCommitTerminalSpanId = postCommitTerminalSpanId ?? this.lastSerialSpanId;
    if (this.tracker && this.characterTurnSerialSpanId) {
      this.tracker.endSpan(this.characterTurnSerialSpanId);
      this.characterTurnSerialSpanId = null;
    }
    return this.postCommitTerminalSpanId;
  }
}
