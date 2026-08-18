# V2 Continuation Override and Forced-Speaker — Investigation Report

**Status:** Investigation complete (design only; implementation not authorized)  
**Date:** 2026-08-18  
**Architecture anchor:** `2ee410321f19e57c4579821ce590f701ccf2eedf`  
**Presence/eligibility anchor:** `7738f00`  
**Investigation HEAD:** `7738f00`

---

## 1. Activation state

| Field | Value |
|-------|-------|
| Repository | `KizzieFae/Holy-Grail-RP-DeepSeek-Harness` |
| Branch | `main` |
| HEAD | `7738f00` |
| `origin/main` | `7738f00` |
| Workflow | assigned standard, effective **full** |
| Pre-investigation validation | 23 Python + 20 Node V2 tests green |

---

## 2. V1 continuation/forced-speaker behavior (verified)

### Forced speaker

| Aspect | V1 behavior |
|--------|-------------|
| **Sources** | (1) `detect_forced_speaker` on user message text (`app_message_processing.py`); (2) harness schedule `make_forced_speaker_from_actor_targeted_schedule` (`user_trigger_schedule.py`) |
| **State** | `pending_forced_speaker`, `forced_speaker_consumed` in Streamlit `session_state` |
| **Lifecycle** | Set before turn loop; consumed on first application; cleared after `run_character_turns` completes |
| **Application** | `choose_next_actor` (`app_turn_director.py` lines 129–180): **hard bypass** — returns immediately without Director LLM call |
| **Priority** | Highest (beats continuation override and Director) |
| **Constraints** | Actor must be in `available_actors` (present, not offstage, not already used this round) |
| **Harness exception** | `ensure_forced_probe_actor_present` can re-enter offstage probe actors (test/validation only) |
| **Validation** | `validate_turn_selection_decision` requires Director pick to match if forced speaker pending and in pool |
| **Fallback exemption** | Skipped when `source == "fallback"` or `is_fallback` |

**Tests:** `test_direct_address_forced_speaker_overrides_everything`, `test_phase5_turn_selection_preemption_forced_speaker_mismatch`, `test_process_user_message_smoke_records_user_turn_and_saves`

### Continuation override

| Aspect | V1 behavior |
|--------|-------------|
| **Source** | `resolve_continuation_override_actor` (`orchestration_continuation.py`) — pure function over orchestration + continuity metadata |
| **State** | Not persisted separately; recomputed each pre-turn from `recent_structured_moves`, `spotlight_history`, `turn_metadata_by_index` |
| **Conditions (all required)** | Last move speaker present in eligible participants; speaker used **exactly once** this round; last spotlight matches speaker; goal/tactic motivation present; no superseding turn tags (`exit`, `agreement`, `refusal`, `arrival`, etc.); no other **present unheard** actors (offstage unheard does not suppress) |
| **Application** | `choose_next_actor` lines 182–245: **hard bypass** when continuation actor ∈ `available_actors` and C2 skip does not apply |
| **C2 skip** | If last spotlight == continuation actor, skip hard route; Director runs without continuation preemption |
| **Priority** | Below forced speaker; above Director |
| **Constraints** | Must be in `available_actors`; **cannot bypass used-actor restriction** (`test_turn_runner_continuation_override`) |
| **Validation** | `validate_turn_selection_decision` requires Director pick to match continuation actor when in pool (unless C2 skip or fallback) |
| **Director prompt** | `continuation_override_actor` passed to `build_director_prompt_payload` as advisory context |

**Tests:** `test_continuation_override_dominates_over_director_and_progression`, `test_continuation_override_c2_skips_when_last_spotlight_matches`, `test_resolve_continuation_override_suppressed_while_other_present_unheard`, `test_resolve_continuation_override_not_suppressed_when_only_offstage_unheard`, `test_turn_runner_continuation_override`

### V1 selection pipeline order (`choose_next_actor`)

```text
1. No available actors → empty decision
2. Forced speaker in available → hard route (Director bypassed)
3. Continuation override in available (C2 not skipped) → hard route
4. Director LLM inference → postprocess validation
5. validate_turn_selection_decision (forced/continuation/offstage/available checks)
```

---

## 3. Behavioral participation contract (mechanism-independent)

### Forced designation

```text
Given explicit external designation of character D for the next turn,
if D satisfies authoritative eligibility constraints,
D is selected for the next character turn without Director inference.
If D is ineligible, designation is ignored and normal selection proceeds.
```

**External designation sources:** user direct address, operator/harness schedule. Not inferred from prior character beats alone.

### Continuation preference

