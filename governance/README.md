# Governance (Issue #45)

This directory holds **project-owned governance**: template sync rules, canonical workflow policy extracts, and the GitHub Issues / Projects specification.

## Layout

| Path | Role |
|------|------|
| `project-sync.toml` | Template sync manifest, allowlists, and safety policies. **No binding values** (repository URLs, pins, etc. stay out of binding keys—use `../bindings/bindings.toml` for late-bound project data). |
| `policies/` | Markdown policy corpus **included** by Cursor `.mdc` stubs under `.cursor/rules/` and `autogen_rp/.cursor/rules/` via `@governance/policies/...`. |
| `rp-app/` | RP-adjacent governance specs split from runtime architecture docs (e.g. issue tracking **§A–§K**, **V2 DSH re-platforming** authority and mapping). |
| `github/` | Notes on GitHub-facing assets (issue templates); forms remain under `.github/ISSUE_TEMPLATE/` because GitHub requires that path. |

## Separation rules

- **Bindings** → `bindings/bindings.toml` only.
- **Governance** → this tree; edit canonical policy here, not inside template-managed Cursor stubs.
- **Template-managed stubs** → keep only YAML frontmatter plus `@`-includes; no resolved binding placeholders in stubs.

## V2 DeepSeek Harness re-platforming (harness repo)

| Document | Role |
|----------|------|
| `rp-app/v2-dsh-replatforming-authority.md` | Governing principles for behavioral-preservation re-platform onto DSH |
| `rp-app/v2-behavioral-evidence-inventory.md` | Existing audits, tests, and artifacts by capability |
| `rp-app/v2-capability-dsh-mapping.md` | Capability → DSH mapping and proposed target architecture |
| `rp-app/v2-runtime-boundary-decision.md` | **V2 runtime boundary & session topology decision** (full-weight architecture proposal) |
| `rp-app/v2-boundary-prototype.md` | **V2 boundary prototype implementation report** (narrow vertical slice) |
| `rp-app/v2-director-character-orchestration.md` | **V2 Director + Character orchestration slice** (multi-role proof) |
| `rp-app/v2-narrator-orchestration.md` | **V2 Narrator orchestration slice** (three-role basic round) |
| `../CHECKPOINT_BASELINE_DSH.md` | Baseline checkpoint report (environment, smoke checks, next slice) |
| `../v2/README.md` | V2 implementation tree (Domain API + RP runtime prototype) |

## Related

- `../bindings/bindings.toml` — canonical entrypoints and paths for agents/tools.
- `../autogen_rp/AGENTS.md` — instruction priority and links into this tree.
