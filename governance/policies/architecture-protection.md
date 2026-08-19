# Architecture Protection

Before making architecture-sensitive changes, read:

- `ARCHITECTURE_OVERVIEW.md`
- `docs/architecture.md`
- `v2/README.md` when the task touches Domain Host or RP runtime layout

Apply these constraints:

- do not move continuity, orchestration, validation, and rendering responsibilities into the wrong layer
- do not treat Director prompt changes as the default fix for RP runtime problems
- keep the Domain Host (`v2/domain_api/`) as the composition boundary for domain truth; keep the UI (`v2/ui/`) as a presentation client unless the task explicitly says otherwise
- preserve bounded-context strategies and avoid reintroducing unbounded hidden chat accumulation
- prefer the smallest fix at the correct layer rather than adding a parallel subsystem

If a change affects a central abstraction, identify the likely downstream consumers before editing.
