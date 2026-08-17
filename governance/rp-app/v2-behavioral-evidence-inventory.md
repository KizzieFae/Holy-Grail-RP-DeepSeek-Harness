# Holy Grail V2 — Behavioral Evidence Inventory

**Status:** Baseline inventory (no new scenarios generated)  
**Purpose:** Identify existing artifacts that support **behavioral invariants** V2 must preserve.

Evidence types: deterministic tests, scenario manifests, validation run artifacts, audit documentation, regression baselines, governance archives.

---

## Summary

| Evidence class | Location | Tracked in git | Notes |
|----------------|----------|----------------|-------|
| Deterministic unit/integration tests | `autogen_rp/python/tests/` | Yes | Primary fast gate; 1348+ tests |
| Scenario manifests | `autogen_rp/python/rp_app/data/progression_simulation_scenarios/` | Yes | 40 JSON scenarios |
| Scene templates | `autogen_rp/python/data/scene_templates/` | Yes | 20 templates |
| Character cards | `autogen_rp/python/data/autogen_characters/` | **No** (gitignored user content) | **Provisioned locally** in harness baseline (22 files copied from original env; not committed) |
| RP audit sessions | `autogen_rp/python/rp_app/data/rp_audits/` | **No** (gitignored runtime output) | `session_908` copied locally for i251 test; full corpus optional |
| Validation run reports | `autogen_rp/python/validation_runs/` | Partial | Markdown + JSONL + scripts tracked |
| Regression baselines | `autogen_rp/python/data/evaluation/` | Yes | issue243/246 baselines |
| Audit interpretation spec | `autogen_rp/python/rp_app/AUDIT_DOCUMENTATION.md` | Yes | Signal semantics, tiers |
| Governance archives | `governance/archives/issue-215/` | Yes | Perception/scaffolding doctrine |

**Gap (resolved for harness dev):** Character cards provisioned locally. **Remaining gap:** one pre-existing test failure (`test_descriptive_exit_updates_authoritative_presence_state`) on both harness and upstream at same revision.

---

## By capability

### Director orchestration

| Evidence | Path / artifact |
|----------|-----------------|
| Turn selection validation | `tests/test_director_validation.py` (llm), `tests/test_orchestration_helpers.py` |
| Director JSON parsing | `tests/test_response_validation_parsing.py`, `response_validation_selection.py` tests |
| Progression / stall advisory | `tests/test_progression_enforcement.py`, `tests/test_progression_advisory.py` |
| Scenario stress | `progression_simulation_scenarios/conflict_3char.json`, `passive_observer.json` |
| Audit readout | `AUDIT_DOCUMENTATION.md` — turn selection, Director fields |

### Character execution