```text
Given the last committed character beat B by actor A,
if A's move indicates ongoing focal engagement (goal/tactic present),
no superseding continuity event occurred,
no other present eligible actor remains unheard this round,
and A satisfies authoritative eligibility constraints,
then A has selection priority for the next character turn.
If A is ineligible (including already-used-this-round), preference is not applied.
If preference applies but Director runs (C2 skip or hard-route unavailable),
Director must select A or be rejected.
```

**Key:** continuation is a **domain-inferred preference**, not operator forcing. It does **not** grant repeat-speaker rights beyond eligibility — V1 tests confirm used-actor restriction is not bypassed.

---

## 4. Authority ordering

| Layer | Can override | Cannot override |
|-------|--------------|-----------------|
| Cast membership | — | — |
| Presence (present/offstage/absent) | — | Everything below if ineligible |
| Used-this-round exclusion | — | Forced/continuation/Director |
| **Forced designation** | Director; continuation | Presence; used-this-round |
| **Continuation preference** | Director (when hard-route or validation) | Presence; used-this-round; forced designation |
| **Director selection** | — (proposes only) | Eligibility floor |
| **Domain validation** | — | Accepts/rejects Director proposals |
| `end_round` | Stops round | — |
| `no_eligible_actors` | Stops round (no Director) | — |
| Defensive ceiling | Stops round | — |

**Answer:** Neither forced speaker nor continuation override can bypass authoritative presence or used-this-round eligibility. Forced speaker dominates continuation; both dominate unconstrained Director choice.

---

## 5. Continuation vs forced-speaker distinction

**Different concepts.**

| | Forced speaker | Continuation override |
|---|----------------|----------------------|
| **Intent class** | Explicit external designation | Domain-inferred conversational continuity |
| **Source** | User text / harness schedule | Last committed move + orchestration metadata |
| **Persistence** | Session-scoped pending flag | Ephemeral per-turn computation |
| **Typical bypass** | Always hard-route when eligible | Hard-route when eligible + C2 allows; else Director constraint |
| **Product role** | Honor player addressing a character | Prevent premature turn-passing mid-beat |

Do not unify into a single flag. Represent as distinct participation-policy outcomes with shared eligibility floor.

---

## 6. V2 design options

| Option | Description | Fidelity | Clean-V2 fit |
|--------|-------------|----------|--------------|
| **A — Pre-Director hard selection** | Policy returns actor; skip Director | Matches forced speaker; partial for continuation | Good for forced; awkward for continuation C2 |
| **B — Director constraint** | Director runs with mandatory/preferred actor | Matches continuation validation path | Good for continuation; wastes inference when forced |
| **C — Director preference only** | Soft hint; Director may ignore | **Low** — contradicts V1 validation | Poor |
| **D — Participation policy service** | Single `ParticipationDecision` API | **High** — models both paths cleanly | **Best** |
| **E — DSH-local flags** | Port `pending_forced_speaker` to runtime | Medium | **Reject** — duplicates authority |

### Option D detail (recommended)

```text
POST /v1/rounds/participation-decision
  → ParticipationDecision {
      eligible_actors,
      selection_mode: "director" | "designated",
      designated_actor?,
      director_constraint?: { required_actor?, preferred_actor?, constraint_reason },
      participation_trace: { forced?, continuation?, sources[] }
    }
```

`runRound` logic:

```text
eligibility → participation decision
if no eligible → no_eligible_actors
if selection_mode == designated → character turn (no Director)
else → Director with constraint manifest → domain validation
```

---

## 7. Preferred architecture

**Single participation-selection pipeline in Python domain kernel:**

```text
authoritative scene state (ContinuityManager)
        ↓
eligibility projection (existing seam)
        ↓
participation policy resolution
        ↓
ParticipationDecision
        ↓
Director required?
   ├── no  → designated actor → character turn
   └── yes → Director inference → domain validation
        ↓
character turn → commit → narrator
```

**Do not port:** `resolve_continuation_override_actor` as a standalone V2 helper name, Streamlit session flags, AutoGen `create_selector_func`, harness presence hacks in production path.

**Do preserve semantics:** forced designation priority, continuation inference rules, C2 skip, eligibility floor, validation rejection.

---

## 8. Ownership

| Concern | Owner |
|---------|-------|
| Eligibility (presence, used-this-round) | Python `DomainKernel` (existing) |
| Continuation inference rules | Python participation policy (new domain capability) |
| Forced designation ingress | Transport/request layer → participation policy input |
| Director bypass vs constraint | Python `ParticipationDecision.selection_mode` |
| Director inference | DSH `HolyGrailRpRuntime` |
| Director validation | Python `validate_director_decision` (extend with participation constraints) |
| Execution trace | DSH events (`hg/participation-decision`, existing eligibility snapshots) |

---

