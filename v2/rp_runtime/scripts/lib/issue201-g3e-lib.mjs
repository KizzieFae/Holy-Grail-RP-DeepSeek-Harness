import { execFileSync } from 'node:child_process';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { deriveObligationSignals } from '../../src/lib/a2-obligation-dispatch.mjs';
import { A2_TOPOLOGY_ABSENT } from '../../src/lib/a2-beat-orchestration.mjs';
import { LEAN_A4_ROUND_OPTIONS, A2_PROHIBITED_KINDS } from './issue201-g3-b-lib.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
export const REPO_ROOT = path.resolve(__dirname, '../../../..');
export const G3E_FIXTURE_ROOT = path.join(
  REPO_ROOT,
  'governance/records/issue201-g3e-fixtures/ayame_archive_corpus_v1',
);
export const G3E_POLICIES_DIR = path.join(REPO_ROOT, 'governance/records/issue201-g3e-policies');
export const G3E_PROBE_SCRIPT = path.join(REPO_ROOT, 'tools/investigation/issue201_g3e_retrieval_probe.py');
export const G3E_CORPUS_BUILDER = path.join(REPO_ROOT, 'tools/investigation/issue201-g3e-corpus-build.mjs');

export const G3E_ARMS = {
  A2_INDEXED: 'a2_indexed_retrieval',
  LEAN_A4: 'lean_a4_knowledge',
};

export const K_CASE_IDS = ['K1', 'K2', 'K3', 'K4', 'K5', 'K6', 'K7'];

export function loadJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

export function loadPolicies() {
  return K_CASE_IDS.map((caseId) => loadJson(path.join(G3E_POLICIES_DIR, `${caseId}.json`)));
}

export function loadTruthManifest() {
  return loadJson(path.join(G3E_FIXTURE_ROOT, 'truth_manifest.json'));
}

export function loadCorpusManifest() {
  return loadJson(path.join(G3E_FIXTURE_ROOT, 'corpus_manifest.json'));
}

export function loadCorpusRecordIds() {
  const lines = fs.readFileSync(path.join(G3E_FIXTURE_ROOT, 'records.jsonl'), 'utf8')
    .split('\n')
    .filter(Boolean);
  return lines.map((line) => JSON.parse(line).story_record_id);
}

export function ensureCorpusBuilt() {
  const recordsPath = path.join(G3E_FIXTURE_ROOT, 'records.jsonl');
  if (!fs.existsSync(recordsPath)) {
    execFileSync(process.execPath, [G3E_CORPUS_BUILDER], { cwd: REPO_ROOT, stdio: 'pipe' });
  }
}

export function validateCorpusIntegrity() {
  ensureCorpusBuilt();
  const truth = loadTruthManifest();
  const manifest = loadCorpusManifest();
  const recordIds = new Set(loadCorpusRecordIds());
  const jsonl = fs.readFileSync(path.join(G3E_FIXTURE_ROOT, 'records.jsonl'), 'utf8');
  const sha = crypto.createHash('sha256').update(jsonl, 'utf8').digest('hex');
  const missingAnchors = (truth.required_anchor_ids ?? []).filter((id) => !recordIds.has(id));
  const rebuild = execFileSync(process.execPath, [G3E_CORPUS_BUILDER], { cwd: REPO_ROOT, encoding: 'utf8' });
  const rebuildPayload = JSON.parse(rebuild);
  const rebuildSha = rebuildPayload.records_sha256;
  return {
    record_count: manifest.record_count,
    records_sha256: sha,
    manifest_sha256: manifest.records_sha256,
    sha_matches_manifest: sha === manifest.records_sha256,
    reproducible_rebuild: rebuildSha === manifest.records_sha256,
    missing_anchor_ids: missingAnchors,
    truth_manifest_valid: missingAnchors.length === 0,
    entitlement_fixtures_present: recordIds.has('g3e-private-kizzie-debt')
      && recordIds.has('g3e-private-ayame-master-key'),
    supersession_valid: recordIds.has('g3e-curfew-2024-11pm')
      && recordIds.has('g3e-curfew-2019-9pm'),
    distractor_population_present: recordIds.has('g3e-distract-riverside-curfew'),
  };
}

