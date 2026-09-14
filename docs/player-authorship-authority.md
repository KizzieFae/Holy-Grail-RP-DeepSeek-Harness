# Player-authorship authority (#157)

Authoritative contract for when Player-owned facts may be treated as established in semantic evaluation.

## Guardrail

- **ID:** `guardrail:player_authorship`
- Replaces retired `guardrail:player_agency` (no runtime alias).

## Tier-1 provenance whitelist

Player authority requires traceable lineage to one of:

| Origin kind | Ref pattern | Source |
|-------------|-------------|--------|
| `user_post` | `player_fact:user_post:{entry_id}` | Committed Player-authored post in `rp_history` |
| `player_decomposition` | `player_fact:decomposition:{entry_id}` | Authoritative decomposition derived from that post |
| `character_card` | `player_fact:card:{file_id}:{field}` | Player character card in session setup snapshot |
| `tagged_derived` | (explicit tagged refs) | Derived facts with traceable Player lineage |

## Anti-laundering

These do **not** establish Player authority:

- Character or Narrator commits
- Generic transcript prose
- Orchestration output
- Untagged continuity, canon, or scene grounding
- Unknown or unproven provenance

## Authorship vs entitlement

| Dimension | Question | Path |
|-----------|----------|------|
| **R02b** | Is the asserted Player fact authoritatively established? | Character semantic evaluation |
| **R14** | Is this Character entitled to know/use that fact? | Perception / #155; cite `perception_fact:entitlement:{entry_id}:{unit_id}` or `perception_fact:player_internal_entitlement` |
| **R16** | Does the candidate represent a Player action or positional completion as accomplished without sufficient authoritative support? | Character semantic evaluation; cite `guardrail:player_action_completion` |
| **nar_player_authorship** | Does Narrator presentation violate Player authorship? | Narrator semantic QA |

An authoritative Player fact may still be unavailable to a Character under R14.

## Semantic boundaries

**Hard violations:** unsupported objective Player assertion; unsupported Player sensation/embodiment; material Player-behavior amplification.

**Perceptual grounding (#199):** Character private/scenario knowledge does **not** authorize fabrication of Player physical, physiological, emotional-display, or other sensory evidence. Such claims require support from `perception_fact:authorized_inventory:*`, `perception_fact:entitled:*`, applicable `grounding:*` visible facts, or established `player_fact:*` observable sources. **Subjective phrasing alone does not cure missing perceptual substrate.**

**Permissible:** faithful paraphrase of entitled perceptual evidence; fallible interpretive conclusions explicitly anchored to entitled perceptual evidence; collaborative world/environment invention without unsupported Player-body attribution.

## Fail-closed

- **Character:** hard R02b violations remain fail-closed (existing behavior).
- **Narrator:** hard `nar_player_authorship` exhaustion yields `player_authorship_rejected` — no committed fallback.

## Narrator repair obligation (#157)

When attempt 0 produces a hard authoritative `nar_player_authorship` finding, runtime records a **repair obligation** (not a permanent round poison). Regeneration may succeed only when a later evaluation **clears** that obligation:

| Outcome | Meaning | Renderable |
|---------|---------|------------|
| **Cleared** | Later pass with no `nar_player_authorship` findings | Yes (subject to other gates) |
| **Persists** | Later hard `nar_player_authorship` | No — fail-closed |
| **Unverified** | Soft-only PA finding, unrelated soft residuals, or otherwise insufficient repair proof | No — fail-closed |

Orchestration enforces obligation existence, verification, and terminal consequences. Semantic equivalence remains the evaluator's responsibility (no keyword matching).

## Forensic chain

```
Player-authoritative source → player_fact:* / guardrail ref
  → evaluator authority context → semantic determination
  → pass/reject → repair obligation (if hard PA) → correction context
  → regenerated candidate → repair verification → accept / regenerate / fail-closed
```

Do not fabricate `player_fact:*` refs for unsupported assertions. Record guardrail citation and inventory absence.

## Player action completion (#193)

- **Guardrail ID:** `guardrail:player_action_completion`
- **R16** enforces that Character moves do not assume Player acceptance, entry, agreement, or positional completion without authoritative support.
- Invitation, `location_entry_outcome.allowed`, threat, and unresolved coercion do **not** establish accomplished Player movement.
- **R16** is orthogonal to **R02b** (authorship) and **R14** (entitlement).

## Implementation

- Authorship contract: `v2/domain_api/player_authorship_authority.py`
- Action-completion contract: `v2/domain_api/player_action_completion_authority.py`
- Character context: `v2/domain_api/semantic_evaluation_context.py`, `v2/domain_api/character_context.py`
- Narrator context: `v2/domain_api/narrator_semantic_qa_context.py`
