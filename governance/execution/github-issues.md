# GitHub Issues

When the user asks to **create**, **file**, **open**, or **track** a GitHub Issue (or supplies title/body for that purpose):

- Follow `governance/sources/issue-tracking-workflow.md` **§B.1**–**§B.6**, **§C**, **§D–§G** for: `gh issue create` with **mandatory** `--label` (§C) and **`--repo`** set to `bindings/bindings.toml` `[github].repository`, add to the **bound GitHub Project** in that same `[github]` table, **Project Status** / **Workflow** (§B.3), **non-empty Priority** when the project defines it (§B.5), and full **§B.2** verification (`gh issue view --repo <bindings.github.repository> --json …` **plus** **Priority** proof from **`gh project item-list`** / UI / GraphQL—not **`projectItems` JSON alone**) **before** reporting completion. Do **not** use `gh repo set-default` as durable authority.
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

## Compressed implementation and reporting defaults

When posting implementation notes, completion records, session summaries, or **checkpoint** comments on Issues:

1. **Default:** Prefer **compressed** prose—outcomes, concrete paths, verification commands run, and structured proof blocks where **`issue-tracking-workflow.md` §B.2** applies—instead of full transcript replay.
2. **Expand** when any applies: material ambiguity; architecture or enforcement risk; explicit reader request; escalation packages requiring oversight or **user** decision; mandatory Issue body fields still demand full detail per **`issue-tracking-workflow.md` §D**.

This section **does not** relax: Issue body mandatory sections, safe body mutation rules below, **§B.2** verification gates, **Priority** proof requirements, or governance authority.

**Cursor / agent alignment:** When reporting implementation outcomes **to Issues** (comments, checkpoint blocks), default to the same compressed-vs-expand judgment unless **`governance/execution/cursor-workflow-layer.md`** mandates a structured report shape that already embeds proof blocks.

## Governance posture inheritance (Issue #217; workflow narration compression)

**Declarative posture** means what kinds of actions are permitted for the **active Issue** (its **`Current status:`**, Projects view, named scope)—**not** investigation conclusions, uncertainty, consensus substance, architectural distinctions, §B.2 proof blocks (including Priority proof discipline), **`Current status:` / §H** transitions (and their **§B.5** comments), workflow-weight rationales, or evidence fields.

When posture is **unchanged** and **unambiguous**, carry it forward with **one readable line** (adjust clauses freely; omit inapplicable items; bind to the Issue number):

`Inherited posture (unchanged): …; scoped to #<N>.`

Example clauses operators may concatenate (human language, **no opaque codes**): **investigation-only**; **no implementation** (no RP app / product code edits for this Issue’s tract); **no GitHub mutation** when that constraint is binding; **validation-only**; **deterministic checks only**.

**Invalidation → full explicit restatement of posture plus context** (do not rely on the compact line alone) when **any** holds: ambiguity or disagreement; **`Current status:`** or Projects **Status/Workflow** shifts that change permitted work; material Issue **body** edits to scope/constraints/validation expectations; orchestration overrides; switching the primary tracked Issue without re-recording posture; taking an action that contradicts inherited posture.

**Adjacent issues (non-umbrella coordination):** **#218** (redundant disclaimer compression) and **#219** (report scaffolding) **must remain consistent**—they compress presentation; they **never** waive §B.2/§H or substitute evidence.

## Redundant disclaimer compression (Issue #218; workflow narration compression)

**Declarative spine depends on Issue #217:** Use the **`Inherited posture (unchanged): …; scoped to #<N>.`** line (**Governance posture inheritance** above). That line **carries** overlapping constraints (investigation-only, **no implementation** / **no product code edits**, **no GitHub mutation** when binding, etc.). **Stable issue/project state** (“unchanged”) is ordinarily visible from **`Current status:`** and **bound GitHub Project** fields—restating it verbatim adds no information **when posture already encodes those limits**.