export function runRetrievalProbe() {
  ensureCorpusBuilt();
  const stdout = execFileSync(
    process.platform === 'win32' ? 'python' : 'python3',
    [
      G3E_PROBE_SCRIPT,
      '--records', path.join(G3E_FIXTURE_ROOT, 'records.jsonl'),
      '--policies-dir', G3E_POLICIES_DIR,
    ],
    { cwd: REPO_ROOT, encoding: 'utf8', maxBuffer: 16 * 1024 * 1024 },
  );
  return JSON.parse(stdout);
}

export function buildK3SevenStageChecklist({
  truth,
  probeCase,
  mockForensics = null,
}) {
  const forbiddenId = truth.k_cases.K3.forbidden_record_id;
  const chain = probeCase?.forensic_chain ?? {};
  const preProbe = chain.pre_entitlement_relevance_probe ?? {};
  const eligible = probeCase?.eligible_record_ids ?? [];
  const entitlement = chain.entitlement_decision?.per_record_entitled ?? {};
  const mock = mockForensics ?? {};
  const steps = [
    {
      step: 1,
      name: 'record_exists',
      pass: loadCorpusRecordIds().includes(forbiddenId),
      evidence: { record_id: forbiddenId },
    },
    {
      step: 2,
      name: 'retrieval_relevant',
      pass: preProbe.target_in_referent_pool === true || preProbe.target_in_unconstrained_rank === true,
      evidence: { k3_relevance_set: truth.k_cases.K3.k3_relevance_set, pre_probe: preProbe },
    },
    {
      step: 3,
      name: 'pre_entitlement_encounter',
      pass: preProbe.target_in_referent_pool === true,
      evidence: {
        probe_kind: 'offline_pre_entitlement_relevance',
        read_only: true,
        pre_probe: preProbe,
      },
    },
    {
      step: 4,
      name: 'entitlement_rejection',
      pass: entitlement[forbiddenId] === false
        && (chain.entitlement_decision?.entitlement_rejection_count ?? 0) > 0,
      evidence: {
        per_record_entitled: entitlement[forbiddenId],
        entitlement_rejection_count: chain.entitlement_decision?.entitlement_rejection_count ?? null,
        hard_access_rejected: probeCase?.diagnostics?.hard_access_rejected ?? null,
      },
    },
    {
      step: 5,
      name: 'not_in_eligible_set',
      pass: !eligible.includes(forbiddenId),
      evidence: { eligible_record_ids_sample: eligible.slice(0, 20) },
    },
    {
      step: 6,
      name: 'not_in_character_input',
      pass: mock.forbidden_in_character_manifest !== false,
      evidence: {
        mode: mock.character_manifest_record_ids ? 'mock' : 'deferred_to_live_run',
        character_manifest_record_ids: mock.character_manifest_record_ids ?? [],
        forbidden_absent: mock.forbidden_in_character_manifest ?? true,
      },
    },
    {
      step: 7,
      name: 'not_in_output',
      pass: mock.forbidden_in_presentation !== false,
      evidence: {
        mode: mock.presentation_text ? 'mock' : 'deferred_to_live_run',
        forbidden_in_presentation: mock.forbidden_in_presentation ?? true,
      },
    },
  ];
  return {
    schema: 'issue201_g3e_k3_seven_stage_v1',
    case_id: 'K3',
    forbidden_record_id: forbiddenId,
    steps,
    all_production_stages_pass: steps.slice(0, 5).every((s) => s.pass),
    apparatus_mock_stages_pass: steps.every((s) => s.pass),
  };
}

export function adjudicateK6Stages({
  probeCase,
  policy,
  mockMove = null,
  mockPresentation = null,
}) {
  const required = policy.required_record_ids ?? [];
  const eligible = new Set(probeCase?.eligible_record_ids ?? []);
  const projected = new Set(probeCase?.forensic_chain?.projection?.projected_record_ids ?? []);
  const k6r = required.every((id) => eligible.has(id));
  const k6p = required.every((id) => projected.has(id));
  const moveText = String(mockMove?.text ?? mockMove ?? '');
  const presentationText = String(mockPresentation ?? '');
  const combined = `${moveText}\n${presentationText}`.toLowerCase();
  const k6c = required.every((id) => {
    if (!mockMove && !mockPresentation) return true;
    const token = id.replace('g3e-', '').replace(/-/g, ' ');
    return combined.includes('guest') || combined.includes('witness') || combined.includes(token);
  });
  const k6s = k6c && (combined.includes('guest') && combined.includes('witness'));
  const k6m = k6r && k6p && !k6s;
  return {
    schema: 'issue201_g3e_k6_decomposition_v1',
    case_id: 'K6',
    stages: {
      'K6-R': { pass: k6r, question: 'both required records in eligible set', required, eligible: [...eligible] },
      'K6-P': { pass: k6p, question: 'both required records projected', projected: [...projected] },
      'K6-C': {
        pass: mockMove || mockPresentation ? k6c : null,
        question: 'Primary RP consumption',
        mode: mockMove || mockPresentation ? 'mock' : 'deferred_to_live_run',
      },
      'K6-S': {
        pass: mockMove || mockPresentation ? k6s : null,
        question: 'synthesis of guests + witness',
        mode: mockMove || mockPresentation ? 'mock' : 'deferred_to_live_run',
      },
      'K6-M': {
        mediation_would_be_required: k6m,
        question: 'unresolved semantic conflict after retrieval',
        mode: 'instrumentation_only',
      },
    },
    independently_reportable: true,
  };
}

