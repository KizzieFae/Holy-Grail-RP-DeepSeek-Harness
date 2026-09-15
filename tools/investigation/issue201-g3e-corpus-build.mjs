#!/usr/bin/env node
/**
 * Issue #201 G3-E — deterministic Ayame archive corpus builder.
 * Writes fixture source + truth manifest under governance/records/.
 */
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '../..');
const FIXTURE_ROOT = path.join(
  REPO_ROOT,
  'governance/records/issue201-g3e-fixtures/ayame_archive_corpus_v1',
);

export const G3E_MEMORY_SCOPE = 'g3e_ayame_archive_v1';
export const G3E_HG_SCENE_ID = 'g3e-ayame-archive-interview';
const SEED_COMMIT = 'g3e-corpus-seed-v1';
const SEED_SESSION = 'g3e-seed-session';

function hashRecordPayload(payload) {
  const encoded = JSON.stringify(payload, Object.keys(payload).sort());
  return crypto.createHash('sha256').update(encoded, 'utf8').digest('hex');
}

function makeDerived({
  story_record_id,
  summary,
  committed_text,
  allowed_viewers,
  stable_refs = [],
  related_refs = [],
  turn_index = 100,
  grounding_markers = [],
}) {
  const base = {
    schema_version: 1,
    record_kind: 'derived',
    memory_scope_id: G3E_MEMORY_SCOPE,
    source_session_id: SEED_SESSION,
    source_domain_commit_id: SEED_COMMIT,
    hg_scene_id: G3E_HG_SCENE_ID,
    turn_index,
    event_type: 'archive_record',
    participants: ['ayame'],
    location: 'Ayame household archive',
    stable_refs,
    grounding_markers,
    evidence: {
      summary,
      committed_text,
      context_before: '',
      context_after: '',
    },
    story_record_id,
    epistemic_authority_ref: {
      ref_kind: 'establishment_decision',
      ref_payload: {
        decision_id: `g3e-est-${story_record_id}`,
        allowed_viewers,
      },
    },
    submission_authority_ref: 'issue201-g3e-corpus-builder',
    related_refs,
  };
  return {
    ...base,
    content_hash: hashRecordPayload(base),
    written_at: '2026-09-15T00:00:00.000Z',
  };
}

