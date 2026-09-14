# Issue #200 — Investigation & Proposal Record (2026-09-14)

**Issue:** [#200](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/200)  
**Session:** `hg-session-f883b2dd-93cc-4914-bcff-8c862589b311`  
**Round / commit:** `hg-round-0ad0479e-475a-4e0b-b489-9aaea15f4be8` / `hg-commit-d726ca4e-5ba9-478c-b520-95157f325361`  
**Repository HEAD (investigation):** `bf1ac61f85262afa5ac9f64232627b328aec7477`  
**Session SHA:** `09f39295cfc6d6aa62367c65d9e09cdbc89b24b0`  
**Assigned / effective workflow weight:** `standard` / `full`  
**Disposition:** investigation-only; no remediation implemented

## Executive summary

PVR correctly captured foot-wiping and shoe-removal observables. Director received the full committed Player post and concluded protocol compliance in free-text `reason`. Character consumption failed because **viewer-specific perceptual projection** delivered only the speech unit to `user_turn_trigger` and `recent_scene_transcript`; observable_event units were withheld (`barrier_blocks_visual` / `insufficient_entitlement_evidence`). Competing stale `scene_pressures`, #193 forward-only R16 steering, and advisory-only Director handoff amplified the error. Character and Narrator semantic evaluators passed; no invariant rejects regressing established Player completions.

**Earliest demonstrated divergence:** Character perceptual visibility assembly for Ayame on entry `hg-hist-dd1cf009-7656-4438-bce5-5bb19f10a75b` — after PVR persistence, before Character move inference.

**Recommended proposal:** Small combination — (1) correct present-scope threshold observable projection / inventory surfacing for co-present entry beats; (2) extend semantic evaluator with inverse completion regression check reusing `player_fact:user_post` / decomposition authority (generalize #193 bidirectionally without new LLM passes).

## Evidence anchors

| Artifact | ID |
|---|---|
| PVR decomposition | `5f660df6-8160-41fb-8a17-c38df7b8eb21` |
| Director decision | `0e72a022-30f9-4cd6-8a31-763b14a95907` |
| Character move | `bed8a11a-32cc-45bd-94df-c0d3a0fddfbd` |
| Character semantic eval | `2f88bcc0-5d1f-4e6c-a41f-e52d016b90a8` |
| Narrator semantic QA | `f7679506-2399-4674-8d33-c1e70b0e1b90` |
| User post entry | `hg-hist-dd1cf009-7656-4438-bce5-5bb19f10a75b` |

## Deterministic reproduction (local)

```python
# v2 on PYTHONPATH; session rp_history entry hg-hist-dd1cf009...
# Ayame viewer assembly → included ['u2'] only; u1/u3 excluded
```

Observable units u1 (`wiping feet and stepping inside`) and u3 (`toed off shoes`) excluded; speech u2 (`Thank you for seeing me`) projected via `non_spatial_recipient_contract`.

---

## Governance challenge refinement (2026-09-14, phase 2)

Governance accepted phase-1 causal reconstruction but **did not authorize** the original B + D remediation (perception widening + bidirectional semantic eval as primary fix). Phase 2 investigated the world-truth vs character-epistemics distinction.

### Refinement executive summary

The F06 failure is **not** best explained as a doorway-perception bug. Threshold entitlement behaved as designed (#155/#199): closed opaque portal across `exterior_threshold` ↔ `interior_entry` withholds visual observables. The more central defects are:

1. **Stale Librarian `semantic_unmet_condition`** projected into Character manifest with objective wording (“compliance has not yet occurred”) after tier-1 Player post established wipe/entry/shoes-off — overlay fingerprint still matched at manifest time because issue material had not yet changed (issues update on Character commits only).
2. **No authoritative resulting-state promotion** from Player turn (`record_user_turn` persists PVR/history only; zones/portals/compliance remain template-seeded; no continuity issue refresh on Player turns).
3. **Manifest incoherence**: suggestive Director context said compliance occurred; derived scene pressure said it had not; perception-filtered trigger contained speech only.
4. **Forward-only R16** (#193) in generation steering and semantic eval; no inverse regression guard; eval passed (`overall_result: pass`, empty findings).

**Revised recommendation:** Option E — **B (stale-pressure correction) + narrow D (objective regression guard)**. **Do not** approve original perception-widening B for this replay. Defer generalized world-state promotion to #201.

### Doorway entitlement (phase 2)

| Question | Determination |
|---|---|
| Could Ayame see wipe/step/shoes at manifest time? | **No** — zones differ, portal `closed` + `opaque` |
| Portal/zone state correct for model? | **Yes** for saved `perceptual_scene_context` (template-seeded, unchanged) |
| Gate 2 basis | `barrier_blocks_visual` / `insufficient_entitlement_evidence` — **by design** |
| Would widening portal rules fix replay without leaking hidden actions? | **No** — would generalize incorrectly |
| Separate note | Turn-1 Ayame narratively opened door but `scene_state_updates` empty; portal stayed `closed` — world-state sync gap (#201), not F06 perception bug |

### Authoritative resulting-state trace (Player turn 2)

| Action | Tier-1 established? | Committed continuity? | Scene grounding? | Zone/portal? | Protocol/compliance state? |
|---|---|---|---|---|---|
| Wipe feet | Yes (`rp_history`, PVR u1) | No public event | No | No | No |
| Step inside | Yes (PVR u1) | No | No | No (Kizzie still `exterior_threshold`) | No |
| Thank Ayame | Yes (PVR u2, projected speech) | No | No | No | No |
| Remove/position shoes | Yes (PVR u3) | No | No | No | No |

`continuity_issue_lifecycle.update_issues()` runs on **Character commits only**. No representation states “mat/shoe requirement satisfied.”

### `scene_pressures` classification

- **Creator:** Librarian B2 `issue_tension_pressure` post-commit (`continuity_librarian_issue_pressure.py`), packaged by `project_character_scene_pressures` / `project_scene_pressures_digest`.
- **Phase:** Turn-1 Character commit overlay; projected unchanged at turn-2 Character manifest assembly.
- **Authority:** `derived` / `librarian_overlay` (labeled in JSON) but **objective phrasing** in `semantic_unmet_condition`.
- **Invalidation:** Fingerprint match on issue status/kind/last_change/participants; Player turn does not invalidate; newer overlay only on new Librarian proposal.
- **Classification:** **Incorrectly stale derived state** + **semantically ambiguous** (objective language for derived overlay).

### Revised causal ranking

| Contributor | Classification |
|---|---|
| PVR extraction | Working correctly |
| Perception entitlement (doorway) | Working correctly |
| World-state promotion (zones, portal, compliance) | **Root cause** (missing handoff) |
| Stale `scene_pressures` overlay | **Root cause** (manifest contradiction) |
| Director handoff (advisory-only) | Contributing |
| Character manifest authority mix | Contributing |
| Character generation | Contributing (rational given inputs) |
| Semantic validation | Contributing (no inverse rule; pass on command-style output) |

### Revised remediation (not implemented)

| Option | Verdict |
|---|---|
| A — Perception correction | **Reject** for #200 F06 (unless separate portal-sync bug filed under #201) |
| B — Stale-pressure/state correction | **Primary** — invalidate/supersede overlay when tier-1 Player authority contradicts; clarify non-objective framing |
| C — Existing authority consumption | **Insufficient today**; gap documented for #201 |
| D — Bidirectional semantic eval | **Secondary/narrow** — objective regression only; preserve ignorance commands and deception |
| E — Minimal combination | **Recommended** — B + narrow D + manifest precedence guidance |

**Status:** Ready for Governance agreement on revised proposal. No implementation in this cycle.
