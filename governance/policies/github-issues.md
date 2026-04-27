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

## Safe issue retrieval and mutation

When retrieving or modifying GitHub Issues, preserve the issue body as authoritative structured state.

### Retrieval discipline

Issue retrieval is infrastructure work, not exploratory reasoning.

When retrieving an issue:

1. Run the intended retrieval command once (for example: `gh issue view <N> --json ...`).
2. If retrieval fails:

   * run `gh auth status`
   * verify repository context with gh repo view or git remote -v
3. Retry retrieval once.

If retrieval still fails:

* stop immediately
* report the exact failure
* do not continue with fallback retrieval strategies unless explicitly instructed by the user

Prohibited recovery behavior:

* switching to alternate tools or APIs
* browser/manual scraping
* reconstructing issue content from memory, logs, or partial output
* speculative repair outside authentication or repository-context verification

Issue retrieval must remain bounded and deterministic.

### Safe issue body mutation

GitHub Issue bodies are authoritative structured workflow state and must be edited with minimal mutation scope.

Before any issue body edit:

1. Retrieve the full current body.
2. Persist the retrieved body to a temporary UTF-8 encoded markdown file.
3. Apply only the intended scoped edit to that file.
4. Update the issue using:

`gh issue edit <N> --body-file <file>`

Do not mutate issue bodies through:

* inline shell string replacement
* PowerShell pipeline substitution
* partial-body reconstruction
* ad-hoc body rebuilding from copied fragments

Mutation requirements:

* preserve markdown structure
* preserve code fences
* preserve line ordering
* preserve Unicode punctuation
* preserve line endings where possible
* preserve untouched sections exactly

After mutation:

1. Re-retrieve the issue body.
2. Verify the intended edit landed correctly.
3. Verify no unrelated body content changed.

If unrelated content changed or formatting corruption is detected:

* stop immediately
* restore from the last known-good retrieved body
* report the corruption before proceeding

Never perform reconstructive repair of issue bodies unless explicitly directed by the user.
