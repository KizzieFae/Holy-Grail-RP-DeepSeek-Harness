# Issue tracking and investigation workflow

**Authority:** Canonical governance copy for GitHub Issues, Projects metadata, and body contract (**§A–§K**), relocated from `autogen_rp/python/rp_app/ARCHITECTURE.md` per Issue #45 Stage 3. **Runtime Director / RP architecture** remains in `autogen_rp/python/rp_app/ARCHITECTURE.md` above the stub section there.

**Maintenance:** Edit this file when changing workflow rules; keep the stub in `ARCHITECTURE.md` aligned.

### A. System of record

- **GitHub Issues** are the system of record for bugs, quality/design work, simulation anomalies, investigations, refactors, and validation follow-up.
- **Project files** (for example `RP_SETUP_TODO.md` at `autogen_rp/python/RP_SETUP_TODO.md`) remain responsible for roadmap, phase structure, architecture notes, and milestones—not for live issue logs.
- **Do not** duplicate detailed issue logs in project files.
- **Reference markdown** in-repo may capture background and acceptance criteria but is **reference-only** for task tracking. **GitHub Issues** hold status, discussion, and closure.

**Non-negotiable tracking rules**

1. GitHub Issues are the **single** source of truth for tracked work.
2. Documentation is **reference only**, not a substitute for Issues.
3. **No issue without evidence** (mandatory fields in **§D**).
4. **One primary Layer** per issue (**§F**).
5. **No implementation before consensus** (`Current status` must reach **`consensus_reached`** before code changes for that issue, except duplicate/withdrawn intake—**§H**).
6. **Quality** and **design_gap** items are **not** silently filed as **bug**; **Type** follows **§E** (PRD authority).
7. **Pattern status** is always explicit (**§I**).
8. **Documentation reviewed and updated** where contracts or behavior changed **before** terminal closure (**§D** checklist).
9. **GitHub Project metadata** (**§B.1**–**§B.5**, **§C**) — Every **tracked** issue on the Holy Grail RP GitHub repo must have **labels**, **RP System Workflow** project membership, and **Project Status** / **Workflow** fields kept in sync with **`Current status:`** (**§H**), except **duplicate** / **withdrawn** intake documented in a comment (**§B.1**). When **Priority** exists on the project (**§B.5**), set and maintain it for triage; it does **not** replace **`Current status:`** or **Workflow**.

### A.1 Audit-driven workflow (reference)

Simulation and audit logging produce JSON under `autogen_rp/python/rp_app/data/rp_audits/`. That output **requires interpretation** before work is scheduled; artifacts are **not** a substitute for filed issues. Pipeline: **Simulation → Audit → Interpretation → Issue detection → Classification → Tracking → Fix → Re-test.** Roles, **Type** / **Layer** / **Pattern status**, evidence standards, and heuristic caveats are in **`autogen_rp/python/rp_app/AUDIT_DOCUMENTATION.md`** → **Audit interpretation and issue tracking**. Deterministic audit layers (v1/v2) and LLM validation logs are **advisory** unless explicitly documented as runtime gates.

### B. Standard workflow

Record progress in the Issue (description updates, comments, checklists). **Status** line must follow **§H**.

### B.0 Terminology (execution stage vs phase-first selection)

> The term "phase" in "phase-first selection" refers to external batching of work and must not be confused with execution stages represented by `Current status` and the Workflow field.

- **Execution stage** — The lifecycle position in **§H** (`open`, `investigating`, …), reflected in the issue body as **`Current status:`** and on **RP System Workflow** as **Project Status** and **Workflow** per **§B.3**. Use **execution stage** (not “selection phase”) when referring to **§H** or that mapping.
- **Phase-first selection** — External operator/AI behavior only: choose a work batch → filter issues → order by **Priority** within that batch (**§B.5**). It is **not** stored as a separate “phase” field on the issue or project and does **not** redefine **Workflow** or **`Current status:`**.