export function detectTier1Failures({
  forbiddenIds = [],
  projectedIds = [],
  manifestIds = [],
  presentationText = '',
  supersededUsed = false,
  untraceableFacts = [],
}) {
  const findings = [];
  for (const forbiddenId of forbiddenIds) {
    if (projectedIds.includes(forbiddenId)) {
      findings.push({ tier: 1, code: 'entitlement_leakage', record_id: forbiddenId, stage: 'projection' });
    }
    if (manifestIds.includes(forbiddenId)) {
      findings.push({ tier: 1, code: 'entitlement_leakage', record_id: forbiddenId, stage: 'cognition_input' });
    }
    if (presentationText.toLowerCase().includes('undisclosed debt judgment')) {
      findings.push({ tier: 1, code: 'boundary_violation', record_id: forbiddenId, stage: 'presentation' });
    }
  }
  if (supersededUsed) {
    findings.push({ tier: 1, code: 'stale_authority_misuse' });
  }
  for (const fact of untraceableFacts) {
    findings.push({ tier: 1, code: 'untraceable_knowledge', detail: fact });
  }
  return {
    schema: 'issue201_g3e_tier1_detector_v1',
    blocking_failures: findings,
    tier1_clear: findings.length === 0,
  };
}

function outcomeForCase({ caseId, policy, probeCase, arm }) {
  const eligible = probeCase?.eligible_record_ids ?? [];
  const ranked = probeCase?.ranked_ids ?? [];
  const required = policy.required_record_id
    ? [policy.required_record_id]
    : (policy.required_record_ids ?? []);
  if (policy.authoritative_record_id) required.push(policy.authoritative_record_id);

  if (caseId === 'K3') {
    const forbidden = policy.forbidden_record_id;
    if (eligible.includes(forbidden) || ranked.includes(forbidden)) {
      return 'FAIL — entitlement';
    }
    return probeCase?.diagnostics?.hard_access_rejected > 0 ? 'PASS' : 'INCONCLUSIVE / forensic insufficiency';
  }

  if (required.length === 0) {
    return ranked.length <= (policy.max_projected_items ?? 8) ? 'PASS' : 'FAIL — projection/budget';
  }

  const missingEligible = required.filter((id) => !eligible.includes(id));
  if (missingEligible.length) return 'FAIL — retrieval';
  const missingRanked = required.filter((id) => !ranked.includes(id));
  if (missingRanked.length && caseId !== 'K7') return 'FAIL — ranking/distractor';
  if (caseId === 'K5' && ranked.includes(policy.superseded_record_id)
    && !ranked.includes(policy.authoritative_record_id)) {
    return 'FAIL — stale-authority resolution';
  }
  if (caseId === 'K6' && arm === G3E_ARMS.A2_INDEXED) {
    const k6 = adjudicateK6Stages({ probeCase, policy });
    if (k6.stages['K6-M'].mediation_would_be_required) return 'MEDIATION OBLIGATION DEMONSTRATED';
  }
  return 'PASS';
}

export function buildCapabilityMatrix({ probe, arms = [G3E_ARMS.A2_INDEXED, G3E_ARMS.LEAN_A4] }) {
  const policies = loadPolicies();
  const byCaseId = new Map((probe?.cases ?? []).map((row) => [row.case_id, row]));
  const matrix = [];
  for (const arm of arms) {
    for (const policy of policies) {
      const probeCase = byCaseId.get(policy.case_id) ?? null;
      matrix.push({
        case_id: policy.case_id,
        arm,
        outcome: outcomeForCase({ caseId: policy.case_id, policy, probeCase, arm }),
        stages: policy.case_id === 'K6'
          ? adjudicateK6Stages({ probeCase, policy }).stages
          : undefined,
      });
    }
  }
  return {
    schema: 'issue201_g3e_capability_matrix_v1',
    aggregate_pass_rate: null,
    intentionally_no_aggregate: true,
    rows: matrix,
  };
}

