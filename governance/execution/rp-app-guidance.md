# RP App Guidance

When a task touches the RP runtime / domain, read:

- `MODULE_INDEX.md` (repo root: symptom → module map)
- `docs/architecture.md`
- `governance/sources/architecture-overview.md`
- `v2/README.md`
- `governance/sources/audit-semantics.md` (program audit semantics, when conducting program audits)
- `docs/audit-workflows.md` (RP session-audit **procedure** only; not `#59` signal inventory)

Important RP app rules:

- preserve the Director + Narrator + continuity-manager architecture
- treat `must_remain` as structural presence, not a requirement to speak every beat
- diagnose continuity and orchestration layers before changing Director prompts
- prefer converting repeated audit findings into focused regression tests
- keep fixes minimal and runtime-layer appropriate

For session audits, use the artifact order in `docs/audit-workflows.md`.