1. **Observation** — Unexpected behavior in runs, tests, or review. Open or update an Issue when work may outlive the session. Create on GitHub via **§B.1** (CLI) or the web UI using **`.github/ISSUE_TEMPLATE/holy_grail_rp.yml`** (repository root).
2. **Investigation** — Gather evidence; set **`Current status: investigating`**. Document ruled-out **Layers** in comments.
3. **Consensus** — Agree fix / defer / monitor / won’t fix; align on **Layer** and scope. Set **`Current status: consensus_reached`** before implementation.
4. **Implementation** — Land changes; reference the Issue in commits (`#123`). Set **`Current status: implemented`** when merged or landed.
5. **Validation** — Tests, scenario reruns, checklists in the Issue. Set **`Current status: validated`** when criteria pass.
6. **Closure** — Set terminal **§H** status; GitHub closed when appropriate; align **Project** fields (**§B.3**) and run **§B.2**. Complete **§D** documentation checklist before **`closed`**.

### B.1 Filing issues via GitHub CLI (humans and agents)

Use when creating the Issue on GitHub from a terminal (e.g. agent asked to *file* / *create* / *open* / *track*, not draft-only).

**Exception — draft-only or duplicate/withdrawn intake:** If the user asked **draft only**, skip `gh` and provide markdown per **§D–§F**. For **duplicate** or **withdrawn** filings closed per **§H** exception, metadata requirements may be abbreviated if documented in a **comment** (still prefer full metadata when practical).

1. Run commands from the **git root** (directory with `.git` whose `origin` hosts Issues).
2. Run `gh auth status`. **`gh project`** subcommands need a token with **`project`** scope; if Projects commands fail, use the GitHub web UI for project steps and still run verification (**§B.2**). If `gh` is missing entirely, provide full body per **§D** for paste into the web UI.
3. Create the issue with **mandatory labels** (**§C**), not optional:  
   `gh issue create --title "..." --body-file path/to/body.md` with one or more `--label "<name>"` flags (repeat per label).
4. Add the issue to the **RP System Workflow** project (owner/org that hosts the repo; discover number via `gh project list`):  
   `gh project item-add <PROJECT_NUMBER> --owner <OWNER> --url <ISSUE_URL>`  
   Use the URL returned from step 3.
5. Set **initial Project fields** to match **`Current status:`** in **body.md** (**§B.3** default row for new issues — typically **Status** = **Todo**, **Workflow** = **Ready** when **`Current status: open`**). When the project defines **Priority** (**§B.5**), set an initial value (typically **P3** until triaged). Use `gh project field-list` / `gh project item-edit` (single-select field and option IDs), or set fields in the **Projects** UI, then verify (**§B.2**).
6. **Verify** before reporting completion (**§B.2**). **Do not** treat filing as complete without a passing verification.

Unless the user asked **draft only**, **completion** means: the Issue **exists** on GitHub **and** **§B.2** passes **and** **§B.3** is satisfied for the issue’s current **`Current status:`**.

### B.2 Verification gate (mandatory)

After **create** or any **metadata-affecting** update (labels, project membership, **§H** transition, closure), the actor **must** run a **deterministic check** and retain the output (paste into the Issue comment or session log as appropriate):

```bash
gh issue view <N> --json number,state,labels,projectItems
```

**Pass criteria (minimum):**

- **`labels`**: JSON array **non-empty** (unless **§B.1** exception applies and is documented).
- **`projectItems`**: JSON array **non-empty**, with an item for **RP System Workflow** (title/name as shown by `gh`).
- **Project Status** and **Workflow**: Values must **not contradict** **`Current status:`** per **§B.3** (if JSON does not expose a field, confirm via **`gh project item-list`** / project board / `gh project item-edit` dry documentation and state the two field values explicitly in the completion note).
- **Priority** (when the project defines **Priority**, **§B.5**): Confirm the value via the **Projects** UI or a GraphQL `node` query on the project item—`gh issue view --json projectItems` may omit **Priority**; when material to the task, state **Priority** explicitly in the completion note.

**Completion is invalid** without this verification for tracked issues. Narrative-only confirmation (“issue filed”) is **not** sufficient.

### B.3 Synchronization — `Current status:` (**§H**) vs GitHub Project fields (execution stages)

**Two surfaces:** **`Current status:`** in the **issue body** (**§H**) is authoritative for **issue text** and **execution-stage** transitions. **Project Status** and **Workflow** on **RP System Workflow** are authoritative for **board execution state** for those stages. They **must not contradict**.

**On create:** Align initial Project fields with the body’s **`Current status:`** (usually **`open`** → **Status** = **Todo**, **Workflow** = **Ready**).

**On execution-stage transition:** Whenever **`Current status:`** is edited (including via Issue description update or comment checklist), **update Project fields** to the matching row **before** reporting that transition complete:

