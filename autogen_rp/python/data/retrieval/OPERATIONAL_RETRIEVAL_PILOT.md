# Operational retrieval pilot — real manifest → v3 index

**Status:** **Closed.** This document is the **runbook and artifact map** for the **accepted operational baseline**. The pilot used a **fixed** cast, **two** Arkham templates, and **`schema_version` 3** index wiring via **`RP_RETRIEVED_CONTEXT_INDEX`**.

**Purpose (historical):** Evaluate whether current retrieval is **useful, neutral, or harmful** before any architecture expansion. Outcome: baseline **accepted** for product use; **template-aware headless** validated; one **selector experiment** was **evaluated and not adopted** (see **Rejected experiments**).

**Authority (unchanged):** continuity → grounding → binding → **retrieved (non-authoritative)**. `RetrievedContextBundle` remains the behavioral source; `retrieved_context_section` is purely derived.

---

## Accepted content baseline (manifest + index)

| Lane | What is retrieved |
|------|-------------------|
| **Character** | Minimal **`lore_facts`** only (per-card **`allowlist_keys`** in manifest) |
| **Template** | **`role_slots`** + **`premise`** (refined, mechanics-focused premise text in source templates; recompile after template edits) |

**Manifest:** `data/retrieval/manifests/operational_pilot.json`  
**Compiled index:** `data/retrieval/compiled/operational_pilot_v3.json`

---

## Locked scope for evaluation (do not swap mid-matrix)

| Slot | Choice | Notes |
|------|--------|--------|
| **Character 1** | `Harley_Quinn` | Card file `harley_quinn.json`; index key = `make_agent_identifier("Harley Quinn")` |
| **Character 2** | `Poison_Ivy` | Card file `poison_ivy.json`; index key = `make_agent_identifier("Poison Ivy")` |
| **Character 3** | `Magpie` | Card file `magpie.json`; index key = `Magpie` |
| **Template A (dyadic / intake tension)** | `arkham_asylum_cell_intake` | `data/scene_templates/arkham_asylum_cell_intake.json` |
| **Template B (3-way conflict)** | `arkham_asylum_cafeteria_harley_ivy_conflict` | `data/scene_templates/arkham_asylum_cafeteria_harley_ivy_conflict.json` |

Changing characters or templates **during** a comparison matrix invalidates A/B baselines.

---

## Artifacts

| Artifact | Path |
|----------|------|
| **Manifest** | `data/retrieval/manifests/operational_pilot.json` |
| **Compiled index (v3)** | `data/retrieval/compiled/operational_pilot_v3.json` |

**Recompile** (from `autogen_rp/python`):

```text
python scripts/compile_authored_retrieval_index.py --manifest data/retrieval/manifests/operational_pilot.json --output data/retrieval/compiled/operational_pilot_v3.json --schema-version 3
```

Runtime reads **legacy chunk fields** from the file; `schema_version` **3** adds canonical fields **alongside** those projections (Phase 3.4 contract) without changing selector behavior beyond the **accepted** caps and merge rules in `retrieved_context_select.py`.

---

## Runtime wiring

### Retrieval OFF vs ON

| Mode | Environment |
|------|-------------|
| **OFF (A / baseline)** | Unset or empty **`RP_RETRIEVED_CONTEXT_INDEX`** |
| **ON (B)** | Set **`RP_RETRIEVED_CONTEXT_INDEX`** to the path of **`operational_pilot_v3.json`** (absolute or cwd-relative from the process that runs the app / headless runner) |

**Test fixtures** that pass an explicit path to `load_authored_retrieval_index` are unchanged; the env applies to **integrated** runs only.

Optional: **`RP_PACKET_SHADOW_COMPARE=1`** during runs to catch packet/prompt-input drift (no behavior change).

### Template-aware headless (parity with Streamlit)

Headless preparation **does** set **`scene_template_id`** when provided:

- **`prepare_headless_session(..., scene_template_id=...)`**
- Scenario JSON field **`scene_template_id`**
- CLI **`--scene-template-id`** on `scripts/run_scene_simulation_llm.py`

Without a template id, template rows from the index are **not** selected (expected). With a template id matching the manifest’s `scene_template` sources, **`role_slots`** and **`premise`** appear when retrieval is ON.

### How to verify retrieval is actually active (ON)

1. Confirm **`RP_RETRIEVED_CONTEXT_INDEX`** points at the intended **`operational_pilot_v3.json`** in the **same** shell / subprocess as the run (matrix script sets this for ON legs).
2. In saved prompts (e.g. character `*_full.json` audit artifacts), expect:
   - A **`RETRIEVED REFERENCE MATERIAL`** (or equivalent) block from `retrieved_context_section`.
   - For template ON runs, lines tagged **`scene_template`** including **`:premise | scene_template]`** (and **`role_slots`** as configured).

Log channel **`rp_app.retrieved_context`** should show item counts and `source_ref` lists when the bundle is non-empty.

---

## Rejected experiments (not the default baseline)

