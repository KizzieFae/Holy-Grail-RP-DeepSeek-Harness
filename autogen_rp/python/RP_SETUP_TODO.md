# RP App - Step-by-Step Implementation (Updated)

**Goal**: A multi-agent roleplay system with strong continuity, deterministic orchestration, and future integration with knowledge-driven packet-based architecture.

This roadmap reflects the correct execution order:

1. Stabilize and validate the current runtime
2. Introduce the packet seam (no behavior change) — **character prompt path complete** (Phase 0.5 closure)
3. **Scoped Phase 1 (retrieval-lock / validation)** — **complete** (bundle seam invariant, tests, snapshots; no new retrieval architecture). Broader scenario re-validation / Director–Narrator packet completeness remains **future** work.
3b. **Phase 4A (retrieval workflow operationalization)** — **complete** — authored retrieval **OFF/ON** is **standard** in headless simulation + audits (`retrieval_session`, `retrieval_summary`, strict verify); **no** selector change. See **Phase 4A** section below; **SCENARIO_VALIDATION_FRAMEWORK.md** / **AUDIT_DOCUMENTATION.md**.
4. Only then expand into retrieval **product** behavior (Phase 2+ index, lanes, etc. — see Phase 2; **Phase 2 is complete**; further retrieval architecture is **not** the default next priority after 4A).
5. Only after that begin ingestion work

---

# Phase 0 — Stabilization & Validation (**complete — v1 checkpoint**; progression: `tests/Testing TODOs/progression layer validation status v1.md`, repo root `SCENARIO_VALIDATION_FRAMEWORK.md`; player-text perception closure: section **G**; turn selection v1 policy: section **I** below)

## A. Structured scenario validation

- [x] Run 5–10 repeatable RP scenarios:
  - [x] one-on-one interaction
  - [x] emotional/relationship tension
  - [x] multi-character (3+ actors)
  - [x] long-session continuity
  - [x] reload-after-save

- [x] Ensure each scenario is reproducible

## B. Validate core behaviors

- [x] Turn selection correctness
- [x] Continuity integrity
- [x] Validation behavior
- [x] Character fidelity (no drift, no flattening)

## C. Failure classification

- [x] Log all failures via audit system
- [x] Categorize failures by layer:
  - [x] continuity
  - [x] orchestration
  - [x] validation
  - [x] prompt surface (last resort)

## D. Exit criteria

- [x] No recurring unclassified failures
- [x] All known failure types mapped to a layer
- [x] System behaves predictably across all test scenarios

---

## E. Progression Advisory Validation

- [x] Confirm plateau detection works
- [x] Confirm advisory triggers appropriately
- [x] Confirm beat-shifts introduce real state changes
- [x] Confirm no continuity corruption
- [x] Confirm characters remain consistent under pressure

---

## F. Scene Grounding Validation

- [x] Confirm settled facts do not re-litigate
- [x] Confirm grounding remains read-only
- [x] Confirm no unintended writes to continuity or character state

---

## G. Player-text perception & knowledge boundaries (Phase 0 closure)

- [x] Character prompts respect knowledge boundaries for **player** input (no global raw trigger for non-recipients)
- [x] All character-visible player text paths use **`perception_audibility`** rules:
  - [x] `TRIGGER FOR THIS BEAT`
  - [x] Beat-shift `LATEST PLAYER INPUT` (character suffix)
  - [x] User lines inside `RECENT SCENE TRANSCRIPT`
- [x] Scenario 1 — knowledge-boundary stress (`memory_private_directed`) **passes** (validated rerun: audit **`session_107`**)
- [x] Simulation pipeline matches Streamlit: same `app_turn_prompting` / `build_recent_dialogue_history_for_viewer` path; audits reflect **filtered** character system prompts
- [x] Director unchanged: full raw trigger and unfiltered user lines in orchestration transcript (`viewer_character_name=None`)
- [x] All **confirmed** Phase 0 runtime blockers resolved (including global player-trigger knowledge leak)

**Not claimed complete in Phase 0** (explicit follow-up, not blockers):

- [ ] Tighter **ambiguity** handling (MVP: ambiguous player input defaults to **public**)
- [ ] **Heuristic** improvements for whisper / directed inference on free-text player lines
- [ ] **Narrator** alignment with player-text perception boundaries
- [ ] Additional **memory** scenarios / memory-layer validation beyond existing checks

### Phase 0 completion note — player-text visibility

The Phase 0 blocker **character prompt knowledge leak from global player trigger visibility** is **closed**. Implementation: recipient-filtered player text via **`player_text_for_character_viewer`** in `perception_audibility.py`, invoked from **`app_turn_prompting`** (per-character trigger + beat-shift suffix) and **`build_recent_dialogue_history_for_viewer`** (user transcript lines). **Director** still receives the full raw trigger for selection. **MVP limitation:** ambiguous player input remains **public** by default to avoid over-redaction; revisit in a later phase.

---

## H. Prompt-layer stability — binding + evidence discipline (**complete**)

High-salience **character** prompt constraints only (no new validators, retries, or schema changes for this track):

- [x] **BINDING CONSTRAINTS (HIGH PRIORITY):** Filtered subset of settled scene facts (allowlisted `(category, key)` pairs), same `scene_grounding` rebuild pipeline as SETTLED SCENE FACTS; `format_character_binding_constraints_section` in `scene_grounding.py`; passed via `app_turn_prompting` as `scene_binding_constraints_section`; injected in `prompt_builders.build_character_turn_prompt` after priority sections 1–7 and **before** **OUTPUT RULES**
- [x] **EVIDENCE & AUTHORITY DISCIPLINE (HIGH PRIORITY):** Static block in `prompt_builders.py` (`_EVIDENCE_AUTHORITY_DISCIPLINE_BLOCK`) immediately **after** the binding block and **before** **OUTPUT RULES** — reduces unsupported who/what/where/when stated as clinical / institutional / “noted” truth; preserves pressure, accusation, intimidation, and contestable bluffing
- [x] **Stress scenarios:** `willow_dorm_binding_stress`, `arkham_multi_character_stress`, `arkham_multi_character_stress_long` in `rp_app/data/progression_simulation_scenarios/`
- [x] **Audit visibility:** binding-related metadata on character audits and failure logging (`turn_runner_audit.py`, `audit_logger_serialization.py`, `app_turn_audit.py`)
- [x] **Observed on audited runs:** same-character **denial** of promoted binding state not seen; dialogue shifts toward **enforcement / resistance**; **unsupported authoritative specifics** (e.g. fabricated perimeter placement as chart fact) **not reproduced** in evaluated Willow/Arkham sessions — stochastic; re-run for regression