| `Current status:` (**§H**) | Project **Status** (typical) | Project **Workflow** (typical) |
|----------------------------|------------------------------|--------------------------------|
| `open` | Todo | Ready |
| `investigating` | In Progress | Investigating |
| `consensus_reached` | In Progress | Awaiting consensus |
| `implemented` | In Progress | Implemented |
| `validated` | In Progress | Validating |
| `closed` | Done | Done |
| `monitor` | Done | Monitor |
| `wont_fix` | Done | Won't fix |

If the board uses different option labels, **map by intent** (investigation vs consensus vs implementation vs validation vs terminal) and document the mapping once in a **Project** wiki or comment on **#35**—do not leave issues on **Todo** while **`Current status:`** reads **`validated`**.

**On closure:** When moving to **`closed`** (or **`monitor`** / **`wont_fix`**), set **Workflow** to the terminal row above, **close** the GitHub Issue when appropriate, and run **§B.2** again so **`projectItems`** and **labels** remain consistent.

### B.4 Rejection rule (metadata)

- **Missing** required **labels**, **project membership**, or **Project** **Status** / **Workflow** alignment with **§B.3** → the **task is incomplete**.
- **No agent** (implementation or review) may report **completion** of filing, transition, or closure **without** passing **§B.2** and explicit confirmation that **§B.3** holds.
- The **review** role **must reject** any completion report that omits verification output or shows empty **`labels`** / **`projectItems`** for a tracked issue.
- The **review** role **must reject** workflows that show: missing **execution-stage** transition comment when **`Current status:`** changed (**§B.5**); missing **session / chat boundary** comment when a session ended or handoff occurred without an update (**§B.5**); **Active Context** or other chat-only text that **contradicts** the Issue body + comments + Project fields; use of **Priority** to skip **phase-first selection** batching rules; or **handoff** content that introduces facts absent from the Issue thread (**§B.5**).

### B.5 Phase-first selection, Priority, execution-stage comments, session boundaries, handoffs

1. **Phase-first selection (process rule)** — External to GitHub fields: the operator/AI chooses a work batch, filters issues, then orders by **Priority** **inside that batch only**. **Priority** must **not** override or replace this batching step (no “priority-first” shortcut around selection). This rule does **not** change **§B.3**: **Workflow** and **`Current status:`** still represent **execution stages** only.

2. **Priority project field** — On **RP System Workflow**, **Priority** is a single-select when enabled: **P0** (do now), **P1** (next), **P2** (later), **P3** (backlog). It applies **only** within the current **phase-first selection** batch for ordering; it does **not** encode an execution stage and must **not** be treated as a substitute for **`Current status:`** or **Workflow**.

3. **Execution-stage transition discipline** — On every **`Current status:`** (**§H**) change: (a) update **Project Status** and **Workflow** to the **§B.3** row **before** calling the transition done; (b) add an **Issue comment** recording: what completed in the prior execution stage, the resulting determination, and the **next execution stage** intended.

4. **Session / chat boundary** — Before ending a work session, switching chats, or handing off to another AI: add an **Issue comment** with: current **execution stage** (and current **`Current status:`**), work completed this session, what remains, and the **next concrete step**. Chat-local **Active Context** (see `governance/policies/project-behavior-holy-grail.md`) must be a **derived summary** of the Issue + comments + Project fields, written **after** this comment when starting a new chat—not a replacement for it.

5. **Handoff prompts (non-authoritative)** — Delegation may still use handoff prompts, but they are **transport only**. **Hard rule:** If information exists in a handoff prompt but not in the issue body or comments, the workflow is invalid until reconciled (copy authoritative facts into the Issue thread first).

### C. Standard GitHub labels (mandatory adjunct)

Labels do **not** replace **Type** or **Layer** in the body. For **Holy Grail RP tracked issues**, applying **at least one** label from the **default set** (or an established **`type:*`** / **`documentation`** / **`infrastructure`** label that matches **Type** / workstream) is **mandatory** on **create**, unless **§B.1** exception applies.

**Default set** (do not expand without reason): `bug`, `improvement`, `research`, `tech-debt`, `blocked`. Additional common labels: `validation`, `docs`, `needs-reproduction`, `documentation`, `infrastructure`, **`maintenance`** (optional scope tag on **`quality`** items—not a **Type**), and **`type:bug`** / **`type:quality`** / **`type:design_gap`** when used by the repository.

