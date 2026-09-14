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

**Explicit empty inventory:** When no entitled Player sensory substrate exists, Character generation still receives an `authoritative_perceptual_inventory` contribution whose master text explicitly states that no authorized perceptual evidence is available (`entitled_count: 0` in provenance). An empty inventory is positive forensic evidence of absent substrate — not omission of the lane.

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
- **R16 inverse (#200):** rejects **objective regression** — asserting an authoritative completed Player action or positional state did not occur, remains unperformed, or was undone without reversal authority. Character ignorance, commands from incomplete perception, deliberate deception/manipulation, and distinct subsequent requirements are **not** objective regression.
- Invitation, `location_entry_outcome.allowed`, threat, and unresolved coercion do **not** establish accomplished Player movement.
- **R16** is orthogonal to **R02b** (authorship) and **R14** (entitlement).

## Bidirectional Player-action authority (#200)

Authoritative Player contributions establish world/action truth. Character epistemics remain separately governed by **R14** perception/entitlement.

| Dimension | Contract |
|-----------|----------|
| World/action truth | Tier-1 `player_fact:*` and committed continuity |
| Character epistemics | Perception entitlement (#155, #199) |
| Character behavior | May be ignorant, mistaken, deceptive, or impose distinct requirements |

Player-authored state must not be **advanced beyond** or **objectively regressed behind** authoritative Player contribution.

## Derived scene-pressure freshness (#200)

Librarian `semantic_unmet_condition` overlays bind `player_authority_sequence_at_apply` at apply time. After a newer tier-1 Player contribution (higher `rp_history` user `sequence_index`), objective semantic fields are withheld until the overlay is refreshed/revalidated. This is structural freshness — not lexical reconciliation against Player prose.

Character packaging includes a compact precedence note: derived scene pressures are dramatic/advisory and do not override newer authoritative Player facts or grant unperceived entitlement.

## Implementation

- Authorship contract: `v2/domain_api/player_authorship_authority.py`
- Action-completion contract: `v2/domain_api/player_action_completion_authority.py`
- Perceptual inventory assembly: `v2/domain_api/character_perceptual_inventory.py` (`authoritative_perceptual_inventory` manifest lane; wired via `character_upstream_context.py`)
- Scene-pressure freshness projection: `v2/domain/modules/continuity_scene_pressure_projection.py`, `v2/domain/modules/continuity_librarian_issue_pressure.py`
- Character context: `v2/domain_api/semantic_evaluation_context.py`, `v2/domain_api/character_context.py`, `v2/domain_api/character_context_projector.py` (scene-pressure precedence note)
- Narrator context: `v2/domain_api/narrator_semantic_qa_context.py`