function anchorRecords() {
  return [
    makeDerived({
      story_record_id: 'g3e-k1-silver-2019',
      summary: '2019 silver-service rule for weekend staff',
      committed_text:
        'Household archive memo (2019): weekend staff must use the silver service '
        + 'tray sequence before 10am; Ayame household weekend staff silver service rule 2019.',
      allowed_viewers: ['ayame', 'kizzie'],
      turn_index: 19,
      grounding_markers: ['silver service', 'weekend staff', '2019'],
    }),
    makeDerived({
      story_record_id: 'g3e-k2-ayame-curfew-policy',
      summary: 'Ayame estate tenant curfew dispute policy',
      committed_text:
        'Ayame estate tenant curfew dispute policy: tenants must file written notice '
        + 'within 24 hours; governs curfew disputes on Ayame grounds.',
      allowed_viewers: ['ayame', 'kizzie'],
      stable_refs: [{ ref_kind: 'policy', stable_ref: 'policy:ayame-curfew-disputes' }],
      turn_index: 42,
    }),
    makeDerived({
      story_record_id: 'g3e-distract-riverside-curfew',
      summary: 'Riverside annex curfew policy distractor',
      committed_text:
        'Riverside annex tenant curfew policy: disputes referred to annex board; '
        + 'high semantic overlap with estate curfew language but wrong estate.',
      allowed_viewers: ['ayame', 'kizzie'],
      stable_refs: [{ ref_kind: 'policy', stable_ref: 'policy:riverside-curfew' }],
      turn_index: 43,
    }),
    makeDerived({
      story_record_id: 'g3e-distract-annex-guest-policy',
      summary: 'Annex guest policy distractor',
      committed_text:
        'Annex guest overnight policy: guests require annex manager approval; '
        + 'tenant curfew dispute wording similar to Ayame policy but annex scope.',
      allowed_viewers: ['ayame', 'kizzie'],
      turn_index: 44,
    }),
    makeDerived({
      story_record_id: 'g3e-private-kizzie-debt',
      summary: 'Kizzie prior tenancy financial judgment (private)',
      committed_text:
        'Prior tenancy financial difficulties: undisclosed debt judgment against Kizzie '
        + 'from previous tenancy; financial debt prior tenancy judgment confidential to Kizzie.',
      allowed_viewers: ['kizzie'],
      stable_refs: [{ ref_kind: 'character', stable_ref: 'char:kizzie' }],
      turn_index: 55,
      grounding_markers: ['financial', 'prior tenancy', 'debt', 'judgment'],
    }),
    makeDerived({
      story_record_id: 'g3e-private-ayame-master-key',
      summary: 'Ayame household master-key custody rule (private)',
      committed_text:
        'Household-private master-key custody rule: only Ayame may hold the master key '
        + 'overnight; staff must sign the custody ledger.',
      allowed_viewers: ['ayame'],
      turn_index: 61,
    }),
    makeDerived({
      story_record_id: 'g3e-curfew-2019-9pm',
      summary: 'Superseded weeknight curfew 9pm (2019)',
      committed_text:
        'Weeknight curfew policy (2019): tenants must be inside by 9pm Sunday through Thursday.',
      allowed_viewers: ['ayame', 'kizzie'],
      stable_refs: [{ ref_kind: 'policy', stable_ref: 'policy:weeknight-curfew' }],
      turn_index: 70,
    }),
    makeDerived({
      story_record_id: 'g3e-curfew-2024-11pm',
      summary: 'Authoritative weeknight curfew 11pm (2024 revision)',
      committed_text:
        'Weeknight curfew policy (2024 revision): tenants must be inside by 11pm Sunday through Thursday.',
      allowed_viewers: ['ayame', 'kizzie'],
      stable_refs: [{ ref_kind: 'policy', stable_ref: 'policy:weeknight-curfew' }],
      related_refs: [{ rel: 'supersedes', target_id: 'g3e-curfew-2019-9pm' }],
      turn_index: 71,
    }),
    makeDerived({
      story_record_id: 'g3e-lease-guests',
      summary: 'Lease clause §4 guest prohibition',
      committed_text:
        'Lease clause §4: overnight guests prohibited without written landlord approval; '
        + 'tenant may not host guests overnight without exception process.',
      allowed_viewers: ['ayame', 'kizzie'],
      stable_refs: [{ ref_kind: 'lease', stable_ref: 'lease:clause-4-guests' }],
      turn_index: 80,
    }),
    makeDerived({
      story_record_id: 'g3e-witness-rule',
      summary: 'Witness-notification requirement for guest exceptions',
      committed_text:
        'Witness-notification rule: any approved guest exception requires a household witness '
        + 'signature logged within 12 hours of arrival.',
      allowed_viewers: ['ayame', 'kizzie'],
      stable_refs: [{ ref_kind: 'policy', stable_ref: 'policy:witness-notification' }],
      turn_index: 81,
    }),
    makeDerived({
      story_record_id: 'g3e-k7-household-open-policy',
      summary: 'General household open-policy reference for volume pressure',
      committed_text:
        'Ayame household open policy compendium index: general household policies for staff, '
        + 'tenants, and archive consultation during interviews.',
      allowed_viewers: ['ayame', 'kizzie'],
      turn_index: 90,
    }),
  ];
}

function fillerRecords(startIndex, count) {
  const rows = [];
  for (let i = 0; i < count; i += 1) {
    const idx = startIndex + i;
    rows.push(makeDerived({
      story_record_id: `g3e-filler-household-${String(idx).padStart(3, '0')}`,
      summary: `Household admin record ${idx}`,
      committed_text:
        `Ayame household administrative filing ${idx}: pantry inventory, linen rotation, `
        + `or staff scheduling note unrelated to archive interview queries.`,
      allowed_viewers: ['ayame', 'kizzie'],
      turn_index: 100 + idx,
    }));
  }
  return rows;
}