| Evidence | Path / artifact |
|----------|-----------------|
| Structured move parsing | `tests/test_response_validation_content.py`, `test_response_validation_parsing.py` |
| Turn runner / retry | `tests/test_turn_runner*.py`, `turn_runner_character_attempt.py` tests |
| Prompt topology (#240/#249) | `tests/test_issue_240_prompt_topology.py`, `validation_runs/issue249/` |
| Identity bleed investigation | `progression_simulation_scenarios/issue1_identity_bleed_3char_cafeteria.json` |

### Validation / bounded retry

| Evidence | Path / artifact |
|----------|-----------------|
| Drift detection | `tests/test_response_validation_drift.py` |
| Presence / must_remain | `tests/test_response_validation_presence.py`, `tests/test_presence_initiative_regressions.py` |
| Proposal coherence / legality | `tests/test_response_validation_proposal_*.py`, `tests/test_semantic_validation.py` |
| Issue #251 exit ontology | `validation_runs/issue251/`, `CANONICAL_DOCTRINE.md` |
| Certification scenarios | `cert_i234_proposal_accept_off_focal.json` |

### Narrator behavior

| Evidence | Path / artifact |
|----------|-----------------|
| Rendering contract | `tests/test_app_turn_rendering.py` (if present), architecture docs |
| Dialogue preservation | `ARCHITECTURE.md` — Narrator-mediated section |
| Audit | `AUDIT_DOCUMENTATION.md` — narrator vs character lanes |

### Continuity authority

| Evidence | Path / artifact |
|----------|-----------------|
| Core continuity | `tests/test_continuity_manager.py`, `tests/test_continuity_*.py` |
| Mutation pipeline | `tests/test_continuity_mutation_pipeline.py` |
| Excursion / reintegration | `tests/test_continuity_excursion*.py`, audit tiers #214 |
| Doctrine #224 | `ARCHITECTURE.md`, `AUDIT_DOCUMENTATION.md` |
| Tier B scenarios | `audit_i214_offstage_continuity_tier_b.json`, `audit_i225_willow_must_remain_v2_offstage_cycles.json` |
| Regression baselines | `data/evaluation/issue243_regression_baselines/`, `issue246_regression_baselines/` |

### Perception / information boundaries

| Evidence | Path / artifact |
|----------|-----------------|
| Audibility gating | `tests/test_perception_audibility.py` |
| Memory boundary scenarios | `memory_private_directed.json`, `memory_public_propagation.json` |
| Tier A perception | `audit_i191_offstage_private_return.json`, `AUDIT_DOCUMENTATION.md` Tier A |
| Issue #215 scaffolding | `governance/archives/issue-215/`, `manual_adjudication_packet_*.md` in validation_runs |

### Scene grounding

| Evidence | Path / artifact |
|----------|-----------------|
| Grounding derivation | `tests/test_scene_grounding.py` |
| Binding constraints | tests referencing `scene_grounding.py`, `prompt_grounding_assembly.py` |
| Spec | `autogen_rp/docs/scene-grounding-layer.md` |

### Character fidelity / state

| Evidence | Path / artifact |
|----------|-----------------|
| Character state model | `tests/test_character_state*.py` |
| Drift / anchors | `tests/test_response_validation_drift.py` |
| Migration format | `CHARACTER_MIGRATION_GUIDE.md` |

### User-character agency

| Evidence | Path / artifact |
|----------|-----------------|
| Operating rules | `ARCHITECTURE.md`, `README.md` |
| Bootstrap / headless parity | `tests/test_issue83_scene_start_contract.py`, `test_issue94_bootstrap_session_integration.py` |
| Trigger modes | `SCENARIO_VALIDATION_FRAMEWORK.md`, `parity_opening_trigger_smoke.json` |

### Memory (episodic)

| Evidence | Path / artifact |
|----------|-----------------|
| Episodic policy | `tests/test_memory_layer*.py`, `tests/test_episodic_memory*.py` |
| Simulation scenarios | `memory_*.json` scenario family |
| LLM simulation (optional) | `tests/test_simulation_memory_*.py` |

### Knowledge retrieval (authored)

| Evidence | Path / artifact |
|----------|-----------------|
| Retrieval seam / bundle authority | `tests/test_phase1_retrieval_seam.py`, `test_retrieved_context_merge.py` |
| Operational pilot | `data/retrieval/OPERATIONAL_RETRIEVAL_PILOT.md`, `operational_pilot_v3.json` |
| Headless smoke | `headless_template_retrieval_smoke.json` |
| Eval matrix | `scripts/run_operational_pilot_eval_matrix.py` |

### Session / resume / audit identity

| Evidence | Path / artifact |
|----------|-----------------|
| Session manager | `tests/test_session_manager.py`, `test_session_lifecycle*.py` |
| Audit identity #106/#109 | `tests/test_audit_identity*.py`, `AUDIT_DOCUMENTATION.md` |
| Headless prepare | `tests/test_prepare_headless_scene_template_id.py` |

### Headless / Streamlit parity

| Evidence | Path / artifact |
|----------|-----------------|
| Framework spec | `SCENARIO_VALIDATION_FRAMEWORK.md` |
| Headless runner | `scripts/run_scene_simulation_llm.py`, `headless_session_prepare.py` |
| Plan execution metrics | `validation_runs/plan_execution/*.json` (paths may reference old checkout) |
| Issue #83 contract tests | `tests/test_issue83_scene_start_contract.py` |

### Progression / beat-shift

| Evidence | Path / artifact |
|----------|-----------------|
| Advisory + enforcement | `tests/test_progression_enforcement.py`, `test_beat_shift_state.py` |
| Long session | `long_session.json`, `validation_runs/plan_execution/long_session.json` |

---

## Historical audit references (not in clone)

`validation_runs/plan_execution/*.json` reference audit summaries under paths like:

`E:\CascadeProjects\Holy Grail RP\autogen_rp\python\rp_app\data\rp_audits\session_388\...`

These are **pointer artifacts** to sessions from the upstream environment. They document the 2026-04-07 post-#24 validation wave (`session_388`–`session_393` per `ARCHITECTURE_OVERVIEW.md`).

**Action for harness operators:** Copy `rp_audits/session_*` folders from the original environment if audit replay is needed; otherwise use manifests + tests.

---

## Obvious evidence gaps

1. **Character cards not in repository** — gitignored; breaks UI character picker and headless tests referencing `harley_quinn`, etc.
2. **Audit session folders not in repository** — runtime-generated; historical sessions referenced by path only.
3. **Some validation JSON matrices** — may be local-only per issue251 README.
4. **LLM-marked tests** — require `DEEPSEEK_API_KEY`; skipped in fast CI-style runs.
5. **DSH-specific evidence** — none yet (DSH not installed by design).

---

## Recommended evidence use during V2

1. **Fast gate:** `pytest -m "not llm"` from `autogen_rp/python`
2. **Capability-specific:** tables above
3. **Behavioral regression:** scenario manifests + existing audit replays (when provisioned)
4. **New invariant:** add deterministic test first; scenario only when emergent behavior matters