---

## I. Turn selection policy — v1 baseline refinement (**complete**)

**Goal:** Cut down continuation double-speaks, avoid progression override fighting a coherent continuation when the last spotlight already matches the continuation actor, and encode P3/P4 vs P1 explicitly for clarity and safe refactors.

**Implemented**

- [x] **C2 (continuation):** If `continuation_override_actor` is available but equals the **last non-empty** `spotlight_history` speaker, **do not** take the continuation hard route — fall through to Director (`app_turn_director.py`).
- [x] **O4 / F2 (explicit):** `p1_continuation_applied` gates progression override resolution and `apply_participation_fairness_to_decision` so P3/P4 do not run when P1 continuation actually fired (guard is redundant with control flow today but documents policy).
- [x] **Validation:** `validate_turn_selection_decision` (`response_validation_selection.py`) uses the same C2 rule so Director picks after a C2 skip are not flagged as continuation preemption failures.
- [x] **Attribution:** Non–hard-route `selection_attribution` records include **`continuation_override_skipped_c2`** when C2 applied (`selection_attribution.py` / `record_selection_attribution_event`).
- [x] **Tests:** `test_continuation_override_c2_skips_when_last_spotlight_matches` (`test_orchestration_helpers.py`), `test_phase5_turn_selection_c2_skips_continuation_preemption_when_last_spotlight_matches` (`test_phase3_regressions.py`).
- [x] **Spot check:** `conflict_3char` and `arkham_multi_character_stress` headless runs (2× each) showed no new instability; continuation hard routes were sparse in that slice.

**Explicitly not in v1:** C1 / extra continuation state, O5 semantic gating for override, threshold tuning, or new selection subsystems.

**Ongoing (normal quality / scenario runs — no dedicated C2-only validation phase):** Note frequency of `continuation_override_skipped_c2: true` in attribution; whether same-speaker continuation beats feel rarer; whether override less often fights coherent continuation. Optional short bullet in future quality reports.

**Related:** Architecture-quality harness variants (`arch_quality_variants.py`, `--arch-quality-variant` on headless sim) are unchanged by this policy.

---

# Phase 0.5 — Packet Seam Introduction (NO BEHAVIOR CHANGE) (**complete — character prompt path**)

**Goal**: Introduce a structured runtime interface (packets) without changing system behavior.

### Phase 0.5 closure — character prompt path (implemented & validated)

**Implemented**

- **`CharacterPromptInputAssembly`** — single authoritative assembly of all inputs needed for **`prompt_builders.build_character_turn_prompt`** (seam boundary). Populated once per character turn in **`app_turn_prompting.build_character_turn_prompt`** after retrieval/grounding assembly.
- **No dual derivation** — **`live_bundle_from_character_prompt_assembly`** and **`runtime_packets_from_character_prompt_assembly`** consume the **same** assembly; live kwargs and packets are not built from parallel parameter lists.
- **Shadow comparison** (`RP_PACKET_SHADOW_COMPARE`, default off): required **structural** equality of live vs reconstructed prompt-input bundles; optional **core prompt text** check (same **`build_character_turn_prompt_text_fn`**, beat-shift / progression / other suffix layers excluded from that check). Side-effect free beyond logging.
- **Parity corpus** — **10** parametrized scenarios in **`tests/test_runtime_packets.py`** (offstage-shaped inputs, no-present fallback cast, high issue pressure, multi-character cast, grounding/binding strings, cross-session slices, session metadata on scene packet, multi-source **`RetrievedContextBundle`**, etc.) plus core prompt-text parity test when bundles match.
- **Runtime** — retrieval, prompt wording, continuity, Director, Narrator, validation unchanged with shadow off.

**Validated**

- Unit/parity tests green; headless **`scripts/run_scene_simulation_llm.py`** runs with **`RP_PACKET_SHADOW_COMPARE=1`** over multiple scenarios (including **`arrival_setup`** with **`--episodic-memory`**) — **zero** packet shadow structured mismatches observed in captured output.

**Known limitation (documentation)**

- Shadow comparison results log to **stderr** via **`rp_app.packet_shadow`**; they are **not** persisted in audit JSON today. Follow-up (optional): record pass/fail in **`rp_app/data/rp_audits`** for CI-style checks.

#### Phase 0.5 — Packet seam (checklist — character path)

- [x] RuntimeScenePacket introduced (authored/stable scene slice only; **character prompt support** — not yet a full Director/Narrator scene abstraction)
- [x] RuntimeCharacterPacket introduced (dynamic per-character slice)
- [x] RetrievedContextBundle introduced (Phase 0.5: empty stub; **Phase 2:** typed items + authored retrieval — see Phase 2)
- [x] Single assembly + packet build integrated into **`app_turn_prompting`** (character path)
- [x] Structured prompt-input bundle reconstruction implemented
- [x] Structured comparison (live vs packet-derived) implemented
- [x] No prompt/output behavior change (validated)
- [x] Shadow compare gated behind env flag
- [x] Test coverage: packet build, comparison, parity corpus

---

