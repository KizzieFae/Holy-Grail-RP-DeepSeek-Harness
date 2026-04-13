# GitHub Issues

When the user asks to **create**, **file**, **open**, or **track** a GitHub Issue (or supplies title/body for that purpose):

- Follow `governance/rp-app/issue-tracking-workflow.md` **§B.1**–**§B.6**, **§C**, **§D–§G** for: `gh issue create` with **mandatory** `--label` (§C), **RP System Workflow** project add, **Project Status** / **Workflow** (§B.3), **non-empty Priority** when the project defines it (§B.5), and full **§B.2** verification (`gh issue view --json …` **plus** **Priority** proof from **`gh project item-list`** / UI / GraphQL—not **`projectItems` JSON alone**) **before** reporting completion.
- **Do not** report filing complete without **non-empty** `labels` and `projectItems` in the issue-view JSON, without **set Priority** when the field exists, or without **§B.2**-compliant Priority proof (unless §B.1 duplicate/withdrawn exception is documented).
- On **`Current status:`** (**§H**) changes or closure: update Project fields per **§B.3**, add the **execution-stage transition** comment required by **§B.5**, re-run **§B.2**, and reject any report that skips verification.
- **Priority** / **phase-first selection** / **session boundaries** / **handoff invalidity** / **Active Context** rules: **§B.0** and **§B.5** in the same canonical file.

If the user explicitly wants a **draft only**, skip `gh` and provide markdown following **§D–§F** (metadata rules apply when the issue is later created on GitHub).

## Pattern evidence (investigations)

When framing suspected behavior in an Issue body or investigation notes:

- **1 scenario** → **observation** only (not a confirmed pattern).
- **2 scenarios** → **possible** pattern; label it as such until stronger evidence exists.
- **3+ scenarios** with **consistent** behavior across them → **confirmed** pattern for investigation purposes.

**Pattern confirmation** depends on **cross-scenario** consistency, not on repetition within a single long run alone.
