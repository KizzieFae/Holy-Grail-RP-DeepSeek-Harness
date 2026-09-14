# Issue #197 — Formal Validation Record

**Date:** 2026-09-14  
**Issue:** [#197](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/197)  
**Final candidate:** `3ed4a2db4de03a562808cd4a06f11a2f5112f8cf`  
**Disposition:** **VALIDATED**

## Provenance remediation

| Item | Value |
|------|-------|
| **Original characterization SHA field** | `65512d5` (execution HEAD at run) |
| **Resolution** | Outcome A — reconstructable |
| **Implementation content at run** | Full #197 tree (uncommitted, dirty working tree) |
| **Implementation commit** | `adac09c` (subsequently committed identical content) |
| **Evidence remediation commit** | `3ed4a2d` (provenance addendum + validation harness only) |
| **Rerun required** | No — original six observations preserved |

Forensic proof: characterization results include verifier output impossible at `65512d5` (`player-uniform-eligibility-verification.mjs` absent).

Record: `governance/records/issue-197-characterization-provenance-2026-09-14.md`

## Activation

| Item | Value |
|------|-------|
| **Branch** | `issue-197-uniform-verification` |
| **Final candidate** | `3ed4a2d` |
| **Previous implementation** | `adac09c` |
| **Investigation lineage** | `65512d5` |
| **origin/main** | `79cdb5a` |
| **Merge base** | `79cdb5a` (no material base drift) |
| **Working tree** | Clean |
| **Issue state** | `implemented` → `validated` |
| **Weights** | `standard` / `full`, Full bootstrap |

## Deterministic policy validation

```bash
cd v2/rp_runtime
node --test tests/issue-197-uniform-eligibility-verification.test.mjs \
             tests/player-visibility-triage-phase.test.mjs \
             tests/issue-194-env-cognition-profile-safety.test.mjs \
             tests/issue-194-player-decomposition-retry.test.mjs
```

**Result:** 25/25 passed

```bash
cd v2/domain
python -m pytest tests/test_issue_121_uniform_projection.py \
                 tests/test_manifest_policy_parity.py \
                 tests/test_issue_194_pvr_coverage_fidelity.py \
                 tests/test_issue_124_semantic_normalization.py -q
```

**Result:** 35/35 passed

All required routing-matrix rows covered including affirmative→disqualified, malformed verifier, inference failure, single verifier invocation, and #194 targeted regressions.

## Live semantic matrix

Script: `node scripts/issue197-formal-validation.mjs`  
Record: `governance/records/issue-197-formal-validation-2026-09-14.json`

| Scenario | Triage | Verifier | Final route | Result |
|----------|--------|----------|-------------|--------|
| F06 mixed (exact) | negative | — | `full_pvr` | PASS |
| F06 paraphrase | negative | — | `full_pvr` | PASS |
| Explicit internal cognition | negative | — | `full_pvr` | PASS |
| Concealed action | negative | — | `full_pvr` | PASS |
| Directed speech | negative | — | `full_pvr` | PASS |
| F06 observable-only | affirmative | clear | `uniform_projection` | PASS |
| Simple observable action | affirmative | clear | `uniform_projection` | PASS |
| Simple room speech | affirmative | clear | `uniform_projection` | PASS |

**8/8 correct; 0 mandatory-negative false-simple.**

## Verifier interception evidence

**Live natural interception (corpus run):** 3 cases where triage proposed affirmative and verifier disqualified → `full_pvr`:

- `pos_simple_action` — verifier `disqualified` / `private_or_unexpressed_content`
- `pos_scene_description` — verifier `disqualified` / `authorial_environmental_narration_nonuniform_perceptibility`
- `pos_f06_observable_only` — verifier `disqualified` / `private_internal_cognition_present`

These demonstrate the adversarial gate is live and fail-safe biased (not dead insurance).

**Deterministic proof:** `affirmative triage + disqualifier routes to full_pvr` test in `issue-197-uniform-eligibility-verification.test.mjs`.

**Limitation:** Formal validation matrix did not observe a mandatory-negative false-affirmative intercepted solely by verifier (triage caught negatives first). Corpus run supplied natural affirmative→disqualified examples on positive corpus cases (stochastic over-disqualification, fail-safe direction).

## Corpus certification

```bash
cd v2/rp_runtime
node scripts/issue121-checker-validation.mjs --repeat 1
```

Record: `governance/records/issue-197-corpus-certification-2026-09-14.json`

Harness uses **end-to-end** `runPlayerVisibilityTriagePhase` (triage + verifier + deterministic gate), not raw triage alone.

| Metric | Value |
|--------|-------|
| Corpus size | 18 |
| False-simple (mandatory negatives) | **0** |
| Safety-critical false-simple | **0** |
| False-complex (positives) | 3 (stochastic verifier over-disqualification) |

Positives passing uniform path: `pos_simple_speech`, `pos_mixed_action_speech`. Formal validation matrix independently confirms legitimate uniform positives remain operational.

## Latency (candidate `3ed4a2d`, live)

| Path | Triage | Verifier | Combined |
|------|--------|----------|----------|
| Uniform affirmative (F06 observable) | ~1037 ms | ~985 ms | ~2.0 s |
| Uniform affirmative (simple action) | ~1013 ms | ~1189 ms | ~2.2 s |
| Negative at triage (F06 mixed) | ~1694 ms | — | ~1.7 s |

Full-PVR reference (~37 s from #194) cited as context only; no production savings claim.

## Non-interference

Post-`adac09c` delta is evidence/provenance-only (`3ed4a2d`). #197 scope limited to perceptual routing (triage orchestration, verifier, audit). No changes to Character/Director/Narrator behavior, #193 action-completion, or #194 decomposition semantics.