**Subsections A–H below** are **forward-looking** packaging / completeness goals (Phase 1+ and broader packet model). They are **not** the Phase 0.5 **character-path** exit gate; closure is defined in **Phase 0.5 closure** above.

## A. Freeze baseline behavior

- [ ] Select 2–3 canonical test scenarios
- [ ] Save audit outputs for comparison
- [ ] Record expected:
  - [ ] turn selection
  - [ ] progression behavior
  - [ ] grounding behavior
  - [ ] continuity behavior

- [ ] Guardrails:
  - [ ] No changes to:
    - [ ] turn_runner*
    - [ ] app_turn_director.py
    - [ ] response_validation*
    - [ ] progression_enforcement.py
  - [ ] Changes limited to:
    - [ ] packet builders
    - [ ] prompt assembly glue

**Exception (documented baseline, not packet work):** The **v1 turn selection policy** (Phase 0 **§I** — continuation C2, explicit P1 vs P3/P4 guards, matching selection validation) intentionally touches `app_turn_director.py` and `response_validation_selection.py`. Phase 0.5 implementation should still avoid **unrelated** edits in those modules.

---

## B. Define packet structures

### ScenePacket

- [ ] template_id
- [ ] premise / opening_text
- [ ] location / time
- [ ] progression_profile
- [ ] role_slots / constraints

Runtime fields:
- [ ] present_characters
- [ ] offstage_characters
- [ ] scene_phase
- [ ] tension level
- [ ] recent events / delta

---

### CharacterPacket

Static:
- [ ] name / description
- [ ] personality / voice
- [ ] goals
- [ ] lore facts

Runtime:
- [ ] current_objective
- [ ] short_term_tactic
- [ ] emotional_state
- [ ] stress_level

---

### CharacterRuntimeContextPacket

- [ ] active issues
- [ ] recent public events
- [ ] summary blocks
- [ ] canon anchors
- [ ] interpretations
- [ ] filtered dialogue
- [ ] filtered moves
- [ ] scene grounding

---

### RetrievedContextBundle

- [x] Phase 0.5: stub (empty `RetrievedContextBundle`)
- [x] Phase 2: `RetrievedItem` + bounded bundle; see **Phase 2** below

---

## C. Build packet builders

- [ ] `build_runtime_scene_packet(...)`
- [ ] `build_runtime_character_packet(...)`
- [ ] `build_character_runtime_context_packet(...)`

Sources:
- [ ] templates
- [ ] character cards
- [ ] continuity_manager
- [ ] character_state_manager
- [ ] perception filtering
- [ ] scene grounding

---

## D. Shadow-mode integration

- [ ] Generate packets alongside current prompt inputs
- [ ] Do NOT replace prompt builder yet

- [ ] Create adapters:
  - [ ] packet → prompt inputs

- [ ] Compare:
  - [ ] scene state
  - [ ] issues
  - [ ] summaries
  - [ ] grounding
  - [ ] dialogue windows
  - [ ] role mappings

- [ ] Log mismatches only

---

## E. File-level integration

### app_turn_prompting.py

- [ ] Entry point for packet building
- [ ] Shadow comparison logging

### prompt_builders.py

- [ ] Validate packet completeness

### character_state_manager.py

- [ ] Source runtime state (no changes)

### continuity_manager.py

- [ ] Source truth data (no logic changes)

### scene_grounding.py

- [ ] Provide grounding into packet

### app_turn_director.py

- [ ] Reference only (no edits) — **except** documented baseline policy updates (Phase 0 **§I**); packet seam work must not piggyback unrelated director changes

---

## F. Data separation enforcement

- [ ] Scene owns:
  - [ ] situation
  - [ ] pressure
  - [ ] constraints

- [ ] Character owns:
  - [ ] voice
  - [ ] goals
  - [ ] behavior

- [ ] Remove duplication at packet level (no prompt edits yet)

---

## G. Validation

- [ ] Re-run baseline scenarios
- [ ] Compare:
  - [ ] audit outputs
  - [ ] narrative outputs
  - [ ] progression metrics

- [ ] Track mismatches:
  - [ ] missing fields
  - [ ] duplication
  - [ ] filtering errors
  - [ ] grounding mismatch

---

## H. Exit criteria

- [ ] Packets fully represent runtime inputs
- [ ] No behavior drift
- [ ] Prompt inputs reproducible from packets
- [ ] Director / validation unchanged

---

# Phase 1 — Packet-Aligned Runtime Validation (**scoped retrieval-lock / validation — complete**)

This milestone was **intentionally narrow:** **validation and enforcement**, not new retrieval product behavior.

**What Phase 1 did *not* do (explicit):**

- No new retrieval capabilities, **no** selector logic changes, **no** new lanes or branches in `retrieved_context_select.py`
- No graph/vector retrieval, **no** retrieval-agent or Director-side retrieval planning
- **No** change to runtime authority (continuity / grounding remain authoritative; retrieved stays **non-authoritative**)
- **No** change to `prompt_builders` wording or placement beyond what existing tests already asserted (Phase 1 added **tests** that **document** current layout)

**What Phase 1 did (closure summary):**

- **Inventory:** Confirmed **no retrieval seam bypass** on the character path — bundle is built only in **`app_turn_prompting.build_character_turn_prompt`**, stored on **`CharacterPromptInputAssembly.retrieved_bundle`**.
- **Assembly invariant (locked):** **`RetrievedContextBundle`** is the **behavioral source** for retrieval in the seam; **`retrieved_context_section`** is a **pure derived** artifact via **`format_retrieved_context_for_prompt(bundle)`** (through **`live_bundle_from_character_prompt_assembly`** only).
- **Tests added:** assembly invariant (`test_phase1_assembly_invariant_section_is_pure_format_of_bundle`); **golden/snapshot** bundle composition (`tests/test_phase1_retrieval_seam.py`, `test_phase1_merge_bundle_composition_snapshot_stable` in `test_retrieved_context_merge.py`); **prompt-shape invariance** and **authority** guardrails (`tests/test_prompt_builders.py` Phase 1 tests).
- **Regression:** **`RP_PACKET_SHADOW_COMPARE=1`** with retrieved / runtime_packets / perception / episodic prompt pytest subset — **green** (no new shadow regressions from this pass).

