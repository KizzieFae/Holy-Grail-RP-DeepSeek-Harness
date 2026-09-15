/**
 * Issue #201 G3-E harness-only A2 indexed retrieval adapter.
 */
import { execFileSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '../../../..');
const G3E_FIXTURE_ROOT = path.join(
  REPO_ROOT,
  'governance/records/issue201-g3e-fixtures/ayame_archive_corpus_v1',
);
const G3E_POLICIES_DIR = path.join(REPO_ROOT, 'governance/records/issue201-g3e-policies');
const G3E_PROBE_SCRIPT = path.join(REPO_ROOT, 'tools/investigation/issue201_g3e_retrieval_probe.py');

let cachedProbe = null;

function loadProbe() {
  if (cachedProbe) return cachedProbe;
  const python = process.platform === 'win32' ? 'python' : 'python3';
  const stdout = execFileSync(
    python,
    [
      G3E_PROBE_SCRIPT,
      '--records', path.join(G3E_FIXTURE_ROOT, 'records.jsonl'),
      '--policies-dir', G3E_POLICIES_DIR,
    ],
    { cwd: REPO_ROOT, encoding: 'utf8', maxBuffer: 16 * 1024 * 1024 },
  );
  cachedProbe = JSON.parse(stdout);
  return cachedProbe;
}

export function runA2IndexedRetrievalStep({ caseId, viewerCharacterId = 'ayame' }) {
  const probe = loadProbe();
  const probeCase = probe.cases.find((row) => row.case_id === caseId);
  if (!probeCase) {
    return {
      ok: false,
      reason: 'probe_case_not_found',
      case_id: caseId,
      librarian_invocation_count: 0,
    };
  }
  const rankedIds = probeCase.ranked_ids ?? [];
  const contributions = rankedIds.map((recordId, index) => ({
    record_id: recordId,
    contribution_index: index,
    provenance: (probeCase.forensic_chain?.provenance ?? []).find((p) => p.record_id === recordId)?.provenance ?? {},
  }));
  return {
    ok: true,
    schema: 'issue201_g3e_a2_indexed_retrieval_v1',
    case_id: caseId,
    viewer_character_id: viewerCharacterId,
    selection_path: probeCase.forensic_chain?.candidate_retrieval?.story_selection_path ?? null,
    eligible_record_ids: probeCase.eligible_record_ids ?? [],
    ranked_ids: rankedIds,
    projected_record_ids: probeCase.forensic_chain?.projection?.projected_record_ids ?? [],
    hard_access_rejected: probeCase.diagnostics?.hard_access_rejected ?? 0,
    pre_entitlement_relevance_probe: probeCase.forensic_chain?.pre_entitlement_relevance_probe ?? null,
    librarian_invocation_count: 0,
    contributions,
    forensic_chain: probeCase.forensic_chain,
  };
}

export function clearIndexedRetrievalProbeCache() {
  cachedProbe = null;
}
