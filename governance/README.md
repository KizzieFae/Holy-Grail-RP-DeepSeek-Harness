# Governance (Issue #45)

This directory holds **project-owned governance**: template sync rules, canonical workflow policy extracts, and the GitHub Issues / Projects specification.

## Layout

| Path | Role |
|------|------|
| `project-sync.toml` | Template sync manifest, allowlists, and safety policies. **No binding values** (repository URLs, pins, etc. stay out of binding keys—use `../bindings/bindings.toml` for late-bound project data). |
| `policies/` | Markdown policy corpus **included** by Cursor `.mdc` stubs under `.cursor/rules/` and `autogen_rp/.cursor/rules/` via `@governance/policies/...`. |
| `rp-app/` | RP-adjacent governance specs split from runtime architecture docs (e.g. issue tracking **§A–§K**). |
| `github/` | Notes on GitHub-facing assets (issue templates); forms remain under `.github/ISSUE_TEMPLATE/` because GitHub requires that path. |

## Separation rules

- **Bindings** → `bindings/bindings.toml` only.
- **Governance** → this tree; edit canonical policy here, not inside template-managed Cursor stubs.
- **Template-managed stubs** → keep only YAML frontmatter plus `@`-includes; no resolved binding placeholders in stubs.

## Related

- `../bindings/bindings.toml` — canonical entrypoints and paths for agents/tools.
- `../autogen_rp/AGENTS.md` — instruction priority and links into this tree.