**Gate:** Phase 0.5 character packet seam remains prerequisite — see Phase 0.5 closure above.

**Future / out of scope (not Phase 1):**

- Optional **headless simulation** burn-in with **`RP_PACKET_SHADOW_COMPARE=1`** (release hygiene; same style as Phase 0.5 validation — not required to call this scoped pass “complete”).
- **Director / Narrator** packet consumers and broader **packaging** read path — separate milestone.
- **Caps / dedup / merge** behavior: **unchanged** in code; existing tests + new snapshots **guard** composition drift.

**Exit criteria (this scoped Phase 1):** **met** — retrieval-lock **documented and test-enforced** without expanding retrieval architecture.

---

# Operational retrieval pilot — real manifest / v3 index (**closed — accepted baseline documented**)

**Status:** Evaluation branch **closed**. The **accepted** operational retrieval baseline is **locked in manifest + compiled artifact**; **template-aware headless** parity is **implemented and validated**; **refined template premise** is **retained** in source templates and index. A **low-tension situational cap** on `scene_template` rows (premise-first trim) was **prototyped, evaluated, and not adopted** — it is **not** in the codebase (reverted); see **Rejected experiments** below.

- **Runbook (current truth):** `data/retrieval/OPERATIONAL_RETRIEVAL_PILOT.md`
- **Manifest:** `data/retrieval/manifests/operational_pilot.json`
- **Compiled artifact:** `data/retrieval/compiled/operational_pilot_v3.json` (regenerate: `python scripts/compile_authored_retrieval_index.py --manifest data/retrieval/manifests/operational_pilot.json --output data/retrieval/compiled/operational_pilot_v3.json --schema-version 3` from `autogen_rp/python`)

### Accepted baseline (operational pilot)

| Lane | Content |
|------|--------|
| **Character** | Minimal **`lore_facts`** (allowlisted per card in manifest) |
| **Template** | **`role_slots`** + **refined `premise`** (mechanics-focused prose; not scene-setup duplication) |
| **Authority** | Retrieval remains **non-authoritative**; bundle-driven; continuity / grounding / binding stay authoritative |

### Completed in this branch

- [x] **Operational A/B matrix** — `scripts/run_operational_pilot_eval_matrix.py` (retrieval OFF vs ON; subprocess env for `RP_RETRIEVED_CONTEXT_INDEX`; ON verification requires `RETRIEVED REFERENCE MATERIAL` + template lines including **`:premise | scene_template]`**).
- [x] **Template-aware headless** — `prepare_headless_session(..., scene_template_id=...)`; scenario JSON **`scene_template_id`** and CLI **`--scene-template-id`**; `tests/test_prepare_headless_scene_template_id.py`.
- [x] **Premise refinement** — `data/scene_templates/arkham_asylum_*.json` premise text + recompiled index (no extra template fields beyond `role_slots` + `premise` for pilot).

### Rejected experiments (not in repo default)

- **Low-tension template row cap / premise-first subcap** — Explored to reduce noise in calm beats; **not clearly beneficial** vs baseline across matrix runs; **reverted** from `retrieved_context_select.py` / `app_turn_prompting.py` so **selector matches accepted baseline** (fixed per-`source_kind` subcaps only).

### Next-step pointer (pilot artifact track)

- **Phase 4A** (below) **completed** — retrieval OFF/ON is **standard** in the simulation + audit workflow; see **SCENARIO_VALIDATION_FRAMEWORK.md** and **AUDIT_DOCUMENTATION.md**.
- **Product / scale:** Broader scenario matrices or token/cost monitoring — **not** “more retrieval tuning” by default; any **new** retrieval architecture work needs an explicit scoped spec.
- **Optional revisit:** Situational template trimming could be re-proposed behind a **flag** if a future phase wants it; keep **manifest + premise** as the stable content contract until then.

---

# Phase 4A — Retrieval workflow operationalization (**complete**)

**Intent:** Treat the **accepted** authored retrieval baseline as a **routine** validation mode (not pilot-only wiring).

**Completed**

- [x] **OFF / ON as standard simulation modes** — `RP_RETRIEVED_CONTEXT_INDEX` is the **only** runtime switch; optional **`--retrieved-context-index`** on `run_scene_simulation_llm.py` (omit flag = leave shell env unchanged; bare flag = empty index / OFF).
- [x] **Template-aware headless** in scenario workflow — `scene_template_id` in scenario JSON / `prepare_headless_session` / CLI `--scene-template-id` (unchanged from pilot closeout; now documented as standard).
- [x] **Audit visibility** — per-turn **`metadata.retrieval_summary`** on character audits; run-level **`retrieval_session`** in **`structured_eval`** and merged into **`_audit_summary.json`** after **headless** simulation; optional index fingerprint.
- [x] **Strict headless check** — retrieval **ON** + non-empty **`scene_template_id`** ⇒ run fails if no turn had a non-empty retrieved bundle.
- [x] **No selector or prompt-structure change** — observability and CLI only; baseline remains **lore_facts** + **role_slots** + **premise**, non-authoritative.

**Docs / tests:** `SCENARIO_VALIDATION_FRAMEWORK.md` (*Authored retrieval*), `AUDIT_DOCUMENTATION.md`, `OPERATIONAL_RETRIEVAL_PILOT.md` (pilot vs standard), `docs/audit-workflows.md`, `tests/test_retrieval_workflow_audit.py`.

**Default next phase:** **Not** retrieval tuning unless a new milestone is opened — prefer other product/validation goals.

---