**Alignment:** Prefer a **Type**-aligned label (e.g. **`type:design_gap`** for **design_gap**) plus scope where useful (**`documentation`**, **`infrastructure`**, **`bug`**, **`maintenance`** on **quality** when appropriate, etc.).

### D. Issue body template (canonical contract)

Use these sections **in order** (copy into `body.md` or the root issue form).

- **Summary** — One short paragraph.
- **Type** — One of **`bug`** | **`quality`** | **`design_gap`** (definitions **§E**).
- **Layer** — One primary value from **§F** (body field, not a label). If **`other`**, include **justification** and **intended final Layer** per **§F**.
- **Pattern status** — One of **`single_instance`** | **`potential_pattern`** | **`confirmed_pattern`** (rules **§I**).
- **Current status** — Exactly one value from **§H** on a single line: `Current status: <value>`.
- **Evidence (mandatory)** — **Scenario id**; **audit session path** (repo-relative or unambiguous); **turn index** or `n/a` with reason.
- **Evidence (preferred)** — Structured move excerpt; consequence output if applicable; continuity snapshot excerpt if applicable.
- **Expected behavior** — What should happen (cite PRD/architecture when **Type** is **bug** or **design_gap**).
- **Observed behavior** — What happened (concrete fields/paths).
- **Deterministic reasoning** — Why observed violates expected (rules, fields, code path—no hand-waving).
- **System impact** — Operator/user-visible effect.
- **Constraints** — e.g. no LLM-only fix; no prompt workaround; no weakening enforcement; continuity authoritative—or `none`.
- **Affected modules** — Concrete paths (e.g. `autogen_rp/python/rp_app/continuity_consequence_classifier.py`).
- **Validation criteria** — Tests / scenario ids / audit checks required to reach **`validated`**.
- **Documentation** — Before terminal closure: `[ ]` Documentation reviewed and updated where behavior or contracts changed (list files in a closing comment).

Optional: **Severity** (`high` / `medium` / `low`); **Next step** (owner / action).

### E. Type (classification; PRD authority)

**Authority:** [Holy Grail PRD.md](../../Holy%20Grail%20PRD.md) (repository root) and [ARCHITECTURE_OVERVIEW.md](../../ARCHITECTURE_OVERVIEW.md) / `autogen_rp/python/rp_app/ARCHITECTURE.md` for runtime architecture expectations. If PRD/architecture are silent, prefer **`quality`** or **`design_gap`** until the spec is updated—not **`bug`**.

| Type | Definition |
|------|------------|
| **bug** | Behavior **violates an explicit** must/should/owns expectation in PRD or linked architecture docs. |
| **quality** | Undesirable but **not** specified as incorrect in those documents (calibration, UX, heuristic noise). |
| **design_gap** | Required capability **missing**, or **implied by stated design** but not implemented. |

### F. Layer (primary; mutually exclusive)

Record **one** **Layer** in the issue body. Snake_case identifiers only.

**Boundary (orchestration vs response_validation)**

- If the bug affects **which actor is selected or allowed to act** → **`orchestration`**.
- If the bug affects **validity of a produced character move or narrator structured output** → **`response_validation`** (not “who speaks next”).

#### `consequence_classification`

Deterministic mapping from a **validated structured character move** (and closely coupled exit signals) to **consequence labels** consumed downstream. Does **not** own authoritative state mutation.

**Belongs:** Wrong/missing tags vs structured move; classifier/dedupe logic; `continuity_consequence_classifier.py`; `scene_exit_detection.py` when the fault is **classification from the move**, not applying state.

**Does not belong:** Wrong issues/events/scene after tags are correct → **`continuity_state`**. Wrong Q interpretation → **`progression`**. Wrong prompt projection → **`grounding`**, **`perception`**, **`memory`**, or **`rendering`** as appropriate.

**Examples:** False REFUSAL; missed REPOSITIONING; duplicate classifier emissions for one turn.

#### `continuity_state`

Authoritative **runtime narrative state** after a turn (events, issues, scene, interpretations, knowledge) in **`ContinuityManager`** and continuity helpers.

**Belongs:** Wrong committed state given correct inputs/tags; issue lifecycle; `continuity_manager.py`, `continuity_*_helpers.py`, `turn_runner_updates.py` when **committed truth** is wrong.

