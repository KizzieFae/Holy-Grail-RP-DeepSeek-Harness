import crypto from 'node:crypto';

import { buildOrchestrationGraph } from './orchestration-graph.mjs';
import { CharacterTurnSpanCoordinator } from './character-turn-span-coordinator.mjs';
import {
  collectPlotCognitionResumeEvidenceIds,
  collectStorytellerEvidenceIds,
} from './orchestration-evidence-collectors.mjs';

function linkEvidenceIds(tracker, phaseId, evidenceIds, parentSpanId) {
  if (!tracker) return;
  for (const evidenceId of evidenceIds) {
    tracker.linkInferenceEvidence(phaseId, evidenceId, { parentSpanId });
  }
}

/**
 * Round-level serial orchestration graph: preamble, turn chaining (#173).
 */
export class RoundOrchestrationSpanCoordinator {
  /**
   * @param {import('./execution-span-tracker.mjs').ExecutionSpanTracker|null} tracker
   * @param {object} scope
   */
  constructor(tracker, scope = {}) {
    this.tracker = tracker;
    this.hgRoundId = scope.hgRoundId ?? null;
    this.roundGraphId = crypto.randomUUID();
    this.roundInternalSpanId = null;
    this.preambleSpanId = null;
    this.storytellerSpanId = null;
    this.plotResumeSpanId = null;
    this.lastChainedSpanId = null;
    this.preambleExecuted = false;
  }

  beginRound() {
    if (!this.tracker) return;
    this.roundInternalSpanId = this.tracker.beginSpan('round_internal_serial', {
      orchestrationGraph: buildOrchestrationGraph({
        nodeKind: 'serial_phase',
        graphId: this.roundGraphId,
      }),
    });
    this.lastChainedSpanId = this.roundInternalSpanId;
  }

  beginPreamble() {
    if (!this.tracker) return;
    this.preambleSpanId = this.tracker.beginSpan('round_preamble_serial', {
      parentSpanId: this.roundInternalSpanId,
      orchestrationGraph: buildOrchestrationGraph({
        nodeKind: 'serial_phase',
        graphId: this.roundGraphId,
        predecessorSpanIds: this.roundInternalSpanId ? [this.roundInternalSpanId] : [],
      }),
    });
    this.preambleExecuted = true;
    this.lastChainedSpanId = this.preambleSpanId;
  }

  endPreamble() {
    if (this.tracker && this.preambleSpanId) {
      this.tracker.endSpan(this.preambleSpanId);
      this.lastChainedSpanId = this.preambleSpanId;
      this.preambleSpanId = null;
    }
  }

  /**
   * @template T
   * @param {() => Promise<T>|T} fn
   * @returns {Promise<T>}
   */
  async measureStoryteller(fn) {
    if (!this.tracker) return fn();
    if (!this.preambleSpanId) this.beginPreamble();
    const predecessorSpanIds = this.storytellerSpanId
      ? [this.storytellerSpanId]
      : (this.preambleSpanId ? [this.preambleSpanId] : []);
    this.storytellerSpanId = this.tracker.beginSpan('storyteller_round_cognition', {
      parentSpanId: this.preambleSpanId ?? this.roundInternalSpanId,
      orchestrationGraph: buildOrchestrationGraph({
        nodeKind: 'serial_phase',
        graphId: this.roundGraphId,
        predecessorSpanIds,
      }),
    });
    const result = await fn();
    linkEvidenceIds(
      this.tracker,
      'storyteller_round_inference',
      collectStorytellerEvidenceIds(result),
      this.storytellerSpanId,
    );
    this.tracker.endSpan(this.storytellerSpanId);
    this.lastChainedSpanId = this.storytellerSpanId;
    return result;
  }

  /**
   * @template T
   * @param {() => Promise<T>|T} fn
   * @returns {Promise<T>}
   */
  async measurePlotResume(fn) {
    if (!this.tracker) return fn();
    if (!this.preambleSpanId) this.beginPreamble();
    const predecessorSpanIds = this.plotResumeSpanId
      ? [this.plotResumeSpanId]
      : (this.storytellerSpanId
        ? [this.storytellerSpanId]
        : (this.preambleSpanId ? [this.preambleSpanId] : []));
    this.plotResumeSpanId = this.tracker.beginSpan('plot_cognition_resume', {
      parentSpanId: this.preambleSpanId ?? this.roundInternalSpanId,
      orchestrationGraph: buildOrchestrationGraph({
        nodeKind: 'serial_phase',
        graphId: this.roundGraphId,
        predecessorSpanIds,
      }),
    });
    const result = await fn();
    linkEvidenceIds(
      this.tracker,
      'plot_cognition_resume_inference',
      collectPlotCognitionResumeEvidenceIds(result),
      this.plotResumeSpanId,
    );
    this.tracker.endSpan(this.plotResumeSpanId);
    this.lastChainedSpanId = this.plotResumeSpanId;
    return result;
  }

  /**
   * @param {number} characterTurnIndex
   * @returns {CharacterTurnSpanCoordinator}
   */
  beginCharacterTurn(characterTurnIndex) {
    if (this.preambleSpanId) this.endPreamble();
    const turnEntryPredecessorSpanIds = this.lastChainedSpanId ? [this.lastChainedSpanId] : [];
    const coordinator = new CharacterTurnSpanCoordinator(this.tracker, {
      roundGraphId: this.roundGraphId,
      characterTurnIndex,
      turnEntryPredecessorSpanIds,
    });
    coordinator.beginTurn();
    return coordinator;
  }

  /**
   * @param {string|null} turnTerminalSpanId
   */
  completeCharacterTurn(turnTerminalSpanId) {
    if (turnTerminalSpanId) {
      this.lastChainedSpanId = turnTerminalSpanId;
    }
  }

  endRound() {
    if (this.preambleSpanId) this.endPreamble();
    if (this.tracker && this.roundInternalSpanId) {
      this.tracker.endSpan(this.roundInternalSpanId);
      this.roundInternalSpanId = null;
    }
  }
}