# Phase 2 — Retrieval (Controlled Introduction) (**complete — authored index only**)

## HARD GATE

- [x] Phase 0 + 0.5 complete

## Implementation (this phase: **authored JSON index**; no graph / vector / transcript mining)

- [x] `RetrievedContextBundle` implemented (`RetrievedItem`, caps, dedup: `source_ref` → text hash → substring)
- [x] Deterministic authored retrieval selection (`retrieved_context_select.py`)
- [x] Relationship retrieval constraints: **relationship-tagged** chunks from other characters only; **≤1 item per other**; lower priority than self/template/setup lane; caps drop cross-character before primary
- [x] Session **opener** excluded from retrieval (no opener items in bundle)
- [x] Bundle integrated through **`RuntimeCharacterPacket.retrieved`**; selection runs **once** per turn in **`app_turn_prompting`** only (`build_runtime_character_packet(..., retrieved=...)` — **no** selector in `runtime_packets`)
- [x] Prompt injection: **after** scene grounding, **before** `CURRENT SCENE STATE` (therefore before recent transcript); **non-authoritative** contract in `format_retrieved_context_for_prompt` / `prompt_builders.build_character_turn_prompt`
- [x] Shadow parity extended: `retrieved_context_section` in live + reconstructed prompt-input bundles (`RP_PACKET_SHADOW_COMPARE`)
- [x] Retrieval logging when bundle non-empty: `rp_app.retrieved_context` (item count, char count, ordered `source_ref` list)
- [x] Env `RP_RETRIEVED_CONTEXT_INDEX`; missing/unset path → **no-op** (prompt shape matches Phase 1 aside from optional empty kwargs default)
- [x] Does **not** affect continuity writes or validation truth; retrieval is assistive only
- [x] Tests: `tests/test_retrieved_context.py`, fixture `tests/fixtures/retrieved_context_index_test.json`

### Explicitly **not** Phase 2 (deferred)

- [ ] Bounded **vector** retrieval into this bundle
- [ ] **Graph** DB / graph-backed retrieval
- [ ] **Transcript** ingestion as retrieval source

**Bounded deterministic episodic recall** is **Phase 3.2** (complete — see below), not Phase 2. Phase 2 remains **authored index only**.

## Evaluation

- [x] Validation completed for Phase 2 scope (see **Phase 2 validation reference** below)
- [ ] Measure usefulness (ongoing / later phases)
- [ ] Monitor token cost at scale (later)

---

## Phase 2 validation reference (closure)

- **Prompt placement correction:** Retrieved context is inserted **immediately after** the scene grounding block and **before** `CURRENT SCENE STATE` (and thus before **RECENT SCENE TRANSCRIPT**). An earlier implementation placed it only adjacent to the transcript section; that was corrected to match the agreed hierarchy.
- **Tests (full tree, no key-presence-only failure):**  
  `pytest tests/ -q -k "not test_deepseek_api_key_exists"` → **green** (e.g. **375 passed**, **25 skipped**, **1 deselected**) with **`DEEPSEEK_API_KEY` unset**.
- **RP-focused subset:** `test_retrieved_context`, `test_runtime_packets`, `test_prompt_builders`, `test_prompt_perception_integration`, `test_offstage_presence`, `test_rp_app_rules` → **green**.
- **Full-suite slowness / apparent hang:** When **`DEEPSEEK_API_KEY` is set**, live DeepSeek / integration / LLM-marked tests run and dominate runtime. **Unrelated** to Phase 2 retrieval.

---

# Phase 3.1 — Authored ingestion expansion (**complete — closure**)

**Scope (authored ingestion only):** manifest-driven compile → **`schema_version` 2** compiled index (**`lore`** lane); deterministic selector; **no** memory, vectors, graph DB, or transcript ingestion.

## Completion checklist

- [x] **Manifest-driven authored compiler** (`authored_index_compile.py`, `compile_authored_index(manifest, output)`)
- [x] **Schema v2 compiled index** (`schema_version` 2, `version`; buckets: `characters`, `templates`, `setup_notes`, **`lore`**)
- [x] **Lore lane** loaded and selected (`world_lore`, template/tag match only)
- [x] **Deterministic selector ordering** updated: template → setup → lore → self (`character_local` only) → relationship
- [x] **Source-kind subcaps** enforced (trim: priority DESC, `source_ref` ASC, keep head / drop from end)
- [x] **Lore truncation at selection time** only (full lore text stored in compiled JSON)
- [x] **Tests:** `tests/test_authored_index_compile.py`, `tests/fixtures/compile_*`, extended `tests/test_retrieved_context.py`
- [x] **Shadow validation:** `RP_PACKET_SHADOW_COMPARE=1` on `test_prompt_perception_integration` — no structured mismatches

### Explicitly **not** Phase 3.1 (still deferred)

- [ ] **Vector** / embedding retrieval
- [ ] **Graph** DB retrieval
- [ ] **Transcript** ingestion

(Episodic / bounded runtime recall → **Phase 3.2**, complete below.)

---

# Phase 3.2 — Bounded episodic memory (**complete — closure**)

**Scope:** Deterministic compile from explicit continuity rows only (`PublicEvent`, `CharacterInterpretation`, `IssueState`, `CanonAnchor` where visibility resolves); **no** LLM in compile/select; **no** continuity writes; merged into the **same** `RetrievedContextBundle` lane as authored items; feature flag **`RP_EPISODIC_MEMORY`**. **Not** vector, graph, or transcript-wide indexing.

## Completion checklist