**Low-tension situational cap on `scene_template` rows (premise-first trim)** was prototyped to reduce template noise in calm beats. It was **evaluated** across the operational matrix and judged **not clearly beneficial enough** to adopt as default. The experiment is **reverted** from the codebase; the **accepted** selector uses **fixed per-`source_kind` subcaps** only (see `retrieved_context_select.py`).

---

## Scenarios (evaluation set)

Use the **locked** cast and templates only.

| ID | Scenario | Template | Cast / roles (suggested) | What to observe |
|----|----------|----------|---------------------------|-----------------|
| **S1** | 2-character emotional loop | **A** `arkham_asylum_cell_intake` | e.g. `harley_quinn` as **cell_anchor**, `magpie` as **new_arrival** | Voice/goals in retrieved vs noise; duplication vs grounding |
| **S2** | 3-character conflict | **B** `arkham_asylum_cafeteria_harley_ivy_conflict` | `harley_quinn` **instigator**, `poison_ivy` **possessive_counterforce**, `magpie` **witness_or_intervenor** | Cross-character pressure; caps; ordering (fixed in code) |
| **S3** | Grounding / binding | **A** or **B** (pick one run per template) | After continuity promotes settled facts / binding | Retrieved must **not** override grounding; check **duplication** of same facts |
| **S4** (optional) | Episodic merge | Same as S1 or S2 | Enable **`RP_EPISODIC_MEMORY=1`** | Redundancy between episodic lines and authored chunks; global cap behavior |

**Automation:** `scripts/run_operational_pilot_eval_matrix.py` runs the A/B matrix with subprocess env for ON/OFF and optional `--scene-template-id` alignment checks.

---

## Required A/B protocol

For **each** scenario (S1–S3, and S4 if run):

1. **Run A — retrieval OFF:** `RP_RETRIEVED_CONTEXT_INDEX` unset. Record prompts (audit) and qualitative behavior.
2. **Run B — retrieval ON:** same manifest, same template, same role assignment, **same seed** if the runner supports it. Record the same artifacts.

**Evaluation must compare A vs B** for:

- relevance and noise in the retrieved block (B only for block content; compare overall reply quality A vs B),
- whether behavior **meaningfully** changes vs baseline,
- duplication issues (below).

**Stability gate (mandatory):** After the **first** full pilot run (all required scenarios once), perform a **second** pass with **no manifest or allowlist changes** — repeat the same A/B matrix. Outputs should be **reproducible** modulo LLM stochasticity; large unexplained drift warrants checking env paths, index file, and audit parity before editing content.

---

## Valid outcomes (no bias toward “success”)

Any of these is an **honest** result for this phase:

- Retrieval **improves** consistency, color, or goal alignment vs baseline.
- Retrieval is **neutral** (no meaningful change).
- Retrieval **degrades** quality, adds confusion, or encourages wrong emphases.

**Pilot iteration** (now complete for this branch) was limited to **manifest content** and **allowlist_keys** / optional **`relationship_keys`** tuning — not ad-hoc selector experiments without a new spec.

---

## Duplication checks (explicit)

When reviewing prompts for run **B**, check for:

1. **Grounding fact repeated in retrieved** — same situational fact appears in scene grounding (or binding) and again in the non-authoritative retrieved block.
2. **Relationship / identity duplication** — same relationship or identity beat appears in **identity/continuity-adjacent** sections and again in retrieved (including cross-character snippets if present).
3. **Same sentence twice** — near-verbatim duplicate across sections (normalize whitespace mentally).

Document instances per scenario.

---

## Hard fail condition

**Fail the pilot** (stop and fix **content** or document a blocker before system work) if:

- Retrieved assistive text **correlates with** the model **contradicting** promoted **grounding** or **continuity** truth (e.g. denies a settled fact, wrong location, wrong binding).

This is a **guardrail**; it does not require a new code path — tighten allowlists, shorten template premise in retrieval, or remove conflicting chunks via manifest edits.

---

## Light instrumentation

- Saved **full prompts** from existing audit workflow.
- Log lines from **`rp_app.retrieved_context`** (item count, chars, `source_ref` list).
- Optional: character length of `retrieved_context_section`; compare ON vs OFF.

---

## Suggested sequencing

1. Compile index (command above); confirm `load_authored_retrieval_index` loads (schema_version 3).
2. Run **S1** A/B, then **S2** A/B, then **S3** A/B (optional **S4**).
3. **Repeat entire matrix once** with **no** manifest/index content changes (stability).
4. Tabulate outcomes + duplication notes + hard-fail check.
5. Only then iterate manifest / allowlists and **recompile** (for future content work).

---

## Reference

- Example manifest: `data/retrieval/authored_manifest.example.json`
- Compiler: `rp_app/authored_index_compile.py`
- Loader / selector: `rp_app/retrieved_context_select.py` — `load_authored_retrieval_index`, `select_retrieved_context_bundle`
- Closeout / roadmap pointer: `RP_SETUP_TODO.md` (Operational retrieval pilot section)
- Canonical contract: repo root `CANONICAL_KNOWLEDGE_MODEL.md`
