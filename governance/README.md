# Governance

Project-owned governance for **Holy Grail RP**: workflow policy, issue tracking, and operating rules.

## Current authorities

| Path | Role |
|------|------|
| `policies/` | Canonical policy corpus (Cursor rules `@`-include these) |
| `rp-app/issue-tracking-workflow.md` | GitHub Issues / Projects workflow |
| `rp-app/workflow-weights.md` | Workflow weight definitions and escalation |
| `rp-app/audit-semantics.md` | Program / system quality audit semantics |

Product architecture and operation: repository root `README.md`, `ARCHITECTURE_OVERVIEW.md`, `AGENTS.md`, and `docs/`.

Program closure: `rp-app/fresh-start-m14-5-program-closure.md` (M14 fresh-start complete).

## Historical workshop / partial registry (not current program-audit authority)

| Path | Role |
|------|------|
| `rp-app/audit-classification-protocol.md` | ACP workshop interchange skeleton (#187) |
| `rp-app/failure-taxonomy-spec-v1.md` | FT1 partial registry / UNKNOWN canon (#186) |
| `rp-app/round-a-*.md` | Round-A workshop facilitation artifacts |

For program/system quality audits, use **`rp-app/audit-semantics.md`**. For RP session-audit procedure, use **`docs/audit-workflows.md`**.

## Separation rules

- **Bindings** → `bindings/bindings.toml` (late-bound repository, upstream, and GitHub Project identity)
- **Governance** → this tree; edit canonical policy here, not inside Cursor stubs
- **Cursor adapters** → repository-root `.cursor/rules/*.mdc` (four-file portable set)
- **Product docs** → repository root and `docs/`

## Related

- `../bindings/bindings.toml` — canonical entrypoints for agents/tools
- `../AGENTS.md` — instruction priority and bootstrap pointers