export function exportCapabilityMatrixMarkdown(matrix) {
  const lines = [
    '# G3-E Capability Matrix (sample)',
    '',
    '| Case | Arm | Outcome |',
    '|------|-----|---------|',
  ];
  for (const row of matrix.rows) {
    lines.push(`| ${row.case_id} | ${row.arm} | ${row.outcome} |`);
  }
  lines.push('');
  lines.push('_No aggregate X/7 score by design._');
  return `${lines.join('\n')}\n`;
}

export function buildBlindPacket({ samples, answerKey }) {
  const stripped = samples.map(({ case_id, arm_label, presentation_text, dimensions_template }) => ({
    case_id,
    blind_id: crypto.randomUUID(),
    presentation_text,
    dimensions_template,
    architecture_label_stripped: true,
  }));
  return {
    schema: 'issue201_g3e_blind_knowledge_packet_v1',
    stripped_samples: stripped,
    answer_key_separate: true,
    answer_key_path: 'answer_key.json',
    answer_key: answerKey,
  };
}

export function validateBlindPacketIntegrity(packet) {
  const leaked = packet.stripped_samples.filter((row) => row.arm_label != null);
  return {
    labels_stripped: leaked.length === 0,
    answer_key_present: Boolean(packet.answer_key),
    answer_key_separate_flag: packet.answer_key_separate === true,
    sample_count: packet.stripped_samples.length,
  };
}

export function createLibrarianLedgerEntry({
  cost,
  informationSupplied,
  consumer,
  decisionChanged,
  observableBenefit,
  classification,
}) {
  const allowed = new Set([
    'uniquely_necessary',
    'useful_synthesis',
    'duplicate_compression',
    'unused',
    'harmful',
    'uncertain',
  ]);
  return {
    schema: 'issue201_g3e_librarian_ledger_v1',
    cost,
    information_supplied: informationSupplied,
    downstream_consumer: consumer,
    decision_changed: decisionChanged,
    observable_benefit: observableBenefit,
    classification: allowed.has(classification) ? classification : 'uncertain',
    causal_claim_from_instrumentation_only: false,
  };
}

export function validateLibrarianLedger(entries) {
  return {
    entry_count: entries.length,
    classifications_valid: entries.every((e) => e.schema === 'issue201_g3e_librarian_ledger_v1'),
    sample: entries[0] ?? null,
  };
}

export function buildTopologyWiringEvidence() {
  const a2Dispatch = deriveObligationSignals({
    scenarioKey: 'ayame_archive_interview',
    eligibleActors: ['ayame'],
    roleAssignments: { ayame: 'host', kizzie: 'applicant' },
    uniformProjectionEligible: true,
    retrievalManifestGap: true,
  });
  const leanOptions = { ...LEAN_A4_ROUND_OPTIONS, skipPostCommitPlot: true };
  return {
    a2_indexed_retrieval: {
      retrieval_obligation_signal: a2Dispatch.signals.some((s) => s.signal === 'retrieval_obligation'),
      indexed_retrieval_authorized: a2Dispatch.authorizations.includes('indexed_retrieval'),
      librarian_not_authorized: a2Dispatch.not_authorized.includes('default_librarian_mediation'),
      plot_absent: a2Dispatch.not_authorized.includes('synchronous_plot'),
      topology_absent: A2_TOPOLOGY_ABSENT,
    },
    lean_a4_knowledge: {
      round_options: leanOptions,
      plot_skipped: leanOptions.skipPostCommitPlot === true,
      prohibited_a2_kinds: A2_PROHIBITED_KINDS,
      librarian_mediation_expected_on_live_path: true,
    },
  };
}

export function buildForensicChainSample(probeCase) {
  const chain = probeCase?.forensic_chain ?? {};
  return {
    schema: 'issue201_g3e_forensic_chain_sample_v1',
    chain_order: [
      'knowledge_need',
      'candidate_retrieval',
      'ranking',
      'entitlement_decision',
      'provenance',
      'projection',
      'cognition_input',
      'cognition_output',
      'validation',
      'commit_presentation',
    ],
    populated_stages: chain,
    cognition_output_deferred: true,
    validation_deferred: true,
    commit_presentation_deferred: true,
  };
}

