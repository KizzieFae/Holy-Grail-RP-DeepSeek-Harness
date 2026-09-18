# Issue #201 — Current vs A2 Scene Data-Pathway Matrix

**Parent Issue:** [#201](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/201)  
**Status:** Canonical pre-migration architecture map (Governance review; #201 closure paused)  
**Related:** `issue-201-final-architecture-decision-2026-09-17.md`, `issue-201-g2-a2-redesign-specification-2026-09-15.md`, migration children [#209](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/209)–[#212](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/212)

## Anchor semantics

| Side | Meaning |
|------|---------|
| **Current** | Production architecture at **inspected SHA** (see below) and date **2026-09-17**, derived from `v2/rp_runtime/`, `v2/domain_api/`, `v2/domain/modules/`, `docs/architecture.md`, and `llm-call-catalog.mjs`. |
| **A2 target** | Governance-accepted direction from #201 final decision and G2 spec — **not implemented** in production. |
| **Experimental** | `#201` investigation harness (`issue201-lh0-*`, `issue201-lh1b-*`, aging campaigns) — **not** default production path unless noted. |

**Inspected production SHA:** `968ba2af20fd3bc1ed4bd7f616e3f098b985463f`.  
**Prior related artifacts (not equivalent):** Package B node inventory (`issue-201-packages-abc-investigation-2026-09-14.md` §5–6); runtime LLM coverage audit (`issue-201-runtime-llm-call-coverage-audit-2026-09-15.md`) — **call-centric**, not information-flow rows; G2 §18–20 — **target flows only**.

## Legend

**Authority class:** `AS` authoritative state · `AD` authoritative decision · `VP` validated proposal · `AC` advisory cognition · `RO` rendered observation · `RE` retrieved evidence · `VW` viewer projection · `AE` audit evidence · `XO` experimental-only  

**Timing (current / A2):** `MS` mandatory synchronous · `CS` conditional synchronous · `PC` post-commit (joined before next Director) · `ASYNC` asynchronous/off critical path · `DET` deterministic/local · `UN` unresolved target timing  

**Change disposition:** `INT` essentially intact · `SIM` simplified · `CON` conditionalized · `OFF` moved off default sync path · `REM` removed from default path · `REP` replaced mechanism · `UNR` unresolved implementation  

**Migration owner:** `209` Track A skeleton · `210` support tiering · `211` Plot topology · `212` acceptance · `—` none  

---

## Primary matrix

Columns: **Path ID** | **Pathway** | **Origin** | **Current (producer → consumer)** | **Current authority** | **Current persistence** | **Current timing** | **A2 target (summary)** | **A2 timing** | **Disposition** | **Owner** | **Confidence** | **Evidence**

### Family 1 — Scenario / world authority

| Path ID | Pathway | Origin | Current | Auth | Persist | Timing | A2 target | A2 timing | Disp | Owner | Conf | Evidence |
|---------|---------|--------|---------|------|---------|--------|-----------|-----------|------|-------|------|----------|
| DP-SC-01 | Scenario premise & static setup | Authored scenario JSON / `data/` | Host `prepare_*` → `scene_setup`, `scenario_authority` lanes in Director/Character/Narrator manifests | AS (scenario contract) | Scenario files + session binding | DET | Same deterministic packaging; bounded omission manifest | DET | INT | 209 | high | `character_context_projector.py`, `prepare_director_context` |
| DP-SC-02 | Session opening prose | Scenario template or LLM `opening` | DSH `runOpeningPhase` → `record_presentation` / history | RO → AS in history | `rp_history`, session store | MS (session init) | Retain opening generation; optional segmentation only on long templates | CS | INT | 209 | high | `opening-phase.mjs`, catalog `opening` |
| DP-SC-03 | Role definitions & character cards | Scenario + Continuity character records | Host projection → Character identity lanes | AS | Continuity character state | DET | Unchanged substrate projection | DET | INT | 209 | high | `character_context_projector.py` |
| DP-SC-04 | Role-private knowledge | Scenario corpus + entitlement tags | Retrieval index + Host gates → Character-only lanes (`known_by`) | AS (entitled facts) | Story JSONL / knowledge store | DET (+ RE when retrieved) | Same; retrieval when obligation fires | CS + DET | INT | 209/210 | high | `story-knowledge.md`, G3-E records |
| DP-SC-05 | World / environmental baseline | Continuity `scene_state`, env modules | Host `scene_state`, `recent_environment` → Director/Character/Narrator | AS | Continuity | DET | Unchanged authoritative env state | DET | INT | 209 | high | `continuity_manager.py`, `docs/architecture.md` |
| DP-SC-06 | Scene progression digest | Continuity after commits | Host `scene_progression` lane (not raw `recent_delta`) | AS (derived digest) | Continuity | DET | Same bounded digest | DET | INT | 209 | high | `docs/architecture.md` §Runtime stack |
| DP-SC-07 | Director steering hints (derived) | Player posts + continuity | Host `user_steering_hints` (optional) → Director manifest | AC/derived | Ephemeral per prepare | DET | Retain as deterministic derivation | DET | INT | 209 | high | `prepare_director_context` |
| DP-SC-08 | Opener / first-turn context carry | Opening + initial continuity | Same as SC-02 + SC-05 into first `runRound` | mixed | history + continuity | MS/DET | Unchanged | DET | INT | 209 | high | `hg-application-client.mjs` session create |

### Family 2 — Player input ingress

| Path ID | Pathway | Origin | Current | Auth | Persist | Timing | A2 target | A2 timing | Disp | Owner | Conf | Evidence |
|---------|---------|--------|---------|------|---------|--------|-----------|-----------|------|-------|------|----------|
| DP-PI-01 | Raw Player post (HTTP) | UI `POST /api/turns/submit` | `app-server.mjs` → `hg-application-client.submitUserTurn` | tier-1 input (pre-persist) | not yet durable | MS | Same ingress | MS | INT | 209 | high | `app-server.mjs` |
| DP-PI-02 | Visibility triage decision | Raw post | `player_visibility_triage` LLM → route uniform vs full PVR | AD (routing) | evidence only | MS | Retain cheap router | MS | INT | 209 | high | catalog #15, Package B N-10 |
| DP-PI-03 | Uniform eligibility verification | Raw post + triage | `player_uniform_eligibility_verification` when affirmative uniform | AD | evidence | CS | Retain on uniform path | CS | INT | 209 | high | #197, N-11 |
| DP-PI-04 | Uniform projection shortcut | Raw post | `player-uniform-projection.mjs` deterministic units | AS (synthetic decomposition) | via recordUserTurn | DET | Retain | DET | INT | 209 | high | N-12 |
| DP-PI-05 | Semantic player decomposition | Raw post | `player_decomposition` LLM → validated units | VP → AS at record | `record_user_turn` | CS (non-uniform) | Obligation-triggered decomposition only | CS | CON | 210 | high | #194, N-13 |
| DP-PI-06 | Player turn authority record | Decomposition or uniform | Host `kernel.record_user_turn` → `rp_history` tier-1 | AS | Continuity history | MS | Unchanged commit of player authority | MS | INT | 209 | high | N-15, `commit_move_transaction` freshness |
| DP-PI-07 | Forced speaker designation | Player UI / API | `forced_designation` → participation API (may bypass Director LLM) | AD | session round state | DET | Retain deterministic bypass | DET | INT | 209 | high | `detect-forced-speaker.mjs`, participation-direct |
| DP-PI-08 | Skip turn signal | Skip API | `record_user_turn` skip path → `runRound` without PVR LLM | AS | history | DET | Retain | DET | INT | 209 | high | `submitSkipTurn` |

### Family 3 — Perception / PVR / entitlement

| Path ID | Pathway | Origin | Current | Auth | Persist | Timing | A2 target | A2 timing | Disp | Owner | Conf | Evidence |
|---------|---------|--------|---------|------|---------|--------|-----------|-----------|------|-------|------|----------|
| DP-PV-01 | Decomposition units → entitlement graph | DP-PI-05/04 | Host `player_decomposition_context` validators | AS (entitlement structure) | with user turn | DET | Same | DET | INT | 209 | high | domain validators |
| DP-PV-02 | Perceptual decomposition / audibility | Domain `perception_audibility` | Deterministic filters on units | AS (entitlement) | embedded in turn | DET | Unchanged PVR substrate | DET | INT | 209 | high | `perception_audibility.py`, #155 |
| DP-PV-03 | Viewer-specific perceptual inventory | Entitlement + scene | Host `authoritative_perceptual_inventory` / character upstream | VW | turn-scoped | DET | Same projection discipline | DET | INT | 209 | high | #199, manifest policy lanes |
| DP-PV-04 | Player stimulus → Character `user_turn_trigger` | Entitled slice of player turn | `prepareCharacterContext` perception-filtered transcript | VW | ephemeral manifest | MS | Same bounded trigger | MS | INT | 209 | high | `docs/architecture.md` |
| DP-PV-05 | Player stimulus → Director `user_turn_source` | Authoritative skip-aware source | Director manifest lane | VW/AS mix | ephemeral | MS | Same | MS | INT | 209 | high | director context digests |
| DP-PV-06 | Presentation perceptual filter | Narrator output | `perceptual_visibility_service` on `record_presentation` | VW on visible text | history | MS | Retain | MS | INT | 209 | high | N-72, Package B |
| DP-PV-07 | Withheld / non-entitled information | Entitlement engine | Absence from consumer manifests (fail-closed) | AS (negative knowledge) | not persisted as fact | DET | Same | DET | INT | 209 | high | G3-E private knowledge tests |
| DP-PV-08 | Scene-pressure freshness gate | Post-commit overlays vs newer player seq | `overlay_semantic_fields_are_fresh` (#200) | AS gate on derived | continuity overlays | DET | Retain freshness binding | DET | INT | 209 | high | `continuity_scene_pressure_projection.py` |

### Family 4 — Director cognition

| Path ID | Pathway | Origin | Current | Auth | Persist | Timing | A2 target | A2 timing | Disp | Owner | Conf | Evidence |
|---------|---------|--------|---------|------|---------|--------|-----------|-----------|------|-------|------|----------|
| DP-DR-01 | Eligible actor set | Continuity + rules | Host `getEligibleActors` | AS | continuity | DET | Unchanged | DET | INT | 209 | high | orchestrator loop |
| DP-DR-02 | Participation decision | Policy + optional forced | Host `getParticipationDecision` | AD | round state | DET | Unchanged | DET | INT | 209 | high | participation API |
| DP-DR-03 | Director selection LLM | Manifest from Host | `director_turn` → validated decision JSON | AD | ephemeral until consumed | MS (unless bypass) | Retain when selection non-trivial; DET when obvious | CS | SIM | 209 | high | G2 §20, catalog |
| DP-DR-04 | Director semantic QA | Candidate decision | `director_semantic_qa` subordinate review | AC (QA) | evidence | MS | Remove default; conditional repair on validator uncertainty | CS | REM/CON | 210 | high | Package D, final decision |
| DP-DR-05 | Director decision → Character | Accepted decision | `director_context` advisory in Character prepare | AC (advisory to Character) | invalidated on commit | MS | Same boundary (advisory ≠ commit) | MS | INT | 209 | high | architecture-overview Model A |
| DP-DR-06 | Storyteller advisory → Director | Round-local package | `storyteller_*` lanes while valid | AC | round-local bind | MS preamble | Not default sync ST preamble | OFF | REM | 210/211 | high | #32, D-01-L |

### Family 5 — Character cognition

| Path ID | Pathway | Origin | Current | Auth | Persist | Timing | A2 target | A2 timing | Disp | Owner | Conf | Evidence |
|---------|---------|--------|---------|------|---------|--------|-----------|-----------|------|-------|------|----------|
| DP-CH-01 | Recent scene transcript (entitled) | `rp_history` + filters | Host lanes in Character manifest | VW | history store | MS | Bounded transcript + omission manifest | MS | INT | 209 | high | character projector |
| DP-CH-02 | Character orientation cognition | Upstream manifest snapshot | `character_orientation` LLM (+ optional KAR) | AC | evidence | MS | Conditional orientation obligation | CS | CON | 210 | high | N-44, catalog |
| DP-CH-03 | Librarian mediation @character | KAR / orientation | `librarian_mediation` → bundle → mapper lanes | RE/AC | none durable | MS | Conditional mediation | CS | CON | 210 | high | N-45 |
| DP-CH-04 | Plot projection → Character | Plot overlay service | epistemic eval + optional `character_advisory_generation` | AC | plot overlay store | MS | Bounded projection; sync only if plot obligation blocks beat | CS | CON/OFF | 211 | medium | `plot-cognition-character-projection.mjs` |
| DP-CH-05 | Storyteller advisory → Character | Bound package | mapper lanes while valid | AC | round-local | MS | No default ST package on simple beats | OFF | REM | 210 | high | storyteller bind |
| DP-CH-06 | Scene pressures → Character | Continuity digests + overlays | `scene_pressures` lanes | AC (derived) | overlays | MS | Same with freshness gates | MS | INT | 209 | high | #200 |
| DP-CH-07 | Character move generation | Full manifest | `character_turn` / `character_move` | VP | evidence | MS | Retain core cognition | MS | INT | 209 | high | N-47 |
| DP-CH-08 | Structural move validation | VP | Host `validate_move` | DET gate | none | MS | Unchanged | DET | INT | 209 | high | N-48 |
| DP-CH-09 | Character semantic evaluation | VP + authority refs | `character_semantic_evaluation` | AC (QA gate) | evidence | MS | Conditional semantic check on failure/uncertainty | CS | CON | 210 | high | #193, #199 |
| DP-CH-10 | Accepted move → commit | Passed validation | `commit_move` / `process_turn` | AS | continuity + history | MS | Unchanged authority seam | MS | INT | 209 | high | `commit_move_transaction.py` |
| DP-CH-11 | Rejected move retry loop | Failed validate/semantic | Re-prep + new inference attempts | — | none | MS | Bounded repair obligation | CS | CON | 210 | medium | character-phase retry policy |
| DP-CH-12 | Committed structured move → Narrator | Post-commit | Orchestrator passes committed surface | AS | continuity | PC→MS | Same | MS | INT | 209 | high | narrator prepare |

### Family 6 — Continuity / authoritative state

| Path ID | Pathway | Origin | Current | Auth | Persist | Timing | A2 target | A2 timing | Disp | Owner | Conf | Evidence |
|---------|---------|--------|---------|------|---------|--------|-----------|-----------|------|-------|------|----------|
| DP-CO-01 | Proposed mutation (pre-commit) | Character VP | validate_move only | VP | none | MS | Same | MS | INT | 209 | high | validation pipeline |
| DP-CO-02 | Authoritative commit transaction | Validated move + director context | `execute_commit_move` single persist gate | AS | session JSON + dedup | MS | Rebuild semantics preserved | MS | INT | 209 | high | #55 C3-F |
| DP-CO-03 | S4 post-commit semantic apply | Librarian proposals | `finalize_librarian_proposals` allowlisted surfaces | AS (derived overlays) | continuity + audit log | PC | Conditional / narrowed triggers | CS | CON | 210 | high | #164, librarian contract |
| DP-CO-04 | Plot overlay mutations | Plot cognition finalize | Domain plot services | AC→AS overlay rules | plot overlay repo | MS/PC | Async default; sync when obligation | OFF/CS | OFF | 211 | medium | plot cognition docs |
| DP-CO-05 | PublicEvent promotion | Post-commit promotion | `KnowledgeService.promote_after_commit` | AS | story JSONL | post-durable | Retain | ASYNC | INT | 209 | high | #51 |
| DP-CO-06 | Storyteller package invalidation | Character commit | Phase F invalidation | DET | round-local cleared | MS | Retain hygiene | DET | INT | 209 | high | commit transaction |
| DP-CO-07 | `domain_commit_id` / turn index | Commit | Propagates to post-commit lanes | AS refs | continuity | MS | Retain correlation | MS | INT | 209 | high | orchestrator |
| DP-CO-08 | Continuity version / scene state reread | After round | `getSceneState` | AS | continuity | DET | Same | DET | INT | 209 | high | round completion |

### Family 7 — Narrator cognition

| Path ID | Pathway | Origin | Current | Auth | Persist | Timing | A2 target | A2 timing | Disp | Owner | Conf | Evidence |
|---------|---------|--------|---------|------|---------|--------|-----------|-----------|------|-------|------|----------|
| DP-NA-01 | Committed move → presentation input | DP-CH-10 | Host `prepareNarratorContext` | AS | continuity | PC | Same | MS/PC | INT | 209 | high | narrator-phase |
| DP-NA-02 | Player post analysis surface | History | Narrator manifest (analysis, not authority) | VW | ephemeral | PC | Retain bounded analysis | MS | INT | 209 | high | architecture |
| DP-NA-03 | Environment cognition (B2) | Material obligations | `narrator_environment_cognition` | AC | proposals | PC (blocks narrator join) | Conditional env obligation | CS | CON | 210 | high | #194 N-62 |
| DP-NA-04 | Librarian mediation @narrator | Env / narrator parent | `librarian_mediation` | RE/AC | none | PC | Conditional | CS | CON | 210 | high | N-63 |
| DP-NA-05 | Narrator presentation LLM | Manifest | `narrator_presentation` | RO | evidence | PC | Retain render cognition | MS | INT | 209 | high | N-64 |
| DP-NA-06 | Narrator semantic QA | RO candidate | `narrator_semantic_qa` | AC | evidence | PC | Default off; repair on failure | CS | REM/CON | 210 | high | Package D |
| DP-NA-07 | Degraded presentation fallback | QA hard fail / infra | Deterministic from `structured_move` | RO | history | DET | Retain deterministic fallback | DET | INT | 209 | high | #29 |
| DP-NA-08 | Presentation → player-visible history | RO accepted | `record_presentation` + PVR filter | AS in history | rp_history | MS | Unchanged | MS | INT | 209 | high | N-70 |

### Family 8 — Retrieval / Librarian

| Path ID | Pathway | Origin | Current | Auth | Persist | Timing | A2 target | A2 timing | Disp | Owner | Conf | Evidence |
|---------|---------|--------|---------|------|---------|--------|-----------|-----------|------|-------|------|----------|
| DP-RT-01 | Retrieval index query (deterministic) | Obligation / manifest gap | Host retrieval façade (#31) | RE | corpus | DET | Expanded obligation routing | DET | INT | 209 | high | story-knowledge.md |
| DP-RT-02 | Librarian contextual semantic (read) | KAR | Host Librarian service | RE | none | MS when invoked | Conditional | CS | CON | 210 | high | #34 |
| DP-RT-03 | Bundle → manifest lanes | S2b mapper | `map_librarian_bundle_to_contributions` | VW/RE | ephemeral | MS | Same mapper; fewer default invocations | CS | CON | 210 | high | architecture §#33 |
| DP-RT-04 | Post-commit issue pressure proposal | ACTIVE issues | `storyteller_post_commit_issue_pressure` | AC→AS overlay | continuity overlays | PC | Optional async refresh; not default sync pressure pass | OFF/ASYNC | OFF | 210/211 | high | #164 |
| DP-RT-05 | S4 audit terminal record | Proposal batch | `librarian_proposal_audit_log` | AE | audit store | PC | Retain forensics | PC/ASYNC | INT | 212 | high | #100 |
| DP-RT-06 | Knowledge revelation significance | Legacy/separate path | `knowledge_revelation_significance` | AS mutation | PublicEvent | rare | Not routine sync | CS | INT | — | medium | librarian contract |

### Family 9 — Environmental / scene grounding

| Path ID | Pathway | Origin | Current | Auth | Persist | Timing | A2 target | A2 timing | Disp | Owner | Conf | Evidence |
|---------|---------|--------|---------|------|---------|--------|-----------|-----------|------|-------|------|----------|
| DP-EN-01 | Env obligation detection | Host signals §G2-15 | Deterministic flags in prepare | DET | none | DET | Same obligation aggregator | DET | INT | 209 | high | G2 §20 |
| DP-EN-02 | Env cognition LLM output | DP-EN-01 | B2 proposals → Narrator context | AC | optional proposals | PC | Only when obligation unresolved | CS | CON | 210 | high | narrator-env substrate |
| DP-EN-03 | Deterministic env sufficiency | Baseline scene_state | Skip env LLM when sufficient | DET | — | DET | Default path | DET | SIM | 210 | high | #151 tests |
| DP-EN-04 | Scene Grounding MVP (if enabled) | Separate doc path | Per `scene-grounding-layer.md` | AS/DET | varies | CS | Align with tiered env | CS | UNR | 210 | medium | docs/scene-grounding-layer.md |

### Family 10 — Plot / Scribe (production Plot Cognition)

| Path ID | Pathway | Origin | Current | Auth | Persist | Timing | A2 target | A2 timing | Disp | Owner | Conf | Evidence |
|---------|---------|--------|---------|------|---------|--------|-----------|-----------|------|-------|------|----------|
| DP-PL-01 | Round-start pending work plan | Domain planner | `planPostCommitPlotCognitionWork` / resume lifecycle | DET | durable pending | MS preamble | Off default sync; resume async | ASYNC | OFF | 211 | medium | orchestrator round start |
| DP-PL-02 | Plot init LLM | Pending init | `plot_cognition_init` | AC | overlay store | MS | Async init when needed | ASYNC | OFF | 211 | medium | N-33 |
| DP-PL-03 | Plot update LLM | Staleness / resume | `plot_cognition_update` | AC | overlay | MS/PC | Default post-commit async | ASYNC | OFF | 211 | medium | N-34, N-61 |
| DP-PL-04 | Epistemic eval for Character projection | Overlay freshness | `plot_cognition_epistemic_eval` | AC | none | MS | Conditional; default off | CS | OFF | 211 | high | N-46 |
| DP-PL-05 | Advisory regeneration | Failed epistemic | `character_advisory_generation` | AC | none | MS | Rare conditional | CS | OFF | 211 | high | plot projection |
| DP-PL-06 | Overlay persistence | Finalize | Domain overlay repository | AS (overlay) | `data/` plot stores | MS/PC | Retain persistence | ASYNC | INT | 211 | high | plot cognition docs |
| DP-PL-07 | Character consumer projection | Overlay view | Host projection service (#62) | VW | ephemeral | MS | Bounded projection when obligation | CS | CON | 211 | high | `plot_cognition_projection_service.py` |
| DP-PL-08 | Forensic chronicle | Mutations | `plot_cognition_forensics` | AE | forensics dir | DET | Retain audit | DET | INT | 212 | high | forensics contract |

### Family 11 — Storyteller-class

| Path ID | Pathway | Origin | Current | Auth | Persist | Timing | A2 target | A2 timing | Disp | Owner | Conf | Evidence |
|---------|---------|--------|---------|------|---------|--------|-----------|-----------|------|-------|------|----------|
| DP-ST-01 | Round-start orientation | Scene snapshot | `storyteller_orientation` | AC | evidence | MS | Not rebuilt as mandatory preamble | OFF | REM | 210 | high | N-30 |
| DP-ST-02 | Librarian mediation @storyteller | ST orientation | `librarian_mediation` (parent narrator profile) | RE/AC | none | MS | Conditional / off default | OFF | REM | 210 | high | N-31 |
| DP-ST-03 | Storyteller assessment | After bundle | `storyteller_assessment` | AC | evidence | MS | Not default sync | OFF | REM | 210 | high | N-32 |
| DP-ST-04 | Advisory package bind | Assessment output | `bindStorytellerAdvisoryPackage` | AC | round-local | MS | Optional future persistent narrative path | UN | UNR | 211 | medium | storyteller service |
| DP-ST-05 | Post-commit issue pressure | Commits | see DP-RT-04 | AC | overlays | PC | Off default sync Storyteller stack | OFF | OFF | 210 | high | D-01-L residual |
| DP-ST-06 | Long-range ST responsibilities (planning, threads) | N/A in production always-on | Partially in advisory text only | AC | not durable ST store | — | May migrate to Plot/async narrative; **not disproven** | UN | UNR | 211 | low | final decision §Storyteller |

### Family 12 — Semantic QA / repair / orientation

| Path ID | Pathway | Origin | Current | Auth | Persist | Timing | A2 target | A2 timing | Disp | Owner | Conf | Evidence |
|---------|---------|--------|---------|------|---------|--------|-----------|-----------|------|-------|------|----------|
| DP-SQ-01 | Director semantic QA | DP-DR-03 | see DP-DR-04 | AC | evidence | MS | Conditional | CS | CON | 210 | high | — |
| DP-SQ-02 | Character semantic eval | DP-CH-07 | see DP-CH-09 | AC | evidence | MS | Conditional | CS | CON | 210 | high | — |
| DP-SQ-03 | Narrator semantic QA | DP-NA-05 | see DP-NA-06 | AC | evidence | PC | Conditional | CS | CON | 210 | high | — |
| DP-SQ-04 | Contract correction (parse) | Structural parse fail | `*_contract_correction` kinds | AC | evidence | CS retry | Retain max-1 correction | CS | INT | 209 | high | contract-correction-substrate |
| DP-SQ-05 | Character orientation (support) | DP-CH-02 | distinct from SQ eval | AC | evidence | MS | Tiered orientation | CS | CON | 210 | high | — |

### Family 13 — Audit / observability

| Path ID | Pathway | Origin | Current | Auth | Persist | Timing | A2 target | A2 timing | Disp | Owner | Conf | Evidence |
|---------|---------|--------|---------|------|---------|--------|-----------|-----------|------|-------|------|----------|
| DP-AU-01 | LLM attempt evidence | Each inference | `execution-evidence/recorder.mjs` | AE | `data/execution_evidence/` | parallel | Preserve | DET/AE | INT | 212 | high | architecture §Inference transport |
| DP-AU-02 | Orchestration spans / graph | Round/post-commit | `execution_span` + #173 graph | AE | evidence | parallel | Preserve join semantics | DET | INT | 212 | high | post-commit-span-coordinator |
| DP-AU-03 | Hg trace events | Orchestrator | `hg-trace-emitter` | AE | scene session | parallel | Retain | DET | INT | 212 | high | trace emitter |
| DP-AU-04 | Commit boundary marker | commit | `measureCommitBoundary` | AE | span graph | MS | Retain | MS | INT | 212 | high | character-turn-span-coordinator |
| DP-AU-05 | Librarian proposal audit log | S4 | Host audit log | AE | session | PC | Retain | PC | INT | 212 | high | #100 |
| DP-AU-06 | Plot cognition forensics | Plot mutations | DP-PL-08 | AE | forensics | DET | Retain | DET | INT | 212 | high | — |

### Family 14 — Turn / scene carryover

| Path ID | Pathway | Origin | Current | Auth | Persist | Timing | A2 target | A2 timing | Disp | Owner | Conf | Evidence |
|---------|---------|--------|---------|------|---------|--------|-----------|-----------|------|-------|------|----------|
| DP-CY-01 | Raw transcript append | Presentations + user turns | `rp_history` | AS | session store | MS | Unchanged | MS | INT | 209 | high | history kernel |
| DP-CY-02 | Authoritative continuity state | Commits | `SceneState` / `process_turn` | AS | continuity | MS | Rebuild substrate same semantics | MS | INT | 209 | high | continuity modules |
| DP-CY-03 | Character memory lanes | Post-commit memory | continuity character memory | AS | continuity | post-durable | Retain | MS | INT | 209 | high | commit transaction |
| DP-CY-04 | Retrieval index updates | Promotions / corpus | story JSONL index | RE | corpus | ASYNC | Retain | ASYNC | INT | 209 | high | story-knowledge |
| DP-CY-05 | Plot overlay carryover | Plot persistence | overlay repo | AC/AS | durable overlay | MS/PC | Async durable narrative state | ASYNC | OFF | 211 | medium | LH R0–R4 evidence |
| DP-CY-06 | Scene pressures to next Director | Overlays + digests | `scene_pressures` | AC | overlays | MS | Same with freshness | MS | INT | 209 | high | #200 |
| DP-CY-07 | Storyteller package carryover | Round-local | Valid until commit invalidation | AC | round-local | MS | No default round-local ST package | OFF | REM | 210 | high | Model A |
| DP-CY-08 | Next-turn Player entitlement | New post | PVR pipeline | AS | history | MS | Unchanged | MS | INT | 209 | high | aging investigation: establishment separate from carryover |

---

## Current Scene Walkthrough (architecture-level)

1. **Scenario/world:** Session loads scenario authority; optional LLM `opening` persists to history; continuity holds `scene_state` / progression digests.  
2. **Player input:** Submit → triage → (uniform verify **or** decomposition) → `record_user_turn` tier-1 authority.  
3. **Entitlement:** Deterministic PVR; entitled slices feed Director `user_turn_source` and Character `user_turn_trigger`; withheld content absent from manifests.  
4. **Round preamble (sync):** Storyteller orientation → Librarian mediation → assessment → bind advisory; Plot pending-work resume (init/update).  
5. **Director loop:** Eligibility → participation (optional bypass) → `director_turn` → `director_semantic_qa` → route Character.  
6. **Character:** Orientation → Librarian @character → Plot projection eval/advisory → `character_move` → `validate_move` → `character_semantic_evaluation` → **`commit_move`**.  
7. **Continuity:** Transactional persist; invalidate Storyteller package; emit `domain_commit_id`.  
8. **Post-commit parallel:** Librarian issue-pressure + Plot update + (Narrator env → Librarian @narrator → presentation → narrator QA); **join** narrator → librarian → plot before next Director iteration.  
9. **Presentation:** `record_presentation` + perceptual filter → UI transcript.  
10. **Audit:** Execution evidence + spans for every LLM and join.  
11. **Carryover:** `rp_history`, continuity, overlays, plot state feed next turn.

## A2 Target Scene Walkthrough

1. **Scenario/world:** Unchanged deterministic authority and scenario lanes (**209**).  
2. **Player input:** Same ingress; decomposition **conditional** on entitlement divergence (**210**).  
3. **Entitlement:** Same PVR substrate (**209**).  
4. **Round start:** **No default** Storyteller preamble chain; Plot pending work **off default sync** (**211** — *DESIGN TO BE RESOLVED BY #211* for exact async scheduler).  
5. **Director:** Deterministic eligibility/participation; `director_turn` **only when** obligation router says selection ambiguous (**209** + G2 §20); **no default** director semantic QA (**210**).  
6. **Character:** Core move + validate + **conditional** semantic check; orientation/Librarian/Plot projection **tiered** (**210**, **211**).  
7. **Continuity:** Same commit authority (**209**).  
8. **Narrator:** Committed move render mandatory; env cognition and Librarian **conditional**; **no default** narrator QA (**210**).  
9. **Plot/Scribe:** Persistence/projection retained; default **async/off critical path** (**211** — *DESIGN TO BE RESOLVED BY #211*).  
10. **Audit:** Full evidence preservation (**212**).  
11. **Carryover:** Authoritative continuity + transcript + conditional retrieval; persistent narrative via Plot/async mechanisms.

## Current → A2 Delta (derived)

| Category | Path count (approx.) | Notes |
|----------|---------------------:|-------|
| Essentially intact (`INT`) | 38 | Core authority, PVR, commit, presentation, audit substrate |
| Simplified (`SIM`) | 3 | Director/Narrator fan-in; env sufficiency default |
| Conditionalized (`CON`) | 22 | Support cognitions + semantic checks + decomposition |
| Moved off default sync (`OFF`) | 14 | ST preamble, post-commit ST pressure default, Plot preamble/sync update, plot epistemic chain |
| Removed from default path (`REM`) | 5 | Always-on QA stacks (grouped with CON rows) |
| Unresolved target (`UNR`) | 4 | Async Plot scheduler detail, long-range ST ownership, Scene Grounding tie-in |

## Inference-identity completeness (PRIMARY_RUNTIME_CATALOG)

| Catalog row / kind | Matrix pathway(s) |
|--------------------|-------------------|
| `director_turn` | DP-DR-03 |
| `director_semantic_qa` | DP-DR-04, DP-SQ-01 |
| `character_turn` | DP-CH-07 |
| `character_semantic_evaluation` | DP-CH-09, DP-SQ-02 |
| `character_orientation` | DP-CH-02, DP-SQ-05 |
| `librarian_mediation@character` | DP-CH-03 |
| `librarian_mediation@narrator` | DP-NA-04 |
| `librarian_mediation_contract_correction` | DP-SQ-04 |
| `storyteller_post_commit_issue_pressure` (+ correction) | DP-RT-04, DP-ST-05 |
| `narrator_presentation` | DP-NA-05 |
| `narrator_environment_cognition` | DP-EN-02, DP-NA-03 |
| `narrator_semantic_qa` | DP-NA-06, DP-SQ-03 |
| `opening` / `opening_segmentation` | DP-SC-02 |
| `player_visibility_triage` | DP-PI-02 |
| `player_uniform_eligibility_verification` | DP-PI-03 |
| `player_decomposition` | DP-PI-05 |
| `storyteller_orientation` / `storyteller_assessment` | DP-ST-01–03 |
| `plot_cognition_init` / `update` (+ corrections) | DP-PL-02–03, DP-SQ-04 |
| `plot_cognition_epistemic_eval` (+ correction) | DP-PL-04 |
| `character_advisory_generation` | DP-PL-05 |
| Harness annex `storyteller_certification_eval` | **non-scene** (harness) |
| Harness annex `infrastructure_provider_probe` | **test-only** |

## Deterministic subsystem completeness

| Subsystem | Matrix coverage |
|-----------|-----------------|
| Continuity / commit | DP-CO-*, DP-CH-10, DP-CY-02 |
| PVR / entitlement | DP-PV-* |
| Validation | DP-CH-08, DP-CH-09, DP-DR-04, DP-NA-06 |
| Audit | DP-AU-* |
| Retrieval / indexing | DP-RT-* |
| Obligation routing (target) | G2 §20 referenced; **implementation UNR** — **209** |
| Plot overlay authority | DP-PL-* |

## Documentation vs code discrepancies

| Topic | Doc | Code/runtime | Disposition |
|-------|-----|--------------|-------------|
| Plot "not single always-on LLM" | `docs/architecture.md` §Plot | Round-start **sync** resume still on critical path before Director | **Doc accurate**; sync **planner** vs conditional **inference** — matrix marks DP-PL-01 MS with inference conditional |
| Post-commit join order | #173 graph | Narrator → Librarian → Plot joins | Aligned |
| Storyteller Narrator mapper | architecture "future socket" | Narrator does not consume ST lanes post-commit | Aligned |
| 27 catalog rows vs 26 kinds | `docs/architecture.md` | `llm-call-catalog.mjs` | Aligned |

## Governance discussion hooks

1. Exact **async Plot** work queue semantics (**#211**).  
2. Whether **post-commit issue pressure** moves fully async or remains conditional sync.  
3. **Character semantic evaluation** minimum bar vs full conditionalization.  
4. **Scene Grounding MVP** relationship to env obligation tiering.  
5. **#201 closure** after matrix review vs keeping OPEN through Track A planning.

---

*Matrix row count: **91** pathways (DP-SC-01 … DP-CY-08). Counts in handoff report are derived from this set.*