- [x] **`episodic_memory_compile.py`** — template-only summaries; visibility gating; anchor/event dedup (`canon_impact`)
- [x] **`episodic_memory_cache.py`** — deterministic snapshot key; `session_state` pool cache; `clear_episodic_pool_cache`
- [x] **`episodic_memory_select.py`** — per-character filter from shared pool; episodic-only subcaps
- [x] **`episodic_memory_inputs.py`** — read-only continuity sequences for compile/cache
- [x] **`episodic_memory_prompt.py`** — `is_episodic_memory_enabled()` (flag)
- [x] **`retrieved_context_select.py`** — `merge_retrieved_context_with_episodic`; single global cap on merged list; **authored wins** on priority tie; stable survivor order
- [x] **`app_turn_prompting.py`** — single path: flag on → merge; flag off → authored-only (no cache touch)
- [x] Packet shadow: merged retrieval only in `retrieved` / `retrieved_context_section` (no separate episodic prompt block)
- [x] **Tests:** `test_episodic_memory_*.py`, `test_retrieved_context_merge.py`, `test_app_turn_prompting_episodic.py`; extended retrieval/packet tests

### Follow-up (hardening — **not** blockers)

- [ ] Run **full** `pytest tests/` to completion in CI or locally when convenient (optional; some environments hit long-running LLM/deep-sim tests)
- [ ] Optional: explicit **continuity no-mutation** unit test around prompt assembly + episodic path

### Explicitly **not** Phase 3.2 (still deferred)

- [ ] **Vector** / embedding retrieval for memory
- [ ] **Graph** schema / graph-backed memory
- [ ] **Transcript-wide** memory indexing or corpus ingestion

---

## Phase 3.2 validation reference (closure)

- **Flag-off regression:** With `RP_EPISODIC_MEMORY` unset/false, `merge_retrieved_context_with_episodic` is not used; prompts match authored-only path (`test_episodic_disabled_no_episodic_line_in_retrieved`, plus `test_prompt_perception_integration`, `test_retrieved_context`, `test_runtime_packets`, `test_prompt_builders`).
- **Flag-on visibility & merge:** Eligible character sees `episodic:*` lines inside `RETRIEVED REFERENCE MATERIAL`; non-`known_by` character does not (`test_app_turn_prompting_episodic`). Merge/cap/tie: `test_retrieved_context_merge`.
- **Shadow parity:** `RP_PACKET_SHADOW_COMPARE=1` + targeted suite (e.g. episodic + retrieval + perception + builders + packets) → **green** (e.g. **67 passed** in closure run); no structured bundle mismatches.
- **Targeted suite counts (example closure run):** **67** tests (episodic + merge + retrieved + runtime_packets + perception + builders + `test_episodic_memory_*`); additional regression cluster e.g. **84** (`test_turn_runner_updates`, `test_continuity_manager`, `test_scene_grounding`, `test_offstage_presence`).
- **Full-suite completion:** optional hardening (see follow-up above); not required for Phase 3.2 sign-off.

---

## Phase 3.1 validation reference (closure)

- **Targeted pytest:**  
  `cd autogen_rp/python && pytest tests/test_authored_index_compile.py tests/test_retrieved_context.py tests/test_runtime_packets.py tests/test_prompt_perception_integration.py -q` → **green** (e.g. **26+ passed** in closure run).
- **Shadow parity:**  
  `RP_PACKET_SHADOW_COMPARE=1` + `pytest tests/test_prompt_perception_integration.py -q` → **green**, no `rp_app.packet_shadow` mismatch warnings.
- **Example compile command** (with `cwd` = `autogen_rp/python`):

  `python scripts/compile_authored_retrieval_index.py --manifest tests/fixtures/compile_sample/manifest.json --output path/to/compiled_index.json`  
  Optional **schema v3** (canonical fields + legacy projection): add `--schema-version 3` (default remains **2**).  
  Manifest entry type **`initial_message`**: JSON file with required **`text`**; optional **`template_id`** on the manifest row for `template:…` relevance tags; compiled rows use **`source_kind` `setup_note`** (retrieval-compatible). Template field **`initial_messages`** (pointer list) is allowlistable but compiles to **zero rows** (`emit_zero_chunks`).  
  **Draft production-shaped manifest** (subset of real paths): `data/retrieval/authored_manifest.example.json` — copy and extend for `RP_RETRIEVED_CONTEXT_INDEX` builds; paths are relative to that file’s directory.

- **Example selection result** (`tests/fixtures/retrieved_context_index_test.json`, `char_name=A`, `scene_template_id=tpl1`, relationship focus `B`, cast `B`):  
  `source_ref` order:  
  `tpl1:atmosphere` → `setup:tpl1` → `lore:fixture:long_trunc` → `A:dup_hash` → `A:self` → `B:rel`

---

# Phase 3.3 — Quality Assessment & Tuning

**Goal:** Improve RP quality on top of the now-stable runtime without changing core architecture or introducing new subsystems.

**Selector-quality & turn-selection stability — CLOSED (complete).** This track is **not reopened** unless a concrete regression appears. Closure reference: `python/rp_app/SELECTOR_QUALITY_PHASE.md`.

### Closure summary — selector-quality

- **Stability:** Core scenario runs showed stable progression (no retries / failed progression in closure matrix); turn selection treated as stable for this gate.
- **Obligation precedence (hard rule):** When `responder_obligation.active` is true, `action_responsibility` must not compete (enforced in `app_turn_director.py`).
- **Diagnostics:** Contradictory validation lines removed; structured `validated_pick` / `final_pick` and effective semantic assessment in audits.
- **Semantic alignment:** Improved via reconciliation + prompts; **non-zero semantic disagreement remains expected and acceptable** — validation stays **advisory**; **zero mismatch is not a target.**

### Optional hardening (non-blocking — does not reopen selector-quality)

- Additional headless evaluation reruns beyond the closure matrix
- Lower-pressure conversational scenario in §F (still unchecked below)
- Character prompt / narrator polish (§B, §C, §E.2, §E.3)
- Fairness re-check only if concrete selection misses appear in production-like runs

---

## A. Scope — Scene movement