function distractorRecords(startIndex, count) {
  const estates = ['riverside', 'annex', 'harbor', 'meadow'];
  const rows = [];
  for (let i = 0; i < count; i += 1) {
    const idx = startIndex + i;
    const estate = estates[i % estates.length];
    rows.push(makeDerived({
      story_record_id: `g3e-distract-${estate}-${String(idx).padStart(3, '0')}`,
      summary: `Distractor policy ${estate} ${idx}`,
      committed_text:
        `${estate} estate policy memo ${idx}: tenant curfew dispute guest overnight wording `
        + `similar to Ayame archive topics but wrong applicant estate context.`,
      allowed_viewers: ['ayame', 'kizzie'],
      turn_index: 300 + idx,
    }));
  }
  return rows;
}

function entityFactRecords(startIndex, count) {
  const rows = [];
  for (let i = 0; i < count; i += 1) {
    const idx = startIndex + i;
    rows.push(makeDerived({
      story_record_id: `g3e-entity-fact-${String(idx).padStart(3, '0')}`,
      summary: `Authorized entity fact ${idx}`,
      committed_text:
        `Ayame authorized household fact ${idx}: staff credentialing, applicant reference `
        + `cross-check, or estate-specific operational detail for archive consultation.`,
      allowed_viewers: ['ayame', 'kizzie'],
      turn_index: 400 + idx,
    }));
  }
  return rows;
}

function privateScopedRecords(startIndex, count) {
  const viewers = [['ayame'], ['kizzie'], ['ayame'], ['kizzie']];
  const rows = [];
  for (let i = 0; i < count; i += 1) {
    const idx = startIndex + i;
    rows.push(makeDerived({
      story_record_id: `g3e-private-scoped-${String(idx).padStart(3, '0')}`,
      summary: `Private scoped record ${idx}`,
      committed_text:
        `Role-scoped private household note ${idx}: confidential staff or applicant detail `
        + `with restricted viewer entitlement.`,
      allowed_viewers: viewers[i % viewers.length],
      turn_index: 500 + idx,
    }));
  }
  return rows;
}

function dependencyGroups() {
  const groups = [];
  for (let g = 0; g < 8; g += 1) {
    const a = `g3e-dep-${g}-a`;
    const b = `g3e-dep-${g}-b`;
    groups.push(
      makeDerived({
        story_record_id: a,
        summary: `Dependency group ${g} part A`,
        committed_text: `Multi-record dependency set ${g} part A for archive cross-reference.`,
        allowed_viewers: ['ayame', 'kizzie'],
        related_refs: [{ rel: 'requires', target_id: b }],
        turn_index: 600 + g * 2,
      }),
      makeDerived({
        story_record_id: b,
        summary: `Dependency group ${g} part B`,
        committed_text: `Multi-record dependency set ${g} part B completes archive cross-reference.`,
        allowed_viewers: ['ayame', 'kizzie'],
        turn_index: 601 + g * 2,
      }),
    );
  }
  return groups;
}

export function buildCorpusRecords() {
  const anchors = anchorRecords();
  const fillers = fillerRecords(1, 180);
  const distractors = distractorRecords(1, 40);
  const entityFacts = entityFactRecords(1, 35);
  const privateScoped = privateScopedRecords(1, 25);
  const deps = dependencyGroups();
  const all = [...anchors, ...fillers, ...distractors, ...entityFacts, ...privateScoped, ...deps];
  all.sort((a, b) => String(a.story_record_id).localeCompare(String(b.story_record_id)));
  return all;
}