**Does not belong:** Tags wrong before commit → **`consequence_classification`**. Next actor wrong → **`orchestration`**. Move invalid → **`response_validation`**.

**Examples:** Exit not applied offstage; stale active issues; wrong event from correct consequences.

#### `progression`

Deterministic **stall / advisory / enforcement** reading continuity-emitted signals. Does **not** author consequences or continuity truth.

**Belongs:** Q1–Q4, retries, gates, `stall_score`, `progression_advisory`, beat-shift enforcement hooks.

**Does not belong:** Wrong consequence strings → **`consequence_classification`**. Wrong continuity issues → **`continuity_state`**.

**Examples:** Retry when Q satisfied; wrong qualification; `stall_score` inconsistent with committed scene signals.

#### `orchestration`

Turn flow: **who may act next**—address, continuation, spotlight, forced speaker, Director merge, **selection-path** validation whose purpose is **choosing or allowing the next actor** (including `response_validation_selection.py` when the defect is **selection outcome or eligibility**).

**Belongs:** Wrong `next_actor` / pool / continuation; `orchestration_helpers.py`, `app_turn_director.py`, `semantic_validation.py` for selection reconciliation.

**Does not belong:** Character/narrator **payload** validity (parse, presence, duplicate dialogue) → **`response_validation`**.

**Examples:** Ineligible actor selected; addressee skipped against rules; selector decisions contradict policy.

#### `response_validation`

Validation of **character** and **narrator** **structured outputs**—whether a **produced move or narrator payload** is **valid** under rules—**excluding** the Director **selection** pipeline (**`orchestration`** owns that).

**Belongs:** `response_validation_parsing.py`, `response_validation_content.py`, `response_validation_presence.py`, `response_validation_drift.py` (and peers) for character/narrator validation.

**Does not belong:** Which actor Director picked → **`orchestration`**. Classifier tags → **`consequence_classification`**. Grounding text wrong with valid move → **`grounding`**.

**Examples:** False must_remain; duplicate-line false positive; malformed move rejection when schema should pass.

#### `grounding`

Scene **grounding** read model: settled facts, binding constraints, **projection into prompts** (non-authoritative vs continuity).

**Belongs:** `scene_grounding.py`; grounding-related prompt assembly when facts/bindings disagree with continuity snapshot.

**Does not belong:** Continuity never updated truth → **`continuity_state`**. Dialogue visibility → **`perception`**.

**Examples:** Missing BINDING CONSTRAINTS; stale SETTLED SCENE FACTS vs continuity.

#### `perception`

**Knowledge boundaries** for prompt assembly: who may see others’ dialogue / rendered text / filtered tails (`perception_audibility` and call sites).

**Belongs:** Leaks or incorrect withholding in per-character prompts.

**Does not belong:** Wrong continuity knowledge records → **`continuity_state`**. Retrieval bundle → **`memory`**.

**Examples:** Whisper visible to wrong character; offstage sees full dialogue against rules.

#### `memory`

Episodic compile/select/cache and **retrieved context** merge into bundles and prompt sections (non-authoritative vs continuity).

**Belongs:** `memory_layer/`, `episodic_memory_*.py`, merge/format of `RetrievedContextBundle` given continuity inputs.

**Does not belong:** Continuity wrote wrong events → **`continuity_state`**. Perception gating → **`perception`**.

**Examples:** Empty episodic when events exist; wrong merge caps/order; retrieval summary inconsistent with bundle passed to prompts.

#### `rendering`

Narrator / UI **presentation** path; dialogue verbatim contract in rendered output.

**Belongs:** `app_turn_rendering.py`, narrator presentation bugs.

**Does not belong:** Move validation → **`response_validation`**. Committed state wrong → **`continuity_state`**. Audit file shape → **`audit_simulation`**.

**Examples:** Paraphrased dialogue in chat; render ordering bug.

#### `audit_simulation`

Observability and **behavioral harness**: headless runs, audit writers, metrics / `structured_eval` when the fault is **instrumentation or driver**, not runtime truth.

**Belongs:** Missing/wrong audit fields; broken `--audit`; CLI/scenario driver bugs.

**Does not belong:** Runtime wrong with correct audits → owning **Layer** above.

**Examples:** `_audit_summary.json` missing promised blocks; misaligned turn indices in artifacts.