- [x] Evaluate progression naturalness (sufficient for selector-quality closure; broader passes optional)
- [x] Evaluate stall / plateau behavior (same)
- [x] Evaluate handoff quality (same)
- [x] Evaluate continuation / Director / override / fairness interaction (same)

## B. Scope — Character performance

_optional hardening — see Phase 3.3 optional list above_

- [ ] Evaluate voice vitality
- [ ] Evaluate emotional sharpness
- [ ] Evaluate instruction drag / prompt crowding
- [ ] Evaluate social plausibility

## C. Scope — Scene readability

_optional hardening — see Phase 3.3 optional list above_

- [ ] Evaluate narrator flow
- [ ] Evaluate turn-to-turn readability
- [ ] Evaluate procedural vs natural prose feel

## D. Current baseline entering this phase

- [x] Architecture-quality harness implemented
- [x] A1 / B / C comparison variants implemented
- [x] No clear evidence of over-layering from architecture runs
- [x] `resolve_progression_override_actor` identified as only repeatable structural-effect layer
- [x] Turn-selection v1 policy refinement accepted:
  - [x] C2 continuation suppression when last spotlight matches
  - [x] Explicit P1 vs P3/P4 guards
  - [x] Validation + attribution alignment
- [x] P3 med-suppressed refinement implemented and accepted as working baseline for further tuning
- [x] Continuation investigation completed; continuation appears mostly inert in standard flow and is deferred as a primary tuning target
- [x] Director selection quality refinement (**selector-quality track — complete**)
- [ ] Character prompt quality refinement _(optional hardening)_
- [ ] Narrator readability refinement _(optional hardening)_

## E. Tuning order

### 1. Selection / handoff

- [x] Validate current selection hierarchy quality in practice
- [x] Monitor `continuation_override_skipped_c2` frequency and effect
- [x] Identify remaining same-speaker stacking issues
- [x] Identify awkward spotlight jumps
- [x] Refine override policy based on repeated quality evidence
- [x] Implement med-suppressed P3 refinement (`low -> high` retained; `med -> high` suppressed)
- [x] Compare old baseline vs `C` vs med-suppressed P3 behavior
- [x] Refine Director primary selection quality for immediate responder correctness (**selector-quality — complete**: obligation vs action-responsibility boundary, diagnostic integrity)
- [x] Re-evaluate fairness only if Director refinement still leaves visible selection-quality misses _(not required at closure; optional if concrete misses appear — see optional hardening)_

### 2. Character prompt quality

_optional hardening_

- [ ] Review prompt density / instruction drag
- [ ] Evaluate ordering and emphasis of prompt sections
- [ ] Confirm character voice remains distinct and sharp
- [ ] Confirm no regression in:
  - [ ] binding constraints
  - [ ] evidence / authority discipline
  - [ ] continuity truth

### 3. Narrator readability

_optional hardening_

- [ ] Review transition smoothness
- [ ] Review procedural vs natural prose feel
- [ ] Confirm narration preserves action clarity without flattening

## F. Validation method

- [x] Use fixed high-signal scenarios:
  - [x] `conflict_3char`
  - [x] `arkham_multi_character_stress`
  - [ ] one lower-pressure conversational scenario
  - [x] one long-session scenario

- [x] Track structural metrics where useful:
  - [x] override count
  - [x] hard-route count
  - [x] fairness count
  - [x] attribution chain distribution

- [x] Pair with qualitative judgment:
  - [x] flow / handoff
  - [x] progression naturalness
  - [x] voice vitality
  - [x] instruction drag
  - [x] pressure integrity
  - [x] scene readability

## G. Constraints

- [x] No threshold tuning without repeated evidence
- [x] No new subsystems
- [x] No weakening of:
  - [x] continuity authority
  - [x] grounding / binding
  - [x] evidence / authority discipline

## H. Exit criteria

- [x] No obvious handoff / override / continuation instability in core scenarios (**selector-quality closure**)
- [ ] Character prompts feel sharp without instruction drag regressions _(optional hardening — not blocking progression)_
- [ ] Narration remains readable and non-procedural _(optional hardening — not blocking progression)_
- [x] Runtime quality is sufficient to defer further **selector / turn-selection** tuning until model change, Phase 4 (vector/graph) ingestion, or a concrete regression (closure met)

---

# Phase 3.4 — Canonical Knowledge Shape & Static Ingestion

**Purpose:** Define the **canonical runtime knowledge model** from **system function**, not from current file layout. Reshape **static authored sources** (character cards, scenarios, initial/setup materials, lore) so they **compile deterministically** into that model and **conform to the existing packet / retrieval contract** when a compiled index is wired via **`RP_RETRIEVED_CONTEXT_INDEX`**. Preserve **authority boundaries** (continuity, grounding, episodic retrieval remain distinct). This work is **pre-packaging**: it produces **offline artifacts**; it does **not** replace the packet seam or merge packaging logic.

**Scope boundary (non-negotiable):** Canonical compile **does not change runtime behavior**: `retrieved_context_select` still reads only **legacy projection** fields on each chunk; v2 and v3 index files behave the same at runtime. **Continuity** remains authoritative for in-scene truth; compiled rows are **non-authoritative** assistive context. **Authoritative spec:** [CANONICAL_KNOWLEDGE_MODEL.md](../../CANONICAL_KNOWLEDGE_MODEL.md).

**Milestone — compiler expansion & validation (complete):** Contract doc + **schema_version 3** compile path (canonical fields + legacy projection), **adapter registry**, **decomposition strategies**, real-source adapter coverage, **`initial_message`** manifest type (`source_kind` **`setup_note`** for retrieval compatibility), tests/fixtures (`compile_sample`, `compile_realistic`, golden v3), example manifest `data/retrieval/authored_manifest.example.json`. **Default CLI remains `--schema-version 2`**.

**Operational follow-ups (not blocking the milestone):**