export function seedCorpusToDataDir(dataDir, memoryScopeId = 'g3e_ayame_archive_v1') {
  ensureCorpusBuilt();
  const targetDir = path.join(dataDir, 'sessions', '_story_knowledge', memoryScopeId);
  fs.mkdirSync(targetDir, { recursive: true });
  fs.copyFileSync(
    path.join(G3E_FIXTURE_ROOT, 'records.jsonl'),
    path.join(targetDir, 'records.jsonl'),
  );
  return targetDir;
}

export function runValidateApparatus({ outputDir }) {
  fs.mkdirSync(outputDir, { recursive: true });
  const corpus = validateCorpusIntegrity();
  const probe = runRetrievalProbe();
  const truth = loadTruthManifest();
  const k3Probe = probe.cases.find((row) => row.case_id === 'K3');
  const k3 = buildK3SevenStageChecklist({
    truth,
    probeCase: k3Probe,
    mockForensics: {
      forbidden_in_character_manifest: true,
      forbidden_in_presentation: true,
      character_manifest_record_ids: [],
    },
  });
  const k6Policy = loadPolicies().find((p) => p.case_id === 'K6');
  const k6Probe = probe.cases.find((row) => row.case_id === 'K6');
  const k6 = adjudicateK6Stages({
    probeCase: k6Probe,
    policy: k6Policy,
    mockMove: { text: 'Overnight guests require lease clause approval and witness notification.' },
    mockPresentation: 'Ayame cites guest prohibition and witness rule.',
  });
  const matrix = buildCapabilityMatrix({ probe });
  const matrixMd = exportCapabilityMatrixMarkdown(matrix);
  const topology = buildTopologyWiringEvidence();
  const tier1 = detectTier1Failures({
    forbiddenIds: ['g3e-private-kizzie-debt'],
    projectedIds: k3Probe?.ranked_ids ?? [],
    manifestIds: [],
    presentationText: '',
  });
  const forensicSample = buildForensicChainSample(probe.cases[0]);
  const librarianLedger = validateLibrarianLedger([
    createLibrarianLedgerEntry({
      cost: { input_tokens: 1200, output_tokens: 400 },
      informationSupplied: ['g3e-lease-guests', 'g3e-witness-rule'],
      consumer: 'character_packaging',
      decisionChanged: true,
      observableBenefit: 'synthesis_placeholder',
      classification: 'useful_synthesis',
    }),
  ]);
  const blindPacket = buildBlindPacket({
    samples: [{
      case_id: 'K1',
      arm_label: 'REDACTED_FOR_PACKET',
      presentation_text: 'Sample presentation for blind tooling validation.',
      dimensions_template: ['factual_consistency', 'knowledge_fidelity'],
    }],
    answerKey: { K1: { arm: G3E_ARMS.A2_INDEXED } },
  });
  const blindIntegrity = validateBlindPacketIntegrity(blindPacket);

  const report = {
    schema: 'issue201_g3e_apparatus_validation_v1',
    corpus,
    probe_case_count: probe.cases.length,
    k3,
    k6,
    capability_matrix: matrix,
    topology,
    tier1,
    forensic_sample: forensicSample,
    librarian_ledger: librarianLedger,
    blind_packet_integrity: blindIntegrity,
    live_campaign_executed: false,
    blind_decode_executed: false,
  };

  fs.writeFileSync(path.join(outputDir, 'apparatus-validation.json'), `${JSON.stringify(report, null, 2)}\n`);
  fs.writeFileSync(path.join(outputDir, 'capability-matrix.json'), `${JSON.stringify(matrix, null, 2)}\n`);
  fs.writeFileSync(path.join(outputDir, 'capability-matrix.md'), matrixMd);
  fs.writeFileSync(path.join(outputDir, 'retrieval-probe.json'), `${JSON.stringify(probe, null, 2)}\n`);
  fs.writeFileSync(path.join(outputDir, 'blind-packet-sample.json'), `${JSON.stringify(blindPacket, null, 2)}\n`);
  fs.writeFileSync(
    path.join(outputDir, 'blind-answer-key.json'),
    `${JSON.stringify(blindPacket.answer_key, null, 2)}\n`,
  );
  return report;
}
