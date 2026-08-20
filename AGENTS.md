# AGENTS.md

Repo-level source of truth for AI assistants working in **Holy Grail RP**.

Use this document together with `docs/` before multi-file, architectural, workflow, or audit-sensitive changes.

## Instruction priority

1. Direct user request
2. This file
3. Shared repo docs in `docs/`
4. Package-specific docs such as `tools/investigation/README.md`
5. Tool-specific features (Windsurf workflows, Cursor rules)

Do not rely on tool memory as the only source of important project behavior.

## Repo working rules

- Preserve existing architecture and patterns unless the user explicitly asks for a redesign.
- Prefer small, reviewable diffs over broad rewrites.
- Focus on files relevant to the task.
- Do not change unrelated code just because it is nearby.
- Prefer extending existing modules and workflows before inventing new ones.
- Keep important guidance in repo files, not only in tool-specific settings.
- If code behavior, architecture constraints, or test expectations change, update the relevant docs.
- When the user asks to **file** a GitHub Issue (not draft-only), follow `governance/sources/issue-tracking-workflow.md` **§B.1**–**§B.6** and **§C** (`gh issue create` from the repo git root with **`--repo`** set to `bindings/bindings.toml` `[github].repository`; **mandatory** labels; add to the **bound GitHub Project** in that same `[github]` table; **Status** / **Workflow** fields per **§B.3**; **non-empty Priority** (typically **P3** until triaged) when the project defines it (**§B.5**); **§B.2** verification before reporting done). Issue body template remains **§D–§F**. Do **not** use `gh repo set-default` as durable authority.
- For **issue-management** tasks (create, transition **§H**, close): completion reports must include **`gh issue view --repo <bindings.github.repository> --json number,state,labels,projectItems`** **and** **§B.2** proof of **Priority** from **`gh project item-list`** / UI / GraphQL (not **`projectItems` JSON alone**), plus **§B.3** alignment and, when **§B.2** applies, the **one-line** material **Priority** acknowledgment — see **`governance/sources/issue-tracking-workflow.md` §B.2**. Missing metadata ⇒ incomplete; do not report completion.
- Do not overwrite environment or secret files without explicit user confirmation.
- **Workflow weights:** GPT **assigns** workflow weight before substantive Issue work; implementation AI (**Cursor**) inherits **assigned**/**effective** weight and must not reinterpret rigor independently (**`governance/sources/gpt-workflow-instruction-set.md`**). Canonical **`light` / `standard` / `full`** and escalation triggers — **`governance/sources/workflow-weights.md`** only. **Routine filing assigned default:** **`standard`**. Weight-aware bootstrap + anchor-first retrieval — **`governance/execution/cursor-workflow-layer.md`**; authoritative profile read lists — **`docs/issue-bootstrap-profiles.md`**. Consensus recording shapes — **`governance/sources/issue-tracking-workflow.md` §B.0.1**.

## Governance layout

- **Bindings** (late-bound project values only): `bindings/bindings.toml`
- **Template sync manifest** (no binding payloads): `governance/project-sync.toml`
- **Governance-AI upload corpus:** `governance/sources/` — minimum sufficient standing sources for Governance AI (7 files; see `governance/README.md`). **Not** uploaded by humans for normal Governance operation: this file (`AGENTS.md`).
- **Implementation execution policies:** `governance/execution/` — Cursor `@`-included execution policies
- **Historical / supporting records:** `governance/records/` — not current Governance-AI authority

**New governance documents:** classify by authority function per `governance/README.md` → **Creating governance documents** (sources vs execution vs records vs system/bootstrap). Do not place new canon under retired `governance/policies/` or `governance/rp-app/` paths.

Repository-root `.cursor/rules/*.mdc` are thin wrappers that `@`-include (or route to) files under `governance/`. The portable four-file adapter set is `2-ai-system-start.mdc`, `project-behavior.mdc`, `github-issues.mdc`, and `github-project-usage.mdc`.

## Where to start

**Governance standing sources (`governance/sources/` — upload corpus):**

- [governance/sources/holy-grail-prd.md](./governance/sources/holy-grail-prd.md)
- [governance/sources/architecture-overview.md](./governance/sources/architecture-overview.md)

**Implementation contracts and navigation (repository root):**

- [MODULE_INDEX.md](./MODULE_INDEX.md)
- [AUTHORED_SOURCE_CONTRACT.md](./AUTHORED_SOURCE_CONTRACT.md)
- [DEBUGGING_GUIDE.md](./DEBUGGING_GUIDE.md)
- [PACKET_CONTRACTS.md](./PACKET_CONTRACTS.md)
- [GLOSSARY.md](./GLOSSARY.md)
- [SCENARIO_VALIDATION_FRAMEWORK.md](./SCENARIO_VALIDATION_FRAMEWORK.md)

**Shared technical docs (`docs/`):**

- [docs/repo-map.md](./docs/repo-map.md) — repository structure
- [docs/rp-data-layout.md](./docs/rp-data-layout.md) — on-disk data
- [docs/architecture.md](./docs/architecture.md) — integration guardrails
- [docs/testing.md](./docs/testing.md) — pytest and validation commands
- [governance/sources/audit-semantics.md](./governance/sources/audit-semantics.md) — program audit semantics
- [docs/audit-workflows.md](./docs/audit-workflows.md) — RP session-audit procedure
- [docs/scene-grounding-layer.md](./docs/scene-grounding-layer.md) — Scene Grounding MVP

**Implementation tree:**

- [v2/README.md](./v2/README.md) — domain, Domain Host, RP runtime layout

## Active project areas

Production code lives under **`v2/`**:

| Area | Path |
|------|------|
| Domain library | `v2/domain/modules/` |
| Domain Host | `v2/domain_api/` |
| Domain tests | `v2/domain/tests/` |
| RP runtime (DSH) | `v2/rp_runtime/` |
| Presentation UI | `v2/ui/` |
| Integration tests | `v2/tests/` |
| Canonical data | `data/` (`HG_DATA_DIR`) |

Node calls the Domain Host over HTTP. Python does not call DSH. UI is a presentation client of the Node application API. Topology and run commands: [v2/README.md](./v2/README.md). Symptom → owner: [MODULE_INDEX.md](./MODULE_INDEX.md).

When a task touches domain behavior, also read:

- [MODULE_INDEX.md](./MODULE_INDEX.md) — symptom → module map
- For **knowledge leaks, whispers, or per-character prompt differences:** `v2/domain/modules/perception_audibility.py`
- [governance/sources/holy-grail-prd.md](./governance/sources/holy-grail-prd.md) — product intent
- [governance/sources/architecture-overview.md](./governance/sources/architecture-overview.md) — standing architectural invariants (progression advisory, Scene Grounding, continuity authority). Advisory-style prompt text must not write continuity or `CharacterState`.

**Offline tooling:** `tools/investigation/`, `tools/maintenance/` — see each README.

**Historical program records** under `governance/records/` document past slices; consult them for history, not as the primary description of current architecture.

## Tool-specific compatibility

### Windsurf

Windsurf automation may exist under `.windsurf/`. Keep useful IDE automation; do not let it become the only source of critical rules.

### Cursor

Cursor uses `.cursor/rules/` as a routing layer into this file, `docs/`, and `governance/`. Avoid duplicating large rule blocks in Cursor-only files.

## Safe switching rule

When switching between IDEs:

- treat repo files as authoritative
- re-read this file and relevant docs for the task
- do not assume tool memory contains the latest architecture
- keep tool-specific rules thin and aligned to shared docs
