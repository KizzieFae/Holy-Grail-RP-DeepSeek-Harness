# Issue #199 — Investigation & Proposal Record

**Date:** 2026-09-14  
**Issue:** [#199](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/199)  
**Source session:** `hg-session-f883b2dd-93cc-4914-bcff-8c862589b311`  
**Repository SHA at session:** `09f39295cfc6d6aa62367c65d9e09cdbc89b24b0`  
**Disposition:** Investigation complete; consensus reached; implementation validated 2026-09-14. See `issue-199-implementation-validation-2026-09-14.md`.

## Root cause (primary)

**Character generation contract gap + semantic-evaluator enforcement gap (combination).**

Character move generation receives scenario premise and character-private knowledge without machine-readable **knowledge-vs-perceptual-evidence** provenance separation, and without the legacy `prompt_builders.py` evidence-discipline block present in manifest assembly. The model invented an NPC observational catalog (`faint tells of recent strain`) from knowledge substrates. Character semantic evaluation (R02b) had sufficient authority inventory to reject the move as an unsupported objective Player sensation/embodiment assertion but passed.

## Contributing factors

1. **Zero entitled Player observables** for Ayame on R1 (door/barrier + internal units) — no positive `user_turn_trigger` lane in Character manifest.
2. **Scenario premise** explicitly states applicant lost employment/housing; **character_private** states engineered vulnerability — both authorize *knowledge*, not *perception*.
3. **R02b subjective-interpretation permissibility** ambiguity — cataloguing language may be misread as permissible inference rather than objective Player-body assertion.
4. **No deterministic observable-grounding gate** on Character move ingress or semantic evaluation.

## Earliest divergence

`22531d59-6bb1-4e88-bf9d-b2493e32a414` (character_move) beat 2. Narrator presentation (`d080e7f2-45d4-474a-84b4-63fb53c0f535`) reproduced committed content; not Narrator-originated.

## Recommended remediation (refined — Governance challenge 2026-09-14)

**Option D (minimal combination, no new LLM pass):**

1. **Final invariant** — Knowledge may support private inference; perceptual interpretation requires authorized perceptual evidence; subjective phrasing does not create evidence.
2. **Positive perceptual inventory** — Deterministic `perception_fact:authorized_inventory:*` built from existing PVR/NVR projection + scene_grounding visible facts (current + prior entitled units); explicit when empty.
3. **Generation contract** — Shared instruction block: context/knowledge may inform reasoning; only authorized perceptual evidence may ground claimed sensory observations. **No new epistemic lane labels** on scenario/private contributions.
4. **R02b clarification** — Tighten `PLAYER_AUTHORSHIP_GUARDRAIL_TEXT` and eval instruction; remove subjective-framing loophole for Player sensory claims; no new rule identifier.
5. **Tests** — Matrix A–G fixtures + deterministic inventory builder tests.

## Non-changes

- PVR decomposition/triage (#197) — behaved correctly in source session.
- Player internal/private classification — correct.
- Narrator lane — propagates committed Character content; not primary fix target.
- No new always-on LLM verifier.

## Evidence anchors

| Artifact | ID |
|----------|-----|
| Character move | `22531d59-6bb1-4e88-bf9d-b2493e32a414` |
| Semantic eval | `17ff4886-6f97-488d-b602-036ec3e3af32` |
| PVR decomposition | `26746c33-48dc-4b3a-8827-1f46e1a778f1` |
| Narrator presentation | `d080e7f2-45d4-474a-84b4-63fb53c0f535` |
| Audit tag | `45f34950-516f-4580-94ae-bb9eff3bc5ce` |