**Trim only:** Extra sentences whose **only** informational content duplicates the posture line or already-visible Issue/Projects truth (examples: repeating “no code changes,” “no GitHub mutation,” “issue unchanged,” “project fields unchanged,” “posture unchanged” in separate sentences). **Never** silently omit material facts or imply work that did **not** happen.

**Forbidden to compress:** **`issue-tracking-workflow.md` §B.2** proof blocks when required; **`Current status:` / §H** transitions and associated **§B.5** comments; mandatory **Evidence / §D** substance; validation criteria prose; consensus records; uncertainty qualification; architectural or **Layer** reasoning; workflow-weight rationale; **§B.2 material Priority** acknowledgment lines when §B.2 treats Priority as material to the outcome.

**Expand / restate disclaimers explicitly** whenever: ambiguity; **material** change to permitted work or Issue/Project/GitHub facts; reader or orchestration asks; escalation/oversight; or compression would conceal whether mutation or advancement occurred.

**Coordination (#219):** Canonical rules in **Report structure compression** below—the posture line stays **early**; **#219** trims **structure/scaffolding**, not disclaimers (**#218**) or declarative posture (**#217**).

## Report structure compression (Issue #219; workflow narration compression)

**Stacking (non-umbrella):** **#217** posture line stays the **first** readable anchor in checkpoints where posture applies. **#218** removes **duplicative sentences** tied to posture. **#219** trims **repeated report skeleton** (headers, intro framing, metadata narration, category setup prose, boilerplate “current understanding” scaffolding, duplicated workflow preamble) **below** posture/disclaimer envelopes.

**Prefer:** Delta-first summaries (what **changed**, decisions, next step); cite **Issue #**, **`Current status:`**, and **`Execution snapshot`/`Execution anchor`** from the Issue body instead of rewriting them as long prose when unchanged.

**Never strip or collapse:** **`issue-tracking-workflow.md` §B.2** proof blocks where required; **`Current status:` / §H** transitions and mandated **§B.5** comments; evidentiary completeness; uncertainty; governance/architecture distinctions; validation criteria citations; consensus text; workflow-weight rationale; **§B.2 material Priority** acknowledgment; substantive governance reasoning or methodology.

**Mandatory expansion (use full scaffolding)** when **any** holds: ambiguity; instability/contradictions; enforcement or architecture-risk decisions; oversight/escalation; multi-issue entanglement without a single clear anchor; explicit reader directive; §D-mandatory narratives for the milestone at hand (see **Compressed implementation and reporting defaults** expansion bullets above).

**Discoverability:** Titles/labels/`Current status:`/`projectItems` authority is unchanged—compression must not hide Issues or mute Project truth.

## Safe issue retrieval and mutation

When retrieving or modifying GitHub Issues, preserve the issue body as authoritative structured state.

### Retrieval discipline

Issue retrieval is infrastructure work, not exploratory reasoning.

When retrieving an issue:

1. Run the intended retrieval command once (for example: `gh issue view <N> --repo <bindings.github.repository> --json ...`).
2. If retrieval fails:

   * run `gh auth status`
   * verify repository context with `gh repo view --repo <bindings.github.repository>` or `git remote -v` (do not rely on bare `gh repo view` when an `upstream` remote exists)
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

### Anchor-first execution context (Issue #145)

After a successful retrieval, when **using** Issue content for ongoing execution (human or agent), read **stable execution cues** before deep thread replay:

When workflow bootstrap rules in `governance/execution/cursor-workflow-layer.md` govern the session, this anchor-first **usage** ordering applies **after** required bootstrap completion (including **SYSTEM UNDERSTANDING REPORT** where applicable).

1. **Execution snapshot** (body / template), if present.
2. **Execution anchor** (permalink, commit hash, scenario id, etc.), if present.
3. Then **`Current status:`**, mandatory **Evidence**, and remaining **`issue-tracking-workflow.md` §D** sections.
4. Then **comments**, prioritizing recent **§B.5** transition and session-boundary comments.

Ordering aligns with **`governance/execution/cursor-workflow-layer.md` → Anchor-first Issue context retrieval**. It does **not** authorize extra retrieval attempts beyond **Retrieval discipline** above.

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
