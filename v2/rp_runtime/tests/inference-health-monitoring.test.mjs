import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

import { buildAssembledRequest } from '../src/lib/execution-evidence/assembled-request.mjs';
import {
  buildInferenceHealth,
  buildInferenceHealthIndex,
  computeUtilization,
  deriveInferenceHealthFromAttempt,
  extractStructuralSignals,
  resolveCeilingConstrainedTokens,
} from '../src/lib/execution-evidence/inference-health.mjs';
import { ExecutionEvidenceStore } from '../src/lib/execution-evidence/store.mjs';

const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');
const LIST_CLI = path.join(REPO_ROOT, 'tools', 'investigation', 'list_execution_evidence.py');

function tempStore(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-inf-health-'));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  return new ExecutionEvidenceStore(root);
}

function baseAttempt(overrides = {}) {
  const evidenceId = overrides.evidence_id ?? 'ev-1';
  return {
    evidence_id: evidenceId,
    correlation: {
      evidence_id: evidenceId,
      hg_session_id: 'sess-health',
      hg_scene_id: 'sess-health',
      hg_round_id: 'round-1',
      role: 'librarian',
      inference_id: 'inf-1',
      attempt_index: 0,
      inference_kind: 'librarian_proposal',
      ...(overrides.correlation ?? {}),
    },
    request: {
      schema: 'hg_assembled_request_v1',
      system_persona: 'test',
      contributions: [],
      user_instruction: { text: 'x' },
      inference_profile: {
        provider: 'mock',
        model: 'm',
        max_tokens: 4096,
        reasoning_effort: 'low',
        ...(overrides.request_profile ?? {}),
      },
      ...(overrides.request ?? {}),
    },
    response: {
      schema: 'hg_model_response_v1',
      assistant_text: overrides.assistant_text ?? '{"ok":true}',
      failed: overrides.failed ?? false,
      failure: overrides.failure ?? null,
      finish: overrides.finish ?? { kind: 'stop' },
      usage: overrides.usage ?? {
        inputTokens: 100,
        outputTokens: 50,
        reasoningTokens: 10,
        totalTokens: 160,
      },
      ...(overrides.response ?? {}),
    },
    decision: overrides.decision ?? null,
    associations: overrides.associations ?? {},
  };
}

test('assembled request persists configured max_tokens ceiling', () => {
  const request = buildAssembledRequest({
    manifest: { contributions: [] },
    userInstruction: 'go',
    systemPersona: 'persona',
    profile: { provider: 'deepseek-official', model: 'x', maxTokens: 8192, reasoningEffort: 'low' },
    manifestId: 'm1',
    contributionIds: [],
  });
  assert.equal(request.inference_profile.max_tokens, 8192);
});

test('utilization uses generation tokens only; prompt does not inflate (G-118-01)', () => {
  assert.equal(computeUtilization({ totalTokens: 1000 }, null), null);
  assert.equal(computeUtilization({ totalTokens: 2048 }, 4096), null);
  assert.equal(computeUtilization({ outputTokens: 2048 }, 4096), 0.5);
  assert.equal(resolveCeilingConstrainedTokens({
    inputTokens: 8000,
    outputTokens: 100,
    reasoningTokens: 50,
    totalTokens: 8150,
  }), 150);
  assert.equal(computeUtilization({
    inputTokens: 8000,
    outputTokens: 100,
    reasoningTokens: 50,
    totalTokens: 8150,
  }, 4096), 150 / 4096);
  assert.equal(computeUtilization({ outputTokens: 0, reasoningTokens: 4096 }, 4096), 1);
  assert.equal(computeUtilization({ outputTokens: 10 }, 0), null);
  assert.equal(computeUtilization({ outputTokens: 10 }, -1), null);

  const noCeiling = buildInferenceHealth({
    profile: {},
    trace: {
      finish: { kind: 'stop' },
      usage: { totalTokens: 3000, outputTokens: 100, inputTokens: 2900 },
      failed: false,
    },
    assistantText: 'ok',
  });
  assert.equal(noCeiling.configured_max_tokens, null);
  assert.equal(noCeiling.utilization, null);
  assert.equal(noCeiling.usage?.input_tokens, 2900);
  assert.equal(noCeiling.hard_exhaustion, false);

  const largePrompt = buildInferenceHealth({
    profile: { maxTokens: 4096 },
    trace: {
      finish: { kind: 'stop' },
      usage: {
        inputTokens: 12000,
        outputTokens: 200,
        reasoningTokens: 100,
        totalTokens: 12300,
      },
      failed: false,
    },
    assistantText: '{"ok":true}',
  });
  assert.equal(largePrompt.utilization, 300 / 4096);
  assert.ok(largePrompt.utilization < 0.1);
  assert.equal(largePrompt.usage.input_tokens, 12000);
});