- Maintain / extend a **production manifest** (copy from `authored_manifest.example.json`) and point **`RP_RETRIEVED_CONTEXT_INDEX`** at a rebuilt index when ready.
- Optional: CI job that compiles with **`--schema-version 3`** and fails on unexpected diff; later, flip CLI default to **3** when operators standardize on v3 artifacts.
- Remaining **high-fallback** paths if allowlisted without new rows: e.g. **`progression_profile`**, **`sleeping_surface_slots`** on templates (see adapter registry).

## Constraints (non-negotiable for this phase)

- No vector DB
- No graph DB
- No transcript-wide ingestion
- No semantic retrieval tuning
- No LLM-based selection logic
- Do not collapse advisory knowledge into authoritative truth (continuity / grounding / binding discipline unchanged)
- **No mandatory runtime retrieval / merge / packet API changes** for this milestone

## Checklist

- [x] Canonical **knowledge object** contract ([CANONICAL_KNOWLEDGE_MODEL.md](../../CANONICAL_KNOWLEDGE_MODEL.md)) + implementation snapshot
- [x] **Knowledge types**, **authority classes**, **visibility**, **authority ceiling table**, **dense-source cap** (spec + compile enforcement for v3)
- [x] **`subject_scope`** resolution rules (no inference) in compile path
- [x] **Adapter mapping** for current real character / template / setup / lore / **initial_message** shapes (`canonical_compile_adapters.py`)
- [x] **Deterministic compile** (`authored_index_compile.py`): **schema_version** 2 and 3; strict fallback; tests + goldens
- [x] **Document** runtime alignment: legacy projection only; no retrieval integration change
- [ ] **Source document** edits to cards/templates only where authors choose stricter allowlists or new fields need adapters
- [ ] **Packet / packaging** consumption of canonical fields as first-class (deferred — next seam work)
- [x] Bridge to Phase 4 documented in canonical spec (§11–§12)

---

# Phase 4 — Advanced Retrieval & Storage (vector / graph — still deferred)

**Note:** Executes **after** Phase 3.4 canonical shape and static ingestion are in place; graph/vector implement storage and retrieval **against** that contract, not instead of it.

## HARD GATE

- Retrieval proven
- Packet interface stable
- Canonical knowledge shape & static ingestion path established (Phase 3.4)

## Steps

- [ ] Extract structured knowledge from sources
- [ ] Store in:
  - [ ] graph DB
  - [ ] vector DB

- [ ] Compile:
  - [ ] character profiles
  - [ ] relationships

- [ ] Feed into packet builders

---

# Core Principles

## Data Separation Principle

- Scene = situation / pressure / constraints
- Character = behavior / goals / voice

Static inputs remain stable:
- scene templates
- character cards
- initial messages

Packets:
- normalize inputs
- remove duplication
- prepare for retrieval

Packets do NOT change behavior.

---

## General Principles

- Fix correct layer, not symptoms
- Prefer structure over prompt tweaks
- Continuity is authoritative truth
- Retrieval is assistive only
- Maintain determinism where possible
- Avoid premature complexity

---

# Summary

**Completed through Phase 3.2** (packet seam + authored retrieval + manifest compile + lore lane + subcaps + **bounded deterministic episodic** merged retrieved lane). **Phase 3.3 selector-quality / turn-selection stability** is **closed** (see Phase 3.3 closure above and `python/rp_app/SELECTOR_QUALITY_PHASE.md`).

**Phase 0 prompt-layer stability** (section **H**): **BINDING CONSTRAINTS** + **EVIDENCE & AUTHORITY DISCIPLINE** in `prompt_builders.py` / `scene_grounding.py` — **complete** for prompt-only scope (see **H** above).

**Phase 0 turn selection** (section **I**): v1 continuation C2, explicit P1 vs P3/P4 guards, aligned `validate_turn_selection_decision`, and `continuation_override_skipped_c2` attribution — **complete** (accepted baseline refinement).

**Phase 3.3 — selector-quality & turn-selection stability:** **complete (closed).** Hard obligation-vs-action-responsibility rule, diagnostic integrity, and advisory semantic alignment are documented in `python/rp_app/SELECTOR_QUALITY_PHASE.md`. Non-blocking optional hardening (character prompts, narrator, extra scenarios) remains listed under Phase 3.3 above; **does not reopen** the selector track unless a concrete regression appears.

**Phase 3.4 — canonical compile expansion:** **closed** for the scoped milestone (offline v3 compile + adapters + tests + example manifest; runtime unchanged).

**Phase 0.5 — packet seam (character prompt path):** **complete and validated** — single assembly (**`CharacterPromptInputAssembly`**), packet construction from assembly, reconstruction + shadow compare, parity corpus tests, simulation runs with shadow on (no mismatches). Shadow logs to stderr only; not yet in audit artifacts (see Phase 0.5 section).

**Phase 1 — scoped retrieval-lock / packet-aligned validation:** **complete** — no seam bypass; **bundle-driven** retrieval invariant; **pure derived** `retrieved_context_section`; snapshot + prompt-shape + authority tests; shadow pytest subset green. **Did not** add selector features, lanes, graph/vector, or Director retrieval. See Phase 1 section.

**Next broader packaging focus:** extend packet consumers **beyond** the character **`build_character_turn_prompt`** seam (Director/Narrator, etc.) per [PACKET_CONTRACTS.md](../../PACKET_CONTRACTS.md). Canonical compile output remains an **upstream artifact**, not a substitute for packets.

Later (deferred):

→ **Phase 4 — Advanced Retrieval & Storage (vector / graph)** — hard gate: retrieval proven, packet interface stable, Phase 3.4 **canonical compile** milestone complete

Optional (non-blocking):

→ **Phase 3.3 optional hardening** — character/narrator polish, extra scenario coverage, ad-hoc reruns

Do not treat Phase 3.2 as completion of **vector**, **graph**, or **transcript-wide** memory. Episodic here is **continuity-backed, capped, non-authoritative** retrieval only.