# Issue #121 / PR #123 — Formal Validation Evidence

**Recorded:** 2026-09-05  
**Issue:** #121 — Player visibility triage gate (checker + uniform_projection)  
**PR:** https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/pull/123  
**Base (`origin/main`):** `4f0d79962bdb0fd89dcec15aa6f5d0e89097f390`

## Candidate lineage

| Stage | SHA | Notes |
|-------|-----|-------|
| Implementation + live checker evidence | `b26b2ff8b3c2cb1bd34d6641e198b2d7f80fabe9` | Greptile SUCCESS (P1/P2 remediated) |
| Documentation-only remediation | **This commit** (PR #123 HEAD after push) | `docs/architecture.md` false-simple/false-complex asymmetry; no runtime change |

## Deterministic validation (candidate `b26b2ff`)

| Command | Result |
|---------|--------|
| `pytest v2/domain/tests/test_issue_121_uniform_projection.py` + related #91/#120/perceptual | 31 passed |
| `node --test player-visibility-triage-phase.test.mjs` + `player-decomposition-phase.test.mjs` | 14 passed |
| `pytest v2/domain/tests/` | 990 passed |
| `pytest v2/tests/` (repo root) | 268 passed, 1 xfailed |

## Checker corpus (live LLM — not re-run for doc-only delta)

- **Artifact:** `v2/rp_runtime/tests/fixtures/issue121-checker-validation-report.json`
- **Cases:** 12 mandatory × 3 repeats = **36 live calls**
- **False-simple:** **0/36**
- **False-complex:** **0/36** (reported separately per architecture)
- **#120 seiza/Japan:** 3/3 → `full_pvr`
- **#88 mixed visibility:** 3/3 → `full_pvr`

## Checker-evidence / candidate binding (§B.0.2 reuse)

- Corpus generated during validation of implementation commits (`f6a4dab`, checker prompt finalization).
- `b26b2ff` changed **validator-only** trust/size enforcement (`player-visibility-triage-*` inference_id prefix, `MAX_PVR_UNIT_TEXT_CHARS`); **checker prompt and routing behavior unchanged**.
- Documentation-only remediation does not affect runtime; **checker inference not re-run**.

## Greptile

- Initial (`f6a4dab`): P1 checker-provenance forgeability, P2 uniform size-bound bypass.
- Remediated on `b26b2ff`; rereview **SUCCESS**.
- Documentation-only HEAD requires exact-head Greptile rereview after push.

## Documentation remediation

- `docs/architecture.md`: checker validation asymmetry (false-simple vs false-complex).

## Governance disposition

- **Validation:** substantively successful.
- **Integration / merge / closure:** **not authorized** (pending Governance).