test('Level-1 scenarios: healthy, high util, max-token, recovery, provider fail', () => {
  const healthy = buildInferenceHealth({
    profile: { maxTokens: 8192 },
    trace: {
      finish: { kind: 'stop' },
      usage: { totalTokens: 800, outputTokens: 100, reasoningTokens: 50, inputTokens: 650 },
      failed: false,
    },
    assistantText: '{"schema":"ok"}',
  });
  assert.equal(healthy.finish_class, 'complete');
  assert.equal(healthy.hard_exhaustion, false);
  assert.equal(healthy.provider_failed, false);
  assert.equal(healthy.recovery.state, 'none');
  assert.equal(healthy.utilization, 150 / 8192);

  const highUtil = buildInferenceHealth({
    profile: { maxTokens: 4096 },
    trace: {
      finish: { kind: 'stop' },
      usage: { totalTokens: 5000, inputTokens: 900, outputTokens: 3800, reasoningTokens: 200 },
      failed: false,
    },
    assistantText: '{"schema":"ok"}',
  });
  assert.equal(highUtil.finish_class, 'complete');
  assert.equal(highUtil.utilization, 4000 / 4096);
  assert.ok(highUtil.utilization > 0.9);
  assert.equal(highUtil.hard_exhaustion, false);
  assert.equal(Object.hasOwn(highUtil, 'near_ceiling'), false);

  const exhausted = buildInferenceHealth({
    profile: { maxTokens: 4096 },
    trace: {
      finish: { kind: 'max_tokens' },
      usage: { totalTokens: 5000, inputTokens: 904, outputTokens: 0, reasoningTokens: 4096 },
      failed: false,
    },
    assistantText: '',
  });
  assert.equal(exhausted.finish_class, 'output_limit');
  assert.equal(exhausted.hard_exhaustion, true);
  assert.equal(exhausted.reasoning_budget_exhausted, true);
  assert.equal(exhausted.utilization, 1);

  const providerFail = buildInferenceHealth({
    profile: { maxTokens: 4096 },
    trace: {
      finish: { kind: 'error' },
      usage: null,
      failed: true,
      failure: { message: 'boom' },
    },
    assistantText: '',
  });
  assert.equal(providerFail.provider_failed, true);
  assert.equal(providerFail.finish_class, 'provider_error');
  assert.equal(providerFail.recovery.state, 'none');
  assert.equal(providerFail.utilization, null);
});

