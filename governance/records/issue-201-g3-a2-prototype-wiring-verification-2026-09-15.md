# Issue #201 G3-A — A2 Prototype Wiring & Objective-Gate Verification Record

**Date:** 2026-09-15  
**Issue:** [#201](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/201)  
**Execution stage:** `consensus_reached` — In Progress / Awaiting Consensus / **P1**  
**Assigned / effective workflow weight:** `full` / `full`  
**G3 proposal:** `1cdc986`  
**Status:** G3-A wiring complete — **NOT G3-B live comparison**

---

## 1. Summary

G3-A implemented harness-isolated A2 beat orchestration, deterministic spatial-claim validation, obligation dispatch, decision-value accounting, and deterministic tests. **No live semantic architecture comparison (G3-B) was executed.**

---

## 2. Candidate SHA

Recorded at commit time (see git log for `docs(#201): G3-A A2 prototype wiring`).

---

## 3. Changed files

| Path | Purpose |
|------|---------|
| `v2/rp_runtime/src/lib/a2-beat-orchestration.mjs` | Experimental A2 orchestrator |
| `v2/rp_runtime/src/lib/a2-obligation-dispatch.mjs` | Deterministic obligation signals |
| `v2/rp_runtime/src/lib/a2-decision-value-logger.mjs` | Per-inference decision-value records |
| `v2/rp_runtime/scripts/issue201-g3-a2-shadow-validation.mjs` | Harness wiring verification entry |
| `v2/rp_runtime/scripts/lib/issue201-g3-scenarios.mjs` | Frozen scenario definitions |
| `v2/rp_runtime/tests/a2-beat-orchestration-g3a.test.mjs` | Isolation/topology/entitlement tests |
| `v2/domain/modules/scenario_spatial_validator.py` | Deterministic spatial-claim validator |
| `v2/domain/tests/test_scenario_spatial_validator.py` | Unit tests |
| `v2/domain/tests/test_issue_201_g3a_spatial_kernel.py` | Arkham kernel integration |
| `v2/domain_api/kernel.py` | `validate_presentation_spatial_claims` |
| `v2/domain_api/contract.py` | Request/response types |
| `v2/domain_api/http_transport.py` | `/v1/presentation/spatial-claims/validate` |
| `v2/rp_runtime/src/lib/domain-api-client.mjs` | Client method |
| `v2/rp_runtime/src/plugins/hg-phase-executors/narrator-phase.mjs` | `skipNarratorEnvironmentCognition` option |
| `data/scene_templates/arkham_asylum_mess_hall_arena.json` | Authoritative zone facts |

**Production orchestrator (`hg-round-orchestrator/service.mjs`) and bootstrap: NOT modified.**

---

## 4. Prototype isolation proof

| Requirement | Evidence |
|-------------|----------|
| No production bootstrap import | `a2-beat-orchestration-g3a.test.mjs` — bootstrap/mount-hg-services grep |
| Harness-only entry | `issue201-g3-a2-shadow-validation.mjs` |
| Isolated temp runtime | `startHarnessRuntime` temp `HG_DATA_DIR` |
| Experimental labels | `schema: issue201_g3_a2_round_v1`, `architecture_arm: a2_prototype` |
| Removable without production change | Delete `a2-*` + `issue201-g3-*` modules |

---

## 5. Simple-path topology

**Sequence enforced:** Character cognition → move validation → commit → Narrator cognition → presentation validation → (optional) spatial claims validation.

**Absent cognition (verified in topology proof):** ST, Director QA, Narrator QA, env cognition, orientation LLM, librarian mediation, sync Plot, character semantic eval (F1 default), plot epistemic eval.

**Two-call contract:** Character move + Narrator presentation (Director deterministic when single eligible actor).

---

## 6. Spatial-validator architecture

**Contract:** `hg_presentation_spatial_claims_v1` with structured `claims[]` (`entity_id`, `relation`, `zone_id` / `target_entity_id`).

**Not prose scraping.** Validates against authoritative `character_zones` resolved from scene template + role assignments.

**Sample-E class:** `magpie` @ `harley_ivy_table` contradicts authoritative `across_room` — **detected** (kernel integration test).

**Residual boundary:** Claims for unknown entities → `unknown` (non-blocking); figurative/unrepresented prose → no claim surface (not validated).

---

## 7. Arkham fixture spatial additions

Added `perceptual_scene_context.character_zones_by_role` to `arkham_asylum_mess_hall_arena.json`:

- `instigator` / `instigator_accomplice` → `harley_ivy_table`
- `new_arrival` / `impulse_disruptor` → `across_room`

**Rationale:** Opener narrative already places Harley/Ivy at one table and Magpie across the room; facts were not previously deterministic for validation.

---

## 8. Character semantic-eval removal (F1)

**OFF by default** in A2 orchestrator (`semanticEvaluationEnabled: false`). Simple-path test passes without semantic evaluator. **No structural impossibility observed.**

---

## 9. Unavoidable A4 coupling

| Coupling | Class | Threat |
|----------|-------|--------|
| Domain Host session/round/commit APIs | Substrate | None — required |
| Phase executors (`runCharacter`, `runNarrator`) | Substrate reuse | None — flags control topology |
| Participation/eligibility engine | Substrate | None |
| `skipNarratorEnvironmentCognition` param on narrator-phase | Minimal shared module option | Low — default false; production orchestrator unchanged |

---

## 10. Tests executed

```text
python -m pytest domain/tests/test_scenario_spatial_validator.py domain/tests/test_issue_201_g3a_spatial_kernel.py  → 10 passed
node --test tests/a2-beat-orchestration-g3a.test.mjs  → 4 passed
node scripts/issue201-g3-a2-shadow-validation.mjs  → wiring report OK
```

---

## 11. G3-B readiness

| Item | Status |
|------|--------|
| A2 orchestrator wired | Ready |
| Spatial validator | Ready (structured claims surface) |
| Decision-value accounting | Ready |
| Obligation dispatch | Ready (harness-local) |
| Live F06/Arkham comparison | **NOT authorized** |
| Baseline rerun policy | Only on material substrate drift |

---

## 12. G3-D decision recorded

**Initial longitudinal sequence length = 4 turns** (D-10 comparability).

---

## 13. Stop-condition assessment

**No stop conditions triggered.** Prototype wiring succeeded without production mutation or cognition expansion.

---

## 14. Governance decision required

**Authorize G3-B** live F1 simple-beat comparison (A2 prototype vs D-07 ablated lean baseline) with blind evaluation — **not authorized by this record**.

**Issue #201 remains `consensus_reached`.**
