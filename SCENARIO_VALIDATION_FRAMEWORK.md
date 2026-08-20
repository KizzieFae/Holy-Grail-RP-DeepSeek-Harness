# Scenario Validation Framework

**Canonical document** for behavioral validation in Holy Grail RP. Governance standing summary: [governance/sources/architecture-overview.md](./governance/sources/architecture-overview.md). Lives at the repository root alongside [MODULE_INDEX.md](./MODULE_INDEX.md).

---

## Purpose

Holy Grail RP validates behavior at two complementary levels:

1. **Deterministic tests** — domain contracts, manifest shape, validation rules, continuity invariants (`v2/domain/tests/`, `v2/tests/`).
2. **Scenario-based evaluation** — fixed JSON manifests describing casts, openings, triggers, and intended behavioral focus; used for manifest regression, structured eval profiles, and (when a live harness is available) LLM-driven runs with audit artifacts.

Unit tests verify correctness of modules. Scenario validation verifies **emergent behavior** against designed situations.

---

## Core principle

Major behavioral changes should be evidenced against **controlled scenario definitions** and/or audited runs—not only isolated unit tests.

---

## Scenario definitions

### Storage

Scenario manifests live under:

```text
data/fixtures/progression_simulation_scenarios/<scenario_id>.json
```

Loaded by `v2/domain/modules/progression_simulation_scenarios.py` via `fixtures_data_dir()`.

The `id` field inside each file must match `<scenario_id>` (filename without `.json`).

### Required and common fields

Each scenario defines:

| Field | Role |
|-------|------|
| `character_card_ids` | Cast — resolved to cards under `data/characters/` |
| `opening_description` | Opening context text |
| `trigger_text` | First-round user trigger (see `startup_trigger_mode`) |
| `startup_trigger_mode` | `"parity"` \| `"overlay"` — see module docstring for resolution |
| `max_turns` | Turn limit |
| `title`, `intent` | Human-readable purpose |
| `location`, `initial_tension`, `initial_phase` | Scene setup |
| `seed_escalating_issue`, `seed_issue` | Optional seeded issues |
| `beat_shift_active` | Optional beat-shift flag |
| `expected_pressure_profile` | Optional design hint (`low` \| `medium` \| `high`) |

**Optional:**

- `scene_template_id` — loads template from `data/scene_templates/` through the same bootstrap spine as the application UI
- `scene_template_role_assignments` — required when `scene_template_id` is set; maps each cast member to a template role
- `cohesion_policy` — production templates use `anchor_only` (see `scene_template_cohesion.py`)

**Trigger semantics:** `effective_round1_trigger_text_headless` in `progression_simulation_scenarios.py` resolves first-round triggers for harness paths. Application UI uses parity-style opening triggers after scene start.

### Manifest regression (no live LLM)

```bash
python -m pytest v2/domain/tests/test_audit_i191_tier_a_manifest.py -q
python -m pytest v2/domain/tests/test_issue_234_cert_manifest.py -q
python -m pytest v2/domain/tests/test_response_validation_investigation_recall.py -q
```

Add or extend domain tests when introducing new manifest contracts.

---

## Current validation mechanisms

| Mechanism | What it proves |
|-----------|----------------|
| `v2/domain/tests/` | Domain semantics, manifest loading, validation, continuity, retrieval assembly |
| `v2/tests/` | Integration, Domain Host wiring, repository architecture invariants |
| `v2/rp_runtime` (`npm test`) | DSH round orchestration against Domain Host |
| `tools/investigation/` | Offline analysis of existing `*_full.json` audit trees |

### Live LLM scenario runs

A shipped **headless LLM scenario CLI** is **not** part of the current repository. Live multi-turn scenario execution with `--audit` and `structured_eval` metrics is planned as a **Domain Host + RP runtime harness** on the production path.

Until that harness ships:

- Use **domain manifest tests** for scenario contract regression.
- Use **integration and runtime tests** for orchestration proof.
- Use **offline investigation tools** to analyze audit JSON produced by supervised runs or historical evidence.

Do not point operators at deleted runner scripts or non-canonical data trees.

---

## Authored retrieval (OFF / ON)

Activation is **only** via environment variable:

```text
RP_RETRIEVED_CONTEXT_INDEX=<path-to-compiled-index.json>
```

Domain Host: `v2/domain_api/knowledge_service.py`, `retrieval_selection.py`, `compiled_index_provider.py`; prompt formatting in `v2/domain/modules/prompt_builders.py`.

**Accepted baseline content:** character `lore_facts` + template `role_slots` + refined `premise`. Reference index: `data/retrieval/compiled/operational_pilot_v3.json`.

Historical pilot artifact map (closed runbook): [governance/records/operational-retrieval-pilot.md](./governance/records/operational-retrieval-pilot.md).

---

## Structured evaluation

`structured_eval` profiles and investigation recall hooks live in the domain library (`semantic_eval_profiles.py`, `response_validation_investigation_recall.py`). Domain tests cover profile shape and manifest-linked expectations.

When a live harness returns, metrics JSON should be written under `data/investigation_runs/` or another gitignored path—not the repository root.

---

## Audits and offline analysis

When audit mode is enabled on a supervised run, per-turn artifacts land under `data/rp_audits/` (gitignored). Interpretation workflow: [docs/audit-workflows.md](./docs/audit-workflows.md).

Offline tools (`tools/investigation/`) read audit trees only; they do not change runtime behavior.

---

## Console captures

Do not write ad-hoc simulation captures to the repository root. Use `data/investigation_runs/` or another gitignored directory under `data/`.

---

## Related docs

- [governance/sources/architecture-overview.md](./governance/sources/architecture-overview.md) — behavioral validation as a core layer
- [MODULE_INDEX.md](./MODULE_INDEX.md) — scenario and audit module routing
- [governance/sources/audit-semantics.md](./governance/sources/audit-semantics.md) — program audit semantics
- [docs/audit-workflows.md](./docs/audit-workflows.md) — RP session-audit procedure
- [docs/rp-data-layout.md](./docs/rp-data-layout.md) — sessions, audits, fixtures
- [docs/testing.md](./docs/testing.md) — pytest commands and scope