test('successful correction does not inherit primary structural failure (G-118-02)', () => {
  const lineage = {
    correction_used: true,
    primary_evidence_id: 'ev-p',
    primary_parse_error: 'json_parse_failed',
    correction_evidence_id: 'ev-c',
    correction_parse_error: null,
  };

  const primarySignals = extractStructuralSignals({
    librarian_proposal: {
      structural_parse_error: 'json_parse_failed',
      proposal_generation_stage: 'primary',
      contract_lineage: lineage,
    },
  }, { correlation: { inference_kind: 'librarian_proposal' } });
  assert.equal(primarySignals.structural_valid, false);
  assert.equal(primarySignals.structural_error, 'json_parse_failed');

  const correctionSignals = extractStructuralSignals({
    librarian_proposal: {
      structural_parse_error: null,
      proposal_generation_stage: 'contract_correction',
      contract_lineage: lineage,
    },
  }, { correlation: { inference_kind: 'librarian_proposal_contract_correction' } });
  assert.equal(correctionSignals.structural_valid, true);
  assert.equal(correctionSignals.structural_error, null);

  const primaryHealth = buildInferenceHealth({
    profile: { maxTokens: 4096 },
    correlation: { inference_kind: 'librarian_proposal', evidence_id: 'ev-p' },
    decision: {
      librarian_proposal: {
        structural_parse_error: 'json_parse_failed',
        proposal_generation_stage: 'primary',
        contract_lineage: lineage,
      },
    },
    trace: {
      finish: { kind: 'stop' },
      usage: { outputTokens: 40, reasoningTokens: 10, inputTokens: 500 },
      failed: false,
    },
    assistantText: '{bad',
  });
  assert.equal(primaryHealth.structural_valid, false);
  assert.equal(primaryHealth.recovery.state, 'recovered');

  const correctionHealth = buildInferenceHealth({
    profile: { maxTokens: 8192 },
    correlation: {
      inference_kind: 'librarian_proposal_contract_correction',
      evidence_id: 'ev-c',
      parent_inference_id: 'inf-p',
    },
    decision: {
      librarian_proposal: {
        structural_parse_error: null,
        proposal_generation_stage: 'contract_correction',
        contract_lineage: lineage,
      },
    },
    trace: {
      finish: { kind: 'stop' },
      usage: { outputTokens: 80, reasoningTokens: 20, inputTokens: 600 },
      failed: false,
    },
    assistantText: '{"ok":true}',
  });
  assert.equal(correctionHealth.structural_valid, true);
  assert.equal(correctionHealth.recovery.state, 'recovered');

  const failedCorrection = extractStructuralSignals({
    librarian_proposal: {
      proposal_generation_stage: 'contract_correction',
      contract_lineage: {
        ...lineage,
        correction_parse_error: 'still_invalid',
      },
    },
  }, { correlation: { inference_kind: 'librarian_proposal_contract_correction' } });
  assert.equal(failedCorrection.structural_valid, false);
  assert.equal(failedCorrection.structural_error, 'still_invalid');
});

