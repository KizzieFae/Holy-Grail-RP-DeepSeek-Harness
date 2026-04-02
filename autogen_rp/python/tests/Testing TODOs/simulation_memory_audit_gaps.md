# Simulation memory testing — audit gap log

Template for observations when running simulations **with** `--audit` (optional). Core tests do **not** require audit; entries here inform a future audit-schema or logging pass.

| Date | Scenario | Gap / observation | Severity (for later) |
|------|----------|-------------------|----------------------|
| 2026-04-01 | `memory_public_propagation` | Cast member (Hannah) had **no character-turn audit files** in session_098; cannot inspect her **character** prompt memory from JSON—only Director/Narrator/other bots. | Medium |
| 2026-04-01 | `memory_private_directed` | Same: no `hannah_*_full.json` in session_099; Hannah prompt memory for codeword **cannot** be audit-verified when she does not take a turn. Director/Narrator payloads still mention present_characters. | Medium |
| 2026-04-01 | (helpers) | `character_prompt_text_from_audit` now uses `rglob("*_full.json")` so nested `round_*` audit files are found. | Resolved (test layer) |

## Notes

- Prompt substring checks belong in `simulation_assertions.assert_prompt_contains_if_audit` (non-gating unless audit dir is provided).
- Prefer logging gaps here over expanding audit payloads during simulation-test rollout.
