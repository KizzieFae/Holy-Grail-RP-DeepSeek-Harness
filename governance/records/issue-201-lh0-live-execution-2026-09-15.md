# Issue #201 LH-0 — Live Seam Verification Execution Record

**Date:** 2026-09-15  
**Issue:** [#201](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/201)  
**Phase:** Phase 5 — long-horizon supplement / LH-0 live mechanical seam verification  
**Activation commit:** `741e1ce`  
**Apparatus candidate:** `a96886b`  
**Execution candidate SHA (HEAD at run):** `a96886b78c190cf8386649747736c879c361e4c0`  
**Canonical state:** `consensus_reached` (unchanged)  
**Assigned / effective workflow weight:** `full` / `full`  
**LH-1A:** NOT authorized  
**Production A4→A2 migration:** NOT authorized  

---

## Run identity

| Field | Value |
|-------|-------|
| Output directory | `data/investigation_runs/issue201-lh0-live-2026-09-15T21-16-16-968Z` |
| Primary report | `issue201-lh0-live-execution-report.json` |
| Fixture | `lh0_seam_micro_v1` (`6295679c…79088`) |
| Policy | `ayame_lh0_policy_v1` (`b2b36d57…7a9e2`) |
| Scenario | `ayame_controlled` / `ayame_household_entry_evaluation` |
| Inference mode | `live` (DeepSeek mount) |
| Wall time (LH-B only) | ~495s (6 turns) |

---

## Forensic adjudication summary

> LH-0 validates transport, persistence, consumption, deferral, activation, and forensic attribution. It does not establish comparative RP quality or long-horizon narrative value.

| Arm | Turns executed | Forensic LH-1A readiness | Primary blocking seam |
|-----|----------------|--------------------------|------------------------|
| **LH-B** (Plot/Scribe) | 6/6 committed | **NOT READY** | Character projection/receipt + consumer-use attribution |
| **LH-C** (Storyteller-class) | 0 (turn-1 abort) | **NOT READY** | Adapter projection package rejected (`missing inference_kind`) |
| **LH-D** (Consolidated NI) | 0 (turn-1 abort) | **NOT READY** | Same adapter projection rejection as LH-C |

Automated in-runner adjudication credited LH-B with a clean pass (criteria A–J). **Governance strengthened review overrides that result** where harness heuristics conflate generation with downstream receipt/use.

---

## LH-B findings (partial seam proof)

**Established (live):**

- Live plot cognition post-commit (`plot_cognition_init` + `plot_cognition_update`) across 6 turns.
- Durable lh0 obligation mirror persisted under `sessions/_lh0_persistent_obligations/`.
- Director-side projection candidates from turn 3 (`director_receipt: true`).
- Lifecycle classifier transitions (`DEFERRED_VALID` → `ACTIVATED_CONSEQUENTIAL`) in harness store.
- Negative control `LH0-OBL-PREMATURE` did not reach `ACTIVATED_PREMATURE`.
- Actor-context isolation pass; no PVR leaks observed.

**Not established (blocking LH-1A):**

- `character_receipt` never true (turns 1–6); `character_move` obligations never reached authorized character consumer package.
- No forensic proof character cognition referenced projected obligations (criterion E).
- No obligation-linked downstream decision influence (criterion F); commits alone are insufficient.
- Consequential activation is harness state classification only; no causally linked observable consequence per obligation (criterion G).
- Deferred→later activation lacks later consumer-use evidence after predicate satisfaction (criterion H).
- K6 probe: both anchors eligible, zero projected (`k6_class_suspected: true`).

---

## LH-C / LH-D findings (adapter abort)

Both arms failed before turn 1 completed:

```
model-context package rejected: missing inference_kind
```

**Attribution:** projection adapter (`buildLh0FinalizedProjection` → `precomputedFinalizedProjection` → `prepareCharacterContext`) — contributions lack manifest-required `inference_kind`. This is a bounded LH-0 live-adapter defect, not a production architecture mutation.

---

## Negative controls

Deterministic classifier simulation (`simulateNegativeControl`) matched expected seams for all four NC IDs. **Live seam-break probes were not re-exercised under actual execution** beyond classifier discrimination.

---

## Evidence disposition

| Artifact | Disposition |
|----------|-------------|
| `data/investigation_runs/issue201-lh0-live-2026-09-15T21-16-16-968Z/` | Retain under investigation_runs (audit authority) |
| Per-arm `LH0-LIVE-*-sequence.json` | Retain |
| Session dirs under output (`hg-session-*`) | Retain with run bundle |
| Uncommitted live harness (`issue201-lh0-live-*.mjs`, policy JSON) | Working tree; commit only with Governance approval |

---

## Next Governance decision required

Authorize **bounded LH-0 adapter remediation** (projection manifest compliance + consumer receipt wiring + strengthened adjudication heuristics) and **re-run LH-B character-consumer path + LH-C/LH-D live arms once** — or accept LH-B partial director-path evidence only and defer persistent Storyteller/consolidated arms pending adapter fix. **Do not** authorize LH-1A, production A4→A2, or K6 remediation under this result.
