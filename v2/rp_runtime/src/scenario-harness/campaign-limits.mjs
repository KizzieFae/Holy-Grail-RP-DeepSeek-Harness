export class CampaignLimits {
  constructor({ maxRuns = 7, maxInferences = 25 } = {}) {
    this.maxRuns = maxRuns;
    this.maxInferences = maxInferences;
    this.runCount = 0;
    this.inferenceCount = 0;
    this.stopped = false;
    this.stopReason = null;
  }

  assertCanRun() {
    if (this.stopped) throw new Error(`campaign_stopped:${this.stopReason}`);
    if (this.runCount >= this.maxRuns) {
      throw new Error('campaign_run_limit_exceeded');
    }
  }

  assertCanInfer() {
    if (this.stopped) throw new Error(`campaign_stopped:${this.stopReason}`);
    if (this.inferenceCount >= this.maxInferences) {
      throw new Error('campaign_inference_limit_exceeded');
    }
  }

  recordRun() {
    this.runCount += 1;
  }

  recordInference() {
    this.inferenceCount += 1;
  }

  stop(reason) {
    this.stopped = true;
    this.stopReason = reason;
  }

  snapshot() {
    return {
      max_runs: this.maxRuns,
      max_inferences: this.maxInferences,
      run_count: this.runCount,
      inference_count: this.inferenceCount,
      stopped: this.stopped,
      stop_reason: this.stopReason,
    };
  }
}