## 9. Presence/eligibility interaction (edge cases)

| Case | Correct behavior (V1-aligned) |
|------|----------------------------|
| Forced actor present + unused | Hard designate |
| Forced actor offstage | Ignore designation; normal selection |
| Forced actor already used | Ignore designation |
| Continuation actor present + unused + conditions met | Hard designate or Director constraint |
| Continuation actor already used | Preference not applied (`test_turn_runner_continuation_override`) |
| Continuation actor offstage | Not in eligible; preference not applied |
| Unheard present actor exists | Continuation suppressed |
| Only offstage actor unheard | Continuation allowed (`test_resolve_continuation_override_not_suppressed_when_only_offstage_unheard`) |
| Override references non-cast character | Ignored (not in participant_names) |
| Presence changes after prior commit | Next eligibility query governs; stale designation invalidated |

---

## 10. Round-semantics interaction

| Question | Answer |
|----------|--------|
| Director run when valid forced designation? | **No** — hard bypass |
| Director run when valid continuation hard-route? | **No** — unless C2 skip |
| Director run when continuation preference but not hard-route? | **Yes** — with constraint |
| Only override target ineligible? | **Normal selection** — no failure |
| `end_round` from Director? | Unchanged — participation policy does not block |
| `no_eligible_actors`? | Unchanged — checked before participation policy |
| Actor exhaustion? | Unchanged — eligibility removes used actors |
| Repeat-speaker via override? | **No** — eligibility excludes used actors; continuation cannot bypass |
| Defensive ceiling? | Unchanged |
| Director/character failure? | Unchanged |

---

## 11. Trace/event model

Emit `hg/participation-decision` (DSH, log-only) with:

```json
{
  "eligible_actors": ["Bob"],
  "selection_mode": "designated",
  "designated_actor": "Bob",
  "participation_sources": ["forced_designation"],
  "director_required": false,
  "constraint_reason": "user_direct_address",
  "continuation_evaluated": false,
  "forced_designation": "Bob"
}
```

Director events retain `eligibility_snapshot`. Participation trace answers **why this character acted next** without being authoritative — Python `ParticipationDecision` response is authoritative.

---

## 12. Clean-V2 assessment — do not migrate

| V1 mechanism | Disposition |
|--------------|-------------|
| `pending_forced_speaker` / `forced_speaker_consumed` session flags | **Replace** with explicit round-scoped participation request |
| `detect_forced_speaker` heuristics in runtime | **Replace** with ingress API field or pre-resolved designation |
| `create_selector_func` AutoGen path | **Do not migrate** (legacy orchestration) |
| `ensure_forced_probe_actor_present` in production | **Test harness only** |
| Continuation function name/port | **Re-express** as participation policy rules |
| Duplicate eligibility in DSH | **Already rejected** (prior slice) |

---

## 13. Challenge/refinement

| Challenge | Response |
|-----------|----------|
| Preserving V1 workaround? | Continuation C2 skip is real product semantics, not workaround |
| General participation policy vs flags? | Yes — unified `ParticipationDecision` |
| Presence still authoritative? | Yes — eligibility floor unchanged |
| Forced vs continuation same authority? | No — different sources and bypass rules |
| Unnecessary Director calls? | Forced designation eliminates them when eligible |
| Bypass Director too aggressively? | Only when designation actor ∈ eligible_actors |
| Future fairness extensibility? | Participation policy is the extension point (deferred) |
| Orchestration branch clutter? | One policy API vs scattered pre-Director checks |
| Plugin architecture fit? | Domain capability on existing kernel, not new Cordis plugin |

**Refinement:** Split forced designation (ingress-supplied) from continuation inference (domain-computed) inside one policy resolver. Do not add `continuation_override_actor` as a parallel top-level concept in V2 contracts.

---

## 14. Architecture verdict

**Clean design established; implementation can proceed after Governance approval.**

No architecture conflict with current V2 eligibility model. Participation policy sits above eligibility, below DSH orchestration.

**Implementation not authorized in this investigation slice.**

---

## 15. Validation performed

| Suite | Result |
|-------|--------|
| `pytest v2/tests` | 23 passed |
| `npm test` (`v2/rp_runtime`) | 20 passed |
| V1 continuation/forced tests (selected) | 17 passed |
| Implementation added | None |

---

## 16. Next step (Governance gate)

**Recommend:** Governance review of `ParticipationDecision` contract (Option D), then implement **participation policy domain seam** as a focused slice:

1. `POST /v1/rounds/participation-decision` (Python)
2. Wire `runRound` to consume `selection_mode`
3. Extend `validate_director_decision` with participation constraints
4. Add trace events + tests for forced designation and continuation preference paths

Do not implement without Governance approval.
