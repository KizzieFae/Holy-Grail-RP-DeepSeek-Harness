# Conditional semantic job contract (#215 Child B)

**Authority:** Semantic job taxonomy and forensic envelope for next-generation conditional tools.  
**Registry:** `v2/rp_runtime/src/lib/conditional-job/registry.mjs` (machine-validatable; single taxonomy authority).  
**Inference operations:** `v2/rp_runtime/src/application/llm-call-catalog.mjs` (canonical `inference_kind` / call catalog).

## Concepts

| Concept | Meaning |
|---------|---------|
| `job_kind` | Semantic capability/work (registry) |
| `canonical_inference_kind` | LLM operation (catalog); not 1:1 with `job_kind` |
| `semantic_job_id` | Stable job identity across attempts |
| `conditional_job` | Canonical forensic envelope on one evidence record |
| `trigger_record` | Eligibility/trigger provenance (records decisions; does not make policy) |

## Persistence (Phase 1)

- One **canonical** `conditional_job` envelope per `semantic_job_id` on a single execution-evidence attempt (`data/execution_evidence/<session>/attempts/<evidence_id>.json`).
- Associated inference attempts carry `correlation.semantic_job_id` and `correlation.canonical_job_evidence_id` only (no duplicated envelope).
- Zero-inference jobs use disposition-only attempts (e.g. post-commit skip).
- Session `index.json` includes `semantic_jobs.by_semantic_job_id` derived index.

## Relationships

- `evaluates` — semantic QA job → target job (`evaluation_pass_id` preserved).
- `depends_on_context` — mediation/orientation lineage.
- Consumer/consequence recorded in `consequence_summary` (Host finalize refs).

## QA compatibility projection

`decision.semantic_qa` on candidate attempts may remain temporarily as a **derived** projection for index consumers (`semantic.qa_pass_chains`). New authority: QA semantic job + `evaluates` relationship. Retirement tracked in implementation; no new consumers.

## Exemplar

`librarian_mediation` (`job_kind: knowledge_mediation`) — see `v2/rp_runtime/tests/conditional-job.test.mjs`.

## Related

- [docs/forensic-auditability-standard.md](./forensic-auditability-standard.md)
- [docs/rp-data-layout.md](./rp-data-layout.md) (execution evidence)
- [governance/records/issue-214-child-a-disposition-map-2026-09-18.md](../governance/records/issue-214-child-a-disposition-map-2026-09-18.md)
