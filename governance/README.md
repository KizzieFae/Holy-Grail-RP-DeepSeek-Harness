# Governance

Project-owned governance for **Holy Grail RP**: workflow policy, issue tracking, and operating rules.

## Current authorities

| Path | Role |
|------|------|
| `policies/` | Canonical policy corpus (Cursor rules `@`-include these) |
| `rp-app/issue-tracking-workflow.md` | GitHub Issues / Projects workflow |
| `rp-app/workflow-weights.md` | Workflow weight definitions and escalation |
| `rp-app/audit-classification-protocol.md` | Audit classification rules |
| `rp-app/failure-taxonomy-spec-v1.md` | Failure taxonomy reference |
| `rp-app/round-a-*.md` | Round-A workflow artifacts |

Product architecture and operation: repository root `README.md`, `ARCHITECTURE_OVERVIEW.md`, `AGENTS.md`, and `docs/`.

Program closure: `rp-app/fresh-start-m14-5-program-closure.md` (M14 fresh-start complete).

## Separation rules

- **Bindings** → `bindings/bindings.toml`
- **Governance** → this tree; edit canonical policy here, not inside Cursor stubs
- **Product docs** → repository root and `docs/`

## Related

- `../bindings/bindings.toml` — canonical entrypoints for agents/tools
- `../AGENTS.md` — instruction priority and bootstrap pointers