test('store: primary failure remains visible after successful correction recovery', (t) => {
  const store = tempStore(t);
  const primaryId = 'ev-primary';
  const correctionId = 'ev-correction';

  store.writeAttempt(baseAttempt({
    evidence_id: primaryId,
    assistant_text: '',
    finish: { kind: 'max_tokens' },
    usage: { totalTokens: 4096, outputTokens: 0, reasoningTokens: 4000 },
    correlation: {
      evidence_id: primaryId,
      inference_kind: 'librarian_proposal',
      inference_id: 'inf-primary',
    },
  }));

  store.writeAttempt(baseAttempt({
    evidence_id: correctionId,
    assistant_text: '{"schema":"hg_librarian_proposal_result_v1","proposals":[]}',
    finish: { kind: 'stop' },
    usage: { totalTokens: 1200, outputTokens: 400 },
    correlation: {
      evidence_id: correctionId,
      inference_kind: 'librarian_proposal_contract_correction',
      inference_id: 'inf-primary-contract-correction',
      parent_inference_id: 'inf-primary',
    },
    request_profile: { max_tokens: 8192 },
  }));

  const lineage = {
    correction_used: true,
    primary_inference_id: 'inf-primary',
    primary_evidence_id: primaryId,
    primary_parse_error: 'truncated_parse_failed',
    correction_inference_id: 'inf-primary-contract-correction',
    correction_evidence_id: correctionId,
    correction_parse_error: null,
  };

  store.patchAttempt('sess-health', primaryId, {
    decision: {
      librarian_proposal: {
        structural_parse_error: 'truncated_parse_failed',
        proposal_generation_stage: 'primary',
        contract_correction_used: true,
        contract_lineage: lineage,
      },
    },
  });
  store.patchAttempt('sess-health', correctionId, {
    decision: {
      librarian_proposal: {
        structural_parse_error: null,
        proposal_generation_stage: 'contract_correction',
        contract_correction_used: true,
        contract_lineage: lineage,
      },
    },
  });

  const primary = store.readAttempt('sess-health', primaryId);
  const correction = store.readAttempt('sess-health', correctionId);
  assert.equal(primary.inference_health.hard_exhaustion, true);
  assert.equal(primary.inference_health.structural_valid, false);
  assert.equal(primary.inference_health.recovery.state, 'recovered');
  assert.equal(primary.inference_health.configured_max_tokens, 4096);
  assert.equal(correction.inference_health.recovery.state, 'recovered');
  assert.equal(correction.inference_health.hard_exhaustion, false);
  assert.equal(correction.inference_health.structural_valid, true);
  assert.equal(correction.inference_health.structural_error, null);

  const index = store.readIndex('sess-health');
  const group = index.inference_health.by_group['inference_kind:librarian_proposal'];
  const corrGroup = index.inference_health.by_group['inference_kind:librarian_proposal_contract_correction'];
  assert.equal(group.hard_exhaustion_count, 1);
  assert.equal(group.recovered_primary_failure_count, 1);
  assert.equal(group.structural_failure_count, 1);
  assert.equal(corrGroup.correction_attempt_count, 1);
  assert.equal(corrGroup.structural_failure_count, 0);
  assert.equal(index.inference_health.totals.hard_exhaustion_count, 1);
  assert.equal(index.inference_health.totals.correction_attempt_count, 1);
  assert.equal(index.inference_health.totals.recovered_primary_failure_count, 1);
  assert.equal(index.inference_health.totals.structural_failure_count, 1);
});

test('structural primary failure then successful correction', (t) => {
  const store = tempStore(t);
  store.writeAttempt(baseAttempt({
    evidence_id: 'ev-s-primary',
    assistant_text: '{bad',
    finish: { kind: 'stop' },
    usage: { totalTokens: 500, outputTokens: 40 },
    correlation: {
      evidence_id: 'ev-s-primary',
      inference_kind: 'plot_cognition_update',
      inference_id: 'inf-plot',
      role: null,
    },
  }));
  store.writeAttempt(baseAttempt({
    evidence_id: 'ev-s-corr',
    assistant_text: '{"ok":true}',
    finish: { kind: 'stop' },
    usage: { totalTokens: 600, outputTokens: 80 },
    correlation: {
      evidence_id: 'ev-s-corr',
      inference_kind: 'plot_cognition_update_contract_correction',
      inference_id: 'inf-plot-contract-correction',
      parent_inference_id: 'inf-plot',
      role: null,
    },
  }));
  const lineage = {
    correction_used: true,
    primary_evidence_id: 'ev-s-primary',
    primary_parse_error: 'invalid_json',
    correction_evidence_id: 'ev-s-corr',
    correction_parse_error: null,
  };
  store.patchAttempt('sess-health', 'ev-s-primary', {
    decision: {
      plot_cognition: {
        structural_parse_error: 'invalid_json',
        contract_lineage: lineage,
      },
    },
  });
  store.patchAttempt('sess-health', 'ev-s-corr', {
    decision: {
      plot_cognition: {
        contract_lineage: lineage,
      },
    },
  });
  const primary = store.readAttempt('sess-health', 'ev-s-primary');
  assert.equal(primary.inference_health.structural_valid, false);
  assert.equal(primary.inference_health.recovery.state, 'recovered');
  assert.equal(primary.inference_health.hard_exhaustion, false);
  const correction = store.readAttempt('sess-health', 'ev-s-corr');
  assert.equal(correction.inference_health.structural_valid, true);
  assert.equal(correction.inference_health.recovery.state, 'recovered');
  const index = store.readIndex('sess-health');
  assert.equal(index.inference_health.totals.structural_failure_count, 1);
  assert.equal(index.inference_health.totals.recovered_primary_failure_count, 1);
});

