# Governance

Project-owned governance: template sync rules, workflow policy extracts, and GitHub Issues / Projects specification.

**Current authorities** for day-to-day work: `AGENTS.md`, `docs/`, and policies in `governance/policies/`.

**Historical program records** in `governance/rp-app/` (including `v2-*` implementation reports and `fresh-start-m14-*` slices) document past execution; they are not required to understand current architecture.

## Layout

| Path | Role |
|------|------|
| `project-sync.toml` | Template sync manifest and safety policies. Binding values live in `bindings/bindings.toml`. |
| `policies/` | Markdown policy corpus included by Cursor `.mdc` stubs via `@governance/policies/...` |
| `rp-app/` | Issue tracking workflow, workflow weights, program execution records |
| `github/` | GitHub-facing asset notes |
| `archive/` | Historical investigation and validation artifacts |

## Separation rules

- **Bindings** → `bindings/bindings.toml` only
- **Governance** → this tree; edit canonical policy here, not inside Cursor stubs
- **Current product docs** → repository root and `docs/` (see `README.md`)

## Holy Grail RP implementation references

| Document | Role |
|----------|------|
| `../README.md` | Product overview and quick start |
| `../ARCHITECTURE_OVERVIEW.md` | Current architecture |
| `../v2/README.md` | Implementation tree (`v2/domain`, `v2/domain_api`, `v2/rp_runtime`) |
| `rp-app/issue-tracking-workflow.md` | GitHub Issues workflow |
| `rp-app/workflow-weights.md` | Workflow weight definitions |

Design and slice implementation history: `rp-app/v2-*.md`, `fresh-start-m14-*.md`.

## Related

- `../bindings/bindings.toml` — canonical entrypoints for agents/tools
- `../AGENTS.md` — instruction priority