function buildTruthManifest(recordIds) {
  return {
    schema: 'issue201_g3e_truth_manifest_v1',
    corpus_id: 'ayame_archive_corpus_v1',
    memory_scope_id: G3E_MEMORY_SCOPE,
    record_count: recordIds.length,
    k_cases: {
      K1: {
        required_record_id: 'g3e-k1-silver-2019',
        query_relevance_terms: ['silver service', 'weekend staff', '2019'],
        depth_class: 'deep_index',
      },
      K2: {
        required_record_id: 'g3e-k2-ayame-curfew-policy',
        forbidden_distractor_ids: ['g3e-distract-riverside-curfew', 'g3e-distract-annex-guest-policy'],
        distractor_similarity_class: 'high_semantic_overlap',
      },
      K3: {
        forbidden_record_id: 'g3e-private-kizzie-debt',
        kizzie_entitled: true,
        ayame_entitled: false,
        expected_query_relevance: 'high',
        expected_referent_match: true,
        forbidden_in_projection: true,
        forbidden_in_character_manifest: true,
        forbidden_in_presentation: true,
        k3_relevance_set: ['financial', 'prior tenancy', 'debt', 'judgment'],
      },
      K4: {
        required_record_id: 'g3e-private-ayame-master-key',
        ayame_entitled: true,
      },
      K5: {
        authoritative_record_id: 'g3e-curfew-2024-11pm',
        superseded_record_id: 'g3e-curfew-2019-9pm',
        supersedes_link: 'g3e-curfew-2024-11pm supersedes g3e-curfew-2019-9pm',
      },
      K6: {
        required_record_ids: ['g3e-lease-guests', 'g3e-witness-rule'],
      },
      K7: {
        optional_required_record_id: 'g3e-k7-household-open-policy',
        max_projected_items: 8,
        max_projected_chars: 8000,
        irrelevant_ratio_threshold: 'logged_not_gating',
      },
    },
    required_anchor_ids: [
      'g3e-k1-silver-2019',
      'g3e-k2-ayame-curfew-policy',
      'g3e-distract-riverside-curfew',
      'g3e-distract-annex-guest-policy',
      'g3e-private-kizzie-debt',
      'g3e-private-ayame-master-key',
      'g3e-curfew-2019-9pm',
      'g3e-curfew-2024-11pm',
      'g3e-lease-guests',
      'g3e-witness-rule',
      'g3e-k7-household-open-policy',
    ],
  };
}

export function writeCorpusArtifacts({ fixtureRoot = FIXTURE_ROOT } = {}) {
  fs.mkdirSync(fixtureRoot, { recursive: true });
  const records = buildCorpusRecords();
  const jsonl = records.map((row) => JSON.stringify(row)).join('\n') + '\n';
  const recordsPath = path.join(fixtureRoot, 'records.jsonl');
  fs.writeFileSync(recordsPath, jsonl, 'utf8');
  const recordsSha = crypto.createHash('sha256').update(jsonl, 'utf8').digest('hex');
  const recordIds = records.map((r) => r.story_record_id);
  const truth = buildTruthManifest(recordIds);
  const truthPath = path.join(fixtureRoot, 'truth_manifest.json');
  fs.writeFileSync(truthPath, `${JSON.stringify(truth, null, 2)}\n`, 'utf8');
  const manifest = {
    schema: 'issue201_g3e_corpus_manifest_v1',
    corpus_id: 'ayame_archive_corpus_v1',
    memory_scope_id: G3E_MEMORY_SCOPE,
    record_count: records.length,
    records_sha256: recordsSha,
    built_at: '2026-09-15T00:00:00.000Z',
    builder: 'tools/investigation/issue201-g3e-corpus-build.mjs',
    reproducible: true,
  };
  const manifestPath = path.join(fixtureRoot, 'corpus_manifest.json');
  fs.writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, 'utf8');
  return { records, truth, manifest, fixtureRoot, recordsPath, truthPath, manifestPath };
}

function main() {
  const result = writeCorpusArtifacts();
  console.log(JSON.stringify({
    record_count: result.records.length,
    fixture_root: result.fixtureRoot,
    records_sha256: result.manifest.records_sha256,
  }, null, 2));
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main();
}