test('historical attempts without health fields rebuild honestly', (t) => {
  const store = tempStore(t);
  const root = store.root;
  const sessionDir = path.join(root, 'sess-hist');
  fs.mkdirSync(path.join(sessionDir, 'attempts'), { recursive: true });
  const historical = {
    schema: 'hg_execution_evidence_attempt_v1',
    evidence_id: 'ev-hist',
    correlation: {
      evidence_id: 'ev-hist',
      hg_session_id: 'sess-hist',
      role: 'narrator',
      inference_id: 'inf-n',
    },
    request: {
      schema: 'hg_assembled_request_v1',
      inference_profile: {
        provider: 'x',
        model: 'y',
        // no max_tokens — pre-#114
      },
      contributions: [],
      user_instruction: { text: 'n' },
    },
    response: {
      schema: 'hg_model_response_v1',
      assistant_text: 'She nodded.',
      failed: false,
      finish: { kind: 'stop' },
      usage: { totalTokens: 200, outputTokens: 40 },
    },
    decision: null,
  };
  fs.writeFileSync(
    path.join(sessionDir, 'attempts', 'ev-hist.json'),
    `${JSON.stringify(historical, null, 2)}\n`,
    'utf8',
  );
  fs.writeFileSync(
    path.join(sessionDir, 'index.json'),
    `${JSON.stringify({
      schema: 'hg_execution_evidence_index_v1',
      hg_session_id: 'sess-hist',
      attempt_ids: ['ev-hist'],
      rounds: {},
      participation_by_round: {},
      semantic: {},
      ni: {},
      plot_cognition: {},
    }, null, 2)}\n`,
    'utf8',
  );

  const rebuilt = store.rebuildSemanticNavigationIndexes('sess-hist');
  assert.ok(rebuilt.inference_health);
  assert.equal(rebuilt.inference_health.observability.attempts_without_ceiling, 1);
  assert.equal(rebuilt.inference_health.observability.attempts_with_ceiling, 0);
  assert.equal(rebuilt.inference_health.totals.utilization.sample_count, 0);
  assert.equal(
    rebuilt.inference_health.totals.utilization.note,
    'not_observable_without_configured_ceiling',
  );
  const group = rebuilt.inference_health.by_group['role:narrator'];
  assert.equal(group.attempt_count, 1);
  // Attempt file must remain without fabricated health write during rebuild.
  const onDisk = JSON.parse(
    fs.readFileSync(path.join(sessionDir, 'attempts', 'ev-hist.json'), 'utf8'),
  );
  assert.equal(onDisk.inference_health, undefined);
  const derived = deriveInferenceHealthFromAttempt(onDisk);
  assert.equal(derived.configured_max_tokens, null);
  assert.equal(derived.utilization, null);
});

