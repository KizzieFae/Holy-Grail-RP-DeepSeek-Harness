# Issue #201 — LH-1B Causal Apparatus Implementation & Qualification Record

**Date:** 2026-09-16  
**Phase:** 5 — long-horizon persistent-narrative-cognition supplement  
**Subphase:** LH-1B causal-apparatus implementation and qualification  
**Issue:** #201 (`consensus_reached`, P1, full/full)  
**Live LH-1B:** NOT authorized  
**Blind-packet tooling defect:** #208 (filed, not implemented)

## Activation

| Field | Value |
|-------|-------|
| Assigned workflow weight | `full` |
| Effective workflow weight | `full` |
| Bootstrap profile | Full |
| LH-0 | COMPLETE |
| LH-1A | COMPLETE (blind evaluation LOCKED) |
| LH-1B proposal | REVIEWED AND ACCEPTED WITH REFINEMENTS |
| LH-1B live execution | NOT authorized |
| K6 remediation | NOT authorized |
| #201 → `implemented` | NOT authorized |

## Frozen hashes

| Artifact | SHA-256 |
|----------|---------|
| Fixture (`ayame_lh1b_v1`) | `96b8ef4fa90ab27f0956b4da8edba1a090b5efd22df28825d4e1a05ea9918a64` |
| Player policy (`ayame_lh1b_policy_v1`) | `362207fa89fa89b87765c5aa78ca5d554c7ae67264eda99463feb09d36514fa3` |
| Causal design | `78bc5ff240f08d8658df9645e4b862366c0a02d8ff3fa96cf18044d436484c58` |

## Deterministic validation

```
node --test v2/rp_runtime/tests/issue201-lh1b-apparatus.test.mjs
# 5/5 pass

runLh1bApparatusValidationSuite()
# pass: true, pass_count: 38, fail_count: 0, synthetic proofs: 14
```

## Experimental matrix (frozen)

| Sequence | Arm | Purpose |
|----------|-----|---------|
| S1 | LH-A | Character-fork control replicate 1 |
| S2 | LH-B | Plot/Scribe Character-fork replicate 1 |
| S3 | LH-A | Character-fork control replicate 2 |
| S4 | LH-B | Plot/Scribe Character-fork replicate 2 |
| S5 | LH-D | Character forks + Director persistent-guidance fork |
| S6 | LH-A | Paired control for S5 |

Ayame only; 18 turns; scenes at T1–9 / T10–18; C1=6, C2=12, C3=18; LH-C excluded.

## Character forks (preregistered)

| Fork ID | Class | Establish | Decision | Obligation |
|---------|-------|-----------|----------|------------|
| FORK-LH1B-DORMANT-RECORD | dormant record | T3 | T15 | LH1B-AYA-DORMANT-RECORD |
| FORK-LH1B-PROMISE-GATE | promise/commitment | T7 | T16 | LH1B-AYA-PROMISE-GATE |
| FORK-LH1B-DEFERRED-KEY | delayed consequence | T4 | T17 | LH1B-AYA-DEFERRED-KEY |
| FORK-LH1B-FORESHADOW-ACCESS | foreshadow/payoff | T5 | T18 | LH1B-AYA-FORESHADOW-ACCESS |

## Director fork (revised advisory)

**Obligation:** `LH1B-AYA-DIR-TRAJECTORY`  
**Semantic content:** Applicant reached foyer but not seated for full terms; threshold compensation exchange unresolved without consequence.  
**Fork:** `FORK-LH1B-DIR-TRAJECTORY` at T15.  
**Not:** actor selection, beat prioritization, or “choose Ayame.”

## Implementation scope

### New governance artifacts
- `governance/records/issue201-lh1b-fixtures/ayame_lh1b_fixture_v1.json`
- `governance/records/issue201-lh1b-policies/ayame_lh1b_policy_v1.json`

### New LH-1B lib modules (`v2/rp_runtime/scripts/lib/`)
- contract, fixtures, player-policy, substrate-uniqueness, causal-classifier, causal-r0-r5, provenance, archaeology, cost-accounting, orchestrator, validation-lib, synthetic-proofs, preflight-lib, live-lib (stub), blind-packet (secondary readiness)

### Runtime / domain seam
- Character provenance preservation (`assembled-request.mjs`, `recorder.mjs`, `character-phase.mjs`)
- Director projection transport (`director-phase.mjs`, `a2-beat-orchestration.mjs`, `issue201-lh0-consumer-evidence.mjs`)
- Domain API Director prepare merge (`contract.py`, `director_context.py`, `http_transport.py`)

### Tests
- `v2/rp_runtime/tests/issue201-lh1b-apparatus.test.mjs`

## Residual limitations

- Live runner stub only (`issue201-lh1b-live-lib.mjs`); full turn runner wiring deferred to live authorization.
- Domain Director projection merge is minimal inline merge; not full storyteller round-packaging binding validation.
- Blind-secondary evaluation optional; `issue201-lh1b-blind-packet.mjs` requires real presentations (#208).

## Next Governance decision

Authorize or deny **live LH-1B S1–S6** campaign after reviewing this qualification record, frozen hashes, and synthetic seam proofs. Do not authorize if fixture/policy/causal-design hashes drift.