#### `application_infrastructure`

Cross-cutting: Streamlit shell, session plumbing, encoding/IO, env/deps, **authored asset loaders** when the bug is **mechanical** (path/schema load), not wrong narrative semantics after load.

**Belongs:** `app.py` wiring; mojibake; broken data paths.

**Does not belong:** Wrong scene semantics after clean load → domain **Layer**. Audit format → **`audit_simulation`**.

**Examples:** Session key loss on rerun; bad encoding in saved JSON.

#### `other`

Allowed **only** when: **(1)** non-runtime (process/tooling/repo workflow outside the Layers above), **or** **(2)** **`Current status` is `investigating`** and the body includes a **target Layer hypothesis** (intended final Layer).

**Always required for `other`:** **justification** (why no named runtime Layer applies yet, or why the issue is non-runtime) and **intended final Layer** (for triage: where the issue should land after investigation). **`other`** is **not** terminal for runtime bugs once **`consensus_reached`**—reclassify to a concrete **Layer**.

**Tie-break order (deterministic):** wrong tags from move → **`consequence_classification`**; wrong state given correct tags → **`continuity_state`**; wrong gate/retry from metadata → **`progression`**; wrong next actor → **`orchestration`**; wrong move/narrator payload validity → **`response_validation`**; wrong facts/bindings in prompts, continuity correct → **`grounding`**; wrong visibility of others’ text → **`perception`**; wrong episodic/retrieved bundle → **`memory`**; wrong final prose path → **`rendering`**; wrong audit/sim artifact → **`audit_simulation`**; load/encoding/UI shell → **`application_infrastructure`**.

### G. Title conventions

Prefix by **Type**:

- `[BUG]` — **bug**
- `[QUALITY]` — **quality**
- `[DESIGN_GAP]` — **design_gap**

Example: `[BUG] Orchestration selects ineligible actor under continuation override`.

### H. Status / execution stages (single active; transitions)

**Allowed values:** `open` | `investigating` | `consensus_reached` | `implemented` | `validated` | `closed` | `monitor` | `wont_fix`

**Representation:** exactly one line in the body: `Current status: <value>`.

**Allowed transitions**

| From | To |
|------|-----|
| `open` | `investigating` |
| `investigating` | `consensus_reached` |
| `consensus_reached` | `implemented` |
| `implemented` | `validated` |
| `validated` | `closed` |
| `investigating` | `monitor` |
| `investigating` | `wont_fix` |

**Exception:** `open` → `closed` only for **duplicate** or **withdrawn** filings (document in a comment). No other skips (e.g. do not jump from `open` to `implemented`).

Terminal statuses: **`closed`**, **`monitor`**, **`wont_fix`**.

### I. Pattern status (discipline)

1. **Audit-only (no GitHub Issue):** Incomplete mandatory evidence (scenario id, audit session path, turn index or documented `n/a`) **or** purely heuristic audit noise without runtime contradiction—keep in audit notes until evidence is complete and **Pattern status** can be assigned.
2. **`single_instance`:** Allowed only when mandatory evidence is complete **and** impact is **high** (integrity, safety, hard contradiction across truth layers, blocking repro), **or** the team explicitly accepts a one-shot fix with documented risk. Otherwise wait for repetition.
3. **`potential_pattern`:** Two or more similar instances **or** one strong instance plus a clear code signature suggesting repeat risk.
4. **`confirmed_pattern`:** Same signature across **distinct** scenarios or sessions (or repeated runs showing the same failure mode).
5. **Escalation:** `single_instance` → `potential_pattern` when a second instance matches; `potential_pattern` → `confirmed_pattern` when the signature holds across distinct scenarios/sessions. Downgrade if evidence shows operator error or invalid run.
6. **Type** is independent of **Pattern status**; do not use **bug** without **§E** and **consensus**.

### J. Guiding principles

- Do **not** open Issues for trivial or disposable thoughts.
- **Do** open Issues when work may need investigation, implementation, validation, or later reference—subject to **§I**.
- Keep roadmap files phase-oriented; keep investigative history in Issues.
- **Reference Issues in commits** (`#nnn` / `Fixes #nnn` when appropriate).
- **Avoid duplicating** long narratives between Issues and repo markdown; link out.

### K. Flexibility clause

> These conventions are the current standard and may be refined by explicit doc change.
