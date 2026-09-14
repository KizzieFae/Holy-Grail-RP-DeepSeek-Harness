# Issue #197 — False-Complex Validation Refinement Record

**Date:** 2026-09-14  
**Issue:** [#197](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/197)  
**Phase:** Validation refinement (lifecycle remains `validated`)  
**Superseded code candidate:** `3ed4a2d` / evidence HEAD `5ba6808`  
**Refined candidate:** `aff53a4` (post evidence commit pending)

## Root cause

**Systematic verifier rubric over-aggression**, not ordinary stochastic variance alone.

The original verifier instruction told the model to:
- disqualify on "any ambiguity that could hide" disqualifying content;
- treat "implicit" internal state broadly;
- "bias toward finding disqualifying content when plausible."

Live corpus evidence (`issue-197-corpus-certification-2026-09-14.json`) showed triage affirmative + verifier disqualified on clearly uniform text:

| Case | Verifier reason | Audit note (why) |
|------|-----------------|------------------|
| `pos_simple_action` | `private_or_unexpressed_content` | Invented "possible implicit interiority or off-screen intent" from stepping back |
| `pos_scene_description` | `authorial_environmental_narration_nonuniform_perceptibility` | Treated ambient rain/candlelight as authorial narration; hypothetical viewing-angle differences |
| `pos_f06_observable_only` | `private_internal_cognition_present` | Reclassified observable "double-checking" as "implicit attentional/verificatory mental act" |

Classification: **hallucinated private/internal content** and **overly conservative interpretation of observable prose** driven by rubric wording.

## Predeclared repeat design

See `issue-197-false-complex-refinement-design-2026-09-14.md`: 3 repeats × 5 positives; 1 repeat × 5 negative controls (post only).

## Pre-remediation repeat (`88be1bd` / old rubric)

Record: `issue-197-false-complex-refinement-pre-2026-09-14.json`

| Case | Final uniform rate (3 runs) |
|------|----------------------------|
| `pos_simple_speech` | 2/3 |
| `pos_simple_action` | 2/3 |
| `pos_scene_description` | 2/3 |
| `pos_mixed_action_speech` | 3/3 |
| `pos_f06_observable_only` | **0/3** |
| **Aggregate** | **9/15 (60%)** |

`pos_f06_observable_only` showed **persistent** verifier veto (systematic on F06-adjacent observable action).

## Remediation

Refined `PLAYER_UNIFORM_ELIGIBILITY_VERIFICATION_OUTPUT_INSTRUCTION` and task prompt to:
- disqualify only **stated** nonuniform semantic content in the source text;
- not invent unstated motivation, hidden cognition, or hypothetical perceptibility differences;
- treat ordinary observable actions and ambient scene description as clear unless text states private/concealed/subset content;
- return `uncertain` rather than inventing disqualifiers;
- retain adversarial scrutiny for genuinely mixed/implicit-internal prose (e.g. steeling oneself).

Architecture E unchanged: affirmative triage → one adversarial verification → deterministic gate.

## Post-remediation repeat (`aff53a4`)

Record: `issue-197-false-complex-refinement-post-2026-09-14.json`

| Metric | Value |
|--------|-------|
| Positive uniform rate | **15/15 (100%)** |
| Negative false-simple | **0/5** |
| F06 exact / paraphrase | `full_pvr` (triage negative, verifier not invoked) |

## Deterministic regressions

- Node (#197 + triage + #194 targeted): **25/25**
- Python (parity + #194 + #121): **35/35**

## Judgment

Pre-remediation 60% positive yield with 0/3 on F06 observable-only was **material** false-complex behavior. Post-remediation bounded repeat shows reliable positive-path operation while mandatory negatives remain safe. Prior `validated` safety acceptance stands; positive-path concern addressed by rubric calibration at `aff53a4`.
