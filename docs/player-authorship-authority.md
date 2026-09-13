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
| **nar_player_authorship** | Does Narrator presentation violate Player authorship? | Narrator semantic QA |

An authoritative Player fact may still be unavailable to a Character under R14.

## Semantic boundaries

**Hard violations:** unsupported objective Player assertion; unsupported Player sensation/embodiment; material Player-behavior amplification.

**Permissible:** clearly framed subjective Character interpretation; faithful paraphrase; collaborative world/environment invention without unsupported Player-body attribution.

## Fail-closed

- **Character:** hard R02b violations remain fail-closed (existing behavior).
- **Narrator:** hard `nar_player_authorship` exhaustion yields `player_authorship_rejected` — no committed fallback.

## Forensic chain

```
Player-authoritative source → player_fact:* / guardrail ref
  → evaluator authority context → semantic determination
  → pass/reject → retry/repair/fail-closed → accepted output
```

Do not fabricate `player_fact:*` refs for unsupported assertions. Record guardrail citation and inventory absence.

## Implementation

- Contract module: `v2/domain_api/player_authorship_authority.py`
- Character context: `v2/domain_api/semantic_evaluation_context.py`
- Narrator context: `v2/domain_api/narrator_semantic_qa_context.py`