test('#111-analog corpus: systematic correction dependence discoverable in Level-2', () => {
  const attempts = [];
  for (let i = 0; i < 5; i += 1) {
    const primaryId = `ev-p-${i}`;
    const corrId = `ev-c-${i}`;
    attempts.push(baseAttempt({
      evidence_id: primaryId,
      assistant_text: '',
      finish: { kind: 'max_tokens' },
      usage: { totalTokens: 4096, outputTokens: 0, reasoningTokens: 4096 },
      correlation: {
        evidence_id: primaryId,
        hg_session_id: 'sess-111',
        inference_kind: 'plot_cognition_update',
        inference_id: `inf-${i}`,
        role: null,
      },
      decision: {
        plot_cognition: {
          structural_parse_error: 'truncated',
          contract_lineage: {
            correction_used: true,
            primary_evidence_id: primaryId,
            primary_parse_error: 'truncated',
            correction_evidence_id: corrId,
            correction_parse_error: null,
          },
        },
      },
    }));
    attempts.push(baseAttempt({
      evidence_id: corrId,
      assistant_text: '{"ok":true}',
      finish: { kind: 'stop' },
      usage: { totalTokens: 1500, outputTokens: 200 },
      correlation: {
        evidence_id: corrId,
        hg_session_id: 'sess-111',
        inference_kind: 'plot_cognition_update_contract_correction',
        inference_id: `inf-${i}-contract-correction`,
        parent_inference_id: `inf-${i}`,
        role: null,
      },
      request_profile: { max_tokens: 8192 },
      decision: {
        plot_cognition: {
          contract_lineage: {
            correction_used: true,
            primary_evidence_id: primaryId,
            correction_evidence_id: corrId,
            correction_parse_error: null,
          },
        },
      },
    }));
  }
  // One healthy first-pass control in another kind
  attempts.push(baseAttempt({
    evidence_id: 'ev-ok',
    correlation: {
      evidence_id: 'ev-ok',
      hg_session_id: 'sess-111',
      inference_kind: 'director_decision',
      role: 'director',
      inference_id: 'inf-dir',
    },
    finish: { kind: 'stop' },
    usage: { totalTokens: 400, outputTokens: 80 },
  }));

  const healthIndex = buildInferenceHealthIndex(attempts);
  const plot = healthIndex.by_group['inference_kind:plot_cognition_update'];
  const plotCorr = healthIndex.by_group['inference_kind:plot_cognition_update_contract_correction'];
  assert.equal(plot.attempt_count, 5);
  assert.equal(plot.hard_exhaustion_count, 5);
  assert.equal(plot.hard_exhaustion_rate, 1);
  assert.equal(plot.recovered_primary_failure_count, 5);
  assert.equal(plot.recovered_primary_failure_rate, 1);
  assert.equal(plot.structural_failure_count, 5);
  assert.equal(plotCorr.correction_attempt_count, 5);
  assert.equal(plotCorr.correction_attempt_rate, 1);
  assert.equal(plotCorr.structural_failure_count, 0);
  assert.equal(healthIndex.totals.correction_attempt_count, 5);
  assert.equal(healthIndex.totals.structural_failure_count, 5);
  assert.ok(healthIndex.totals.correction_attempt_rate > 0);
  assert.ok(
    plot.recovered_primary_failure_rate === 1
      && plot.hard_exhaustion_rate === 1,
    'systematic primary exhaustion + recovery dependence must be visible on the kind group',
  );
});

test('list_execution_evidence.py --inference-health exposes Level-2 aggregates', (t) => {
  const store = tempStore(t);
  store.writeAttempt(baseAttempt({
    evidence_id: 'ev-cli-1',
    finish: { kind: 'max_tokens' },
    assistant_text: '',
    usage: { totalTokens: 4096, outputTokens: 0, reasoningTokens: 4096 },
  }));
  const evidenceRoot = store.root;
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-cli-data-'));
  t.after(() => fs.rmSync(dataDir, { recursive: true, force: true }));
  const cliEvidenceRoot = path.join(dataDir, 'execution_evidence');
  fs.cpSync(evidenceRoot, cliEvidenceRoot, { recursive: true });
  const result = spawnSync(
    process.env.HG_PYTHON_EXECUTABLE || 'python',
    [LIST_CLI, 'sess-health', '--inference-health'],
    {
      encoding: 'utf8',
      env: {
        ...process.env,
        HG_DATA_DIR: dataDir,
      },
      cwd: REPO_ROOT,
    },
  );
  assert.equal(result.status, 0, result.stderr || result.stdout);
  assert.match(result.stdout, /totals\.hard_exhaustion_count: 1/);
  assert.match(result.stdout, /by_group:/);
  assert.match(result.stdout, /inference_kind:librarian_proposal/);
});
