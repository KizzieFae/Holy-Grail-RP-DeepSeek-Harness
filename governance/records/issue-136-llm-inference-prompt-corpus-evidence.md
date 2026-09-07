# Issue #136 — LLM Inference Prompt/Instruction Corpus Evidence

**Parent assessment:** [`issue-136-llm-inference-contract-assessment.md`](issue-136-llm-inference-contract-assessment.md)  
**Issue:** [#136](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/136)  
**Evidence snapshot SHA:** *(set at PR head — historical Issue #136 evidence only; does not supersede production sources)*  
**Investigation baseline SHA:** `c616d98912474cc1b3366ac21afebe9397885de3`  
**Captured from branch:** `issue-136-llm-inference-assessment` at publication commit

---

## Disclaimer

This document is a **read-only snapshot** of model-facing instruction material at the cited repository SHA. Production prompt authority remains the source files cited below. If those sources change later, this evidence remains the historical #136 record.

---

## Assembly model (all inference kinds)

### Message structure

1. **DSH ephemeral agent** created per call (`inference-substrate.mjs`).
2. **Manifest contributions** registered on agent system context via `hg-context-bridge/service.mjs` — each `PromptContribution` becomes a named context block ordered by `priority` (ascending).
3. **User message** appended via `createUserMessage({ content: [{ type: 'text', text: prompt }] })` where `prompt` is the DSH-side user prompt (envelope builder, phase constant, or inline string).
4. **No separate system prompt file** beyond `inferenceConfig.systemPersona` default: `Holy Grail RP runtime.` (recorder metadata; not role instructions).

### Three evidence layers (per call)

| Layer | What appears in model context |
|-------|------------------------------|
| **A. Static instruction text** | DSH `prompt` argument + manifest `inference_instruction` / rubric contributions + shared constants in `narrative_visibility_prompt.py` etc. |
| **B. Assembly/scaffolding** | Context bridge ordering; JSON schema blocks embedded in prompts; contract-correction prompts on retry; semantic_correction JSON contributions (priority 29) |
| **C. Dynamic context** | All other manifest `source_kind` lanes (scene_state, committed_move, librarian catalog, storyteller advisory, memory, etc.) — content varies per turn |

**Model-facing order:** Lower `priority` numbers appear earlier in system context; user `prompt` is always last (after manifest registration).

---

## Coverage table (inventory reconciliation)

| Inference kind / path | Static prompt evidence | Coverage status |
|----------------------|------------------------|-----------------|
| `director_turn` | §D.1 | complete static prompt evidence captured |
| `director_semantic_qa` | §D.2 | complete (DSH + Host rubric; see duplication) |
| `storyteller_orientation` | §S.1 | complete (DSH envelope + Host instruction) |
| `storyteller_assessment` | §S.2 | complete (DSH envelope + Host instruction) |
| `librarian_mediation` | §L.1 | complete (DSH envelope + Host instruction + catalog) |
| `librarian_proposal` | §L.2 | complete |
| `character_orientation` | §C.1 | complete |
| `character_turn` (production) | §C.2 | complete |
| `character_turn` (`character_inference_slice`) | §C.3 | shares canonical instruction sources + slice-specific DEFAULT |
| `character_semantic_evaluation` | §C.4 | complete (DSH inline + Host rubric) |
| `plot_cognition_epistemic_eval` | §PC.1 | complete |
| `plot_cognition_init` | §PC.2 | complete |
| `plot_cognition_update` / replan | §PC.3 | schema/scaffolding-only instruction captured |
| `character_advisory_generation` | §PC.4 | dynamic-context-only distinction documented (Host-prepared; prompt from service) |
| `narrator_environment_cognition` | §N.1 | complete |
| `narrator_presentation` | §N.2 | complete (DSH user + Host render instruction + NVR) |
| `narrator_semantic_qa` | §N.3 | complete (DSH + Host rubric) |
| `opening` | §AUX.1 | complete |
| `opening_segmentation` | §AUX.2 | shares `OPENING_SEGMENTATION_OUTPUT_INSTRUCTION` |
| `player_visibility_triage` | §AUX.3 | complete |
| `player_decomposition` | §AUX.4 | complete |
| `storyteller_certification_eval` | §HARNESS | harness/test-only |
| `instrumented-inference` | §HARNESS | harness wrapper only |

---

## D. Director

### D.1 `director_turn`

**Provenance**

| Component | Path | Identity |
|-----------|------|----------|
| DSH user prompt | `v2/rp_runtime/src/lib/live-inference-prompts.mjs` | `LIVE_DIRECTOR_PROMPT` |
| Host scratch | `v2/domain_api/director_context.py` | `director_scratch` contribution L71–74 |
| Host instruction | `v2/domain_api/director_context.py` | `inference_instruction` contribution L83–88 |
| Assembly | `v2/rp_runtime/src/plugins/hg-phase-executors/director-phase.mjs` | `runDirectorPhase` → `prepareDirectorContext` + `runEphemeralInference({ prompt: LIVE_DIRECTOR_PROMPT })` |

#### A. Static text — DSH user prompt (verbatim)

```
Respond with ONLY one JSON object. No markdown, no commentary. Required keys: next_actor (string), end_round (boolean), reason (string), environment_event (string), tension_shift (string). Set tension_shift to exactly escalate, soften, or steady. environment_event is optional; use an empty string instead of repeating a recent accepted environment development. Select next_actor from the eligible cast in context. Set end_round false unless the scene should stop.
```

#### A. Static text — Host `director_scratch` (verbatim)

```
Director scratch: weigh participation balance and select the next actor. Do not assume character-private knowledge.
```

#### A. Static text — Host `inference_instruction` (verbatim)

```
Output only JSON with next_actor, end_round, reason, environment_event, tension_shift. tension_shift must be escalate, soften, or steady. environment_event is optional; use an empty string rather than repeating a recent accepted environment development.
```

#### B. Assembly notes

- Scene digests, storyteller advisory, plot overlay, auth projections inserted as manifest contributions (priorities 10–25 range).
- On semantic QA regen: `semantic_correction_contribution` JSON (priority 29) inserted before instruction; includes `instruction` field from `buildCorrectionContextFromDirectorQa`.

#### C. Dynamic context (summary)

| Material | source_kind examples | Insertion |
|----------|---------------------|-----------|
| Scene state, continuity, grounding | `scene_state`, `continuity_canon`, `scene_grounding` | Via `project_authoritative_context` + digests |
| Eligible actors | digest contributions | `build_director_scene_evidence_contributions` |
| Storyteller advisory | `storyteller_*` | `storyteller_contributions_for_consumer(consumer_target="director")` |
| Plot overlay | `overlay_*` | overlay service |

---

### D.2 `director_semantic_qa`

**Provenance:** `director-semantic-qa.mjs` `buildDirectorEvaluatorPrompt`; `director_semantic_qa_context.py` `DIRECTOR_SEMANTIC_QA_RUBRIC`; DSH user prompt passed to `runSemanticQaEvaluation`.

#### A. DSH user prompt (verbatim — single joined string)

```
You are a bounded semantic QA evaluator for a Director decision candidate. Return ONLY one JSON object (no markdown) with schema hg_semantic_qa_result_v1. Set evaluation_target_role to "director" and evaluation_pass_id to "<pass id>". Use overall_result pass|reject_soft|reject_hard and findings[] with dimensions: dir_actor_suitability, dir_scene_contradiction, dir_env_event, dir_pacing_tension, dir_reason_coherence. Rubric: - dir_actor_suitability: eligible-actor fit, explicit user addressee, spotlight balance.   Hard findings may cite authoritative user:* and orch:* refs only. - dir_scene_contradiction: contradiction with committed scene facts.   Hard findings require authoritative refs (ground:*, event:*, canon:*, orch:*, issue:*:status|last_change). - dir_env_event: non-empty environment_event redundancy or implausibility.   Hard allowed for near-duplicate committed environment evidence. - dir_pacing_tension: tension_shift vs scene phase/pressures. Soft by default;   advisory issue:*:required_next_step refs cannot support hard findings. - dir_reason_coherence: reason explains chosen actor/tension/env. Soft only. Authority rules: - Hard findings require valid authoritative_citation.ref_id from the authority references block. - Do not judge missing context, global creative optimality, or replacement actor choice. - Do not emit replacement Director JSON or bind next_actor. If no issues, return {"schema":"hg_semantic_qa_result_v1","evaluation_target_role":"director", "evaluation_pass_id":"<pass id>","overall_result":"pass","findings":[]}.
```

#### A. Host manifest rubric (verbatim)

```
Evaluate the Director decision candidate for defensibility against bounded scene evidence. Judge only these five dimensions:
- dir_actor_suitability: eligible-actor fit, explicit user addressee, spotlight balance. Hard findings may cite authoritative user:* and orch:* refs only.
- dir_scene_contradiction: contradiction with committed scene facts. Hard findings require authoritative refs.
- dir_env_event: non-empty environment_event redundancy or implausibility. Hard allowed for near-duplicate committed environment evidence.
- dir_pacing_tension: tension_shift vs scene phase/pressures. Soft by default; advisory issue:*:required_next_step refs cannot support hard findings.
- dir_reason_coherence: reason explains chosen actor/tension/env. Soft only.
Do not judge missing context, global creative optimality, or replacement actor choice. Output only JSON matching schema hg_semantic_qa_result_v1. Hard findings require valid authoritative ref_id citations from the references block. Do not emit replacement Director JSON or bind next_actor.
```

**Duplication note:** DSH user prompt and Host rubric substantially overlap (same five dimensions and authority rules). Both are model-facing in the same inference (manifest priority 30 + user message).

---

## C. Character

### C.1 `character_orientation`

#### A. DSH `buildCharacterOrientationPrompt` (verbatim)

```
You are the Holy Grail Character knowledge-orientation phase.
Given the upstream scene context, identify what additional knowledge you need to act.
Populate information_gaps with focus questions for the Librarian.
Do NOT output a character move, dialogue, narration, or continuity mutations.
Do NOT reference retrieval backends, candidate ids, or relevance ranks.
Return ONLY one JSON object matching schema hg_character_orientation_v1.
```

---

### C.2 `character_turn` (production round path)

**Provenance:** `LIVE_CHARACTER_PROMPT`; `character_context.py` instruction; `character-phase.mjs`.

#### A. DSH user prompt (verbatim)

```
Respond with ONLY one JSON object. No markdown, no commentary. Required shape exactly: {"move_schema_version":2, "beats":[{"type":"action","action":"<short action text>"},{"type":"speech","dialogue":"<spoken line>"}], "motivation":{"goal":"...","tactic":"...","emotional_driver":"...","risk_level":"low"}, "semantic_evaluation":{"decision":"no_covered_change"}}. Action beats use the key "action" (not description or intent). Speech beats use the key "dialogue". Action-only, speech-only, and mixed beat sequences are all valid when appropriate. risk_level must be lowercase: low, medium, or high.
```

#### A. Host `inference_instruction` (verbatim)

```
Output only valid JSON for move_schema_version 2 with non-empty beats[], motivation object, and semantic_evaluation. Each beat must be type action (key action) or type speech (key dialogue). Action-only, speech-only, and mixed beat sequences are all valid when appropriate to the scene.
```

#### C. Dynamic context (summary)

Upstream manifest from `assemble_character_upstream_contributions`: auth projections, round transcript, director decision, character lane (identity/goals from `character_context_projector.py`), conversation projection, storyteller/plot overlays, librarian bundle (if mapped), memory lanes, private secret, optional `semantic_correction`.

**Descriptive (non-operational) example:** Character lane blocks project card identity, goals, emotions, relationships as structured/desccriptive text — not behavioral rewrite rules.

---

### C.3 `character_inference_slice`

**Provenance:** `character-inference-slice.mjs` `DEFAULT_CHARACTER_PROMPT`; `prepareCharacterContext` via Domain API.

**Lifecycle distinction from production `character_turn`:**

- **Does not run:** orientation, Librarian mediation, plot projection, or semantic evaluation loops.
- **Synthetic Director decision:** Unless `options.directorDecision` is supplied, injects default into manifest prepare:
  ```json
  {"next_actor":"<characterId>","end_round":false,"reason":"character-only slice","environment_event":"","tension_shift":""}
  ```
- **Commit behavior:** On `validateMove` accept, **always** calls `commitMove` with that director decision; loop retries until committed or attempts exhausted. Not a "prompt-only" or commit-optional path in normal operation.

#### A. Slice default user prompt (verbatim)

```
Respond with a single JSON object only (no markdown). Schema: {"move_schema_version":2,"beats":[{"type":"action","action":"..."},{"type":"speech","dialogue":"..."}],"motivation":{"goal":"...","tactic":"...","emotional_driver":"...","risk_level":"low"},"semantic_evaluation":{"decision":"no_covered_change"}}. Action-only, speech-only, and mixed beat sequences are all valid when appropriate.
```

**Shares:** Host `inference_instruction` from `character_context.py` when manifest prepared.

---

### C.4 `character_semantic_evaluation`

#### A. DSH user prompt (verbatim)

```
You are a bounded semantic evaluator for a Character move candidate. Return ONLY one JSON object (no markdown) with schema hg_semantic_evaluation_result_v1. Use overall_result pass|reject_soft|reject_hard and findings[] with dimension R02b|R11|R12|R14|R15. If no issues, return {"schema":"hg_semantic_evaluation_result_v1","overall_result":"pass","findings":[]}.
```

#### A. Host eval instruction (verbatim)

```
Evaluate the candidate for R02b player agency, R11 repetition/stagnation, R12 character fidelity, R14 knowledge/perception, R15 binding continuity. Output only JSON matching schema hg_semantic_evaluation_result_v1. Hard findings require a valid authority ref_id from the references block. Do not supply replacement RP prose.
```

**Fidelity language location:** Dimension names in DSH prompt; expanded definitions enforced in parse/validation layer and Host rubric reference — not lengthy behavioral prose in generative Character prompt.

#### B. Correction instruction (on regen, via `semantic_correction` contribution)

```
Revise your Character move JSON. Address the semantic evaluation findings. Do not invent player-controlled behavior. Output replacement RP as JSON only.
```

---

## S. Storyteller

### S.1 `storyteller_orientation`

#### A. DSH `buildStorytellerOrientationPrompt` (verbatim)

```
You are the Holy Grail Storyteller orientation phase.
Identify what information you need to understand the current narrative situation.
Populate information_gaps with focus questions for the Librarian.
Do NOT prescribe plot outcomes, actor selection, dialogue, narration, or continuity mutations.
Do NOT reference retrieval backends, candidate ids, or relevance ranks.
Return ONLY one JSON object matching schema hg_storyteller_orientation_v1.
```

#### A. Host instruction (verbatim)

```
STORYTELLER ORIENTATION TASK:
Identify what information you need to understand the current narrative situation.
Return focus questions in information_gaps. Do NOT prescribe plot outcomes, actor selection, dialogue, narration, or continuity mutations.
Do NOT reference retrieval backends, candidate ids, or relevance ranks.
```

---

### S.2 `storyteller_assessment`

#### A. DSH `buildStorytellerAssessmentPrompt` (verbatim)

```
You are the Holy Grail Storyteller informed narrative assessment phase.
Given the Librarian bundle digest, assess what is narratively significant now.
Use opportunity framing — not mandates. Cite evidence_refs from bundle entries or authoritative refs.
Do NOT prescribe actor selection, dialogue, narration, structured moves, or continuity mutations.
Return ONLY one JSON object matching schema hg_storyteller_assessment_v1.
```

#### A. Host instruction (verbatim)

```
STORYTELLER INFORMED ASSESSMENT TASK:
Given the Librarian bundle, assess what is narratively significant now.
Use opportunity framing — not mandates. Cite evidence_refs from bundle entries or authoritative refs.
PROHIBITED: next_actor, required_action, mandated_beat, dialogue, narration, structured_move, continuity mutations.
```

---

## L. Librarian

### L.1 `librarian_mediation`

#### A. DSH `buildLibrarianMediationPrompt` (verbatim)

```
You are the Holy Grail Librarian information mediator.
Select and rank ONLY catalog source_id values that contextually help answer the focus questions.
Do NOT choose narrative direction, dramatic theme, or plot prescription.
Do NOT invent new source identities or authoritative facts.
Indirect causal relevance, cross-relationship explanation, and late-emerging significance are in scope.
Lexical overlap alone is insufficient when another supplied item better explains the need.
Return ONLY one JSON object matching schema hg_librarian_mediation_result_v1.
```

#### A. Host mediation tail instruction (verbatim)

```
Return ONLY one JSON object matching schema {"schema": "hg_librarian_mediation_result_v1"}. Use selected_items[].source_id from the catalog only. Do not introduce new source identities or authoritative facts. Synthesis entries must cite source_ids from the catalog. This is suggestive information mediation — not Storyteller narrative advice.
```

**Preceding manifest blocks:** `KnowledgeAccessRequest` JSON, visibility envelope, full mediation catalog JSON (dynamic).

---

### L.2 `librarian_proposal`

#### A. DSH `buildLibrarianProposalPrompt` (verbatim)

```
You are the Holy Grail Librarian post-commit semantic interpreter.
Propose grounded information-level persistence/change candidates ONLY from evidence catalog anchor_id values.
Do NOT invent facts, authority, or continuity commits.
Do NOT use Storyteller PreservationSignal or attention refs as evidence.
Occurrence truth ≠ proposition truth: public_event and committed_move anchors prove what occurred or was said; they do NOT establish objective world truth of claims inside dialogue.
For knowledge_revelation_significance:
- interpretation_scope utterance_occurrence: mark significance of what the Character said/claimed/expressed without endorsing the proposition as world truth. derivation_summary must frame significance of the utterance/claim, not objective ontology.
- interpretation_scope referenced_authoritative_proposition: connect the occurrence to a proposition that already has independent world authority; cite proposition_authority_refs to catalog anchors with world_truth_eligible metadata (e.g. scenario_premise).
- authored_role_private anchors support private epistemic alignment only; they cannot be the sole world-truth authority.
Return ONLY one JSON object (no markdown fences, no commentary).

Required top-level JSON object:
- schema: "hg_librarian_proposal_result_v1"
- proposals: array

Each proposal object MUST include:
- proposal_kind: one of consequence_meaning | information_salience | knowledge_revelation_significance | issue_tension_pressure
- derivation_summary: non-empty string
- confidence: one of confirmed | likely | speculative
- proposed_payload: object matching proposal_kind (see below)
- evidence_anchors: non-empty array of objects with anchor_id and evidence_kind from the catalog only

proposed_payload by proposal_kind:
- consequence_meaning: { tags: non-empty string[] from advancement|complication|revelation|resolution_candidate|relationship_shift|tension_escalation|tension_release }
- information_salience: { subject_ref: string, salience_level: minor|major|pivotal }
- knowledge_revelation_significance: { event_ref, subject_character, revelation_significance_level: minor|major|pivotal, interpretation_scope: utterance_occurrence|referenced_authoritative_proposition, proposition_authority_refs?: string[] (required when interpretation_scope=referenced_authoritative_proposition; must cite world_truth_eligible catalog anchors) }
- issue_tension_pressure: { issue_ref, semantic_unmet_condition, stakes_summary? }

Forbidden:
- Do NOT use field aliases: change_kind, target, type, candidate_id, info_kind — use proposal_kind and proposed_payload.
- Do NOT use string entries in evidence_anchors — each anchor must be an object.
- Do NOT omit the top-level schema field.
- Do NOT use preservation_signal anchors.
- Do NOT invent anchor_id values outside the evidence catalog.

Minimal example (replace anchor_id with a catalog value such as "committed_move:COMMIT_ID"):
<JSON minimal_example from buildLibrarianProposalContractSpec — see source>
```

*(Full minimal JSON example is generated at runtime from `buildLibrarianProposalContractSpec`; see `librarian-proposal-envelope.mjs` L80–101.)*

---

## N. Narrator

### N.1 `narrator_environment_cognition`

#### A. DSH `buildCognitionPrompt` (verbatim)

```
Perform Narrator environmental cognition (#49 / #89 sufficiency).
Return JSON only matching the provided schema.
Assess whether the environmental baseline suffices; if not, list semantic information needs.
Resolve each need into category A, B1, B2, C, or cannot_safely_resolve.
Librarian match means relevant knowledge was found — NOT render sufficiency.
Set response_sufficient per resolution. When insufficient, minimum B2 may follow Host validation.
Never reinterpret match as no_match. Never invent on retrieval/mediation failure.
<COGNITION_SCHEMA JSON — see narrator-environment-cognition-substrate.mjs L8–48>
```

---

### N.2 `narrator_presentation`

#### A. DSH user prompt (verbatim)

```
Render the committed character move as scene narration only. Plain prose, no JSON.
```

*(When NVR enabled, parse path expects JSON envelope — Host `inference_instruction` carries full render + NVR contract; DSH prompt is minimal.)*

#### A. Host `build_narrator_render_prompt` — primary v2 structured-move path (verbatim core)

See full text in `v2/domain/modules/narrator_render_instruction.py` L46–66:

```
Render the following structured character turn (v2 ``beats[]``) into third-person past-tense scene narration.

CHARACTER: {char_name}
STRUCTURED MOVE (authoritative; render only this visibility scope; do not invent speech):
{structured_move JSON}
OPTIONAL ENVIRONMENT EVENT: {environment_event}
{ESTABLISHED ENVIRONMENTAL BASELINE block if present}
{environmental_response_obligations block if present}
SCENE CONTEXT:
{scene_context}

IMMERSIVE ENVIRONMENT DUTY (#49 / #89):
- Make the physical environment perceptibly present through selective concrete detail (spatial relationships, lighting, sound, texture, temperature, smell, visible wear, motion, atmosphere).
- Respond physically to what the user/character actually did; use immediate_user_turn_context for current-turn player intent and triggering_user_context when authoritative occurrence evidence is present.
- Preserve established environmental facts from the baseline; do not reinvent continuity-bearing properties each turn.
- When environmental response obligations are present, communicate communicate_grounded obligations concretely; do not substitute inferred purpose for requested observable detail.
- Use ephemeral sensory texture for liveliness where appropriate; avoid sterile action-summary narration and generic irrelevant filler.
- Do not invent material facts when baseline or cognition marked bounded_refusal/failure; omit rather than guess.
- Vary focus and phrasing; avoid full re-description every turn unless materially expected.

RULES:
1. Preserve ``beats[]`` order: do not reorder beats.
2. For each ``type: speech`` beat, the ``dialogue`` string must appear in your output as a contiguous **verbatim** substring, in the same order as in ``beats`` (you may add connective narrator prose between beats; adjacent speech may be merged in prose only if every speech line still appears as an exact, ordered substring).
3. For ``type: action`` beats, you may paraphrase the action text in third person; do not treat action text as a verbatim substring requirement.
4. Do not add new spoken lines or quoted speech that are not substrings of the provided speech lines (narrator connective prose without quotes is allowed between beats).
5. If you include optional environment event material, work it in naturally; do not contradict authoritative scene progression, environmental baseline, or the structured move — omit environment material when it conflicts.
6. Only describe this character for action/speech; no other character dialogue.
7. Be concise but not sterile — roughly 2-8 sentences when environmental response is materially relevant.
8. Write in third person past tense.

{NARRATOR_VISIBILITY_OUTPUT_INSTRUCTION}
```

#### A. `NARRATOR_VISIBILITY_OUTPUT_INSTRUCTION` (verbatim)

See `narrative_visibility_prompt.py` L16–47 (full block in source file; includes OUTPUT FORMAT JSON schema, SEMANTIC UNIT RULES, COVERAGE rules).

---

### N.3 `narrator_semantic_qa`

DSH `buildNarratorEvaluatorPrompt` and Host `NARRATOR_SEMANTIC_QA_RUBRIC` (`narrator_semantic_qa_context.py` L38+) — same pattern as Director QA: overlapping five-dimension rubric in both user prompt and manifest (priority 30).

**Fidelity dimensions (verbatim excerpt from Host rubric):**

```
- nar_attribution_error: material misassignment of speaker, actor, addressee, or ownership of an action/dialogue beat. ...
- nar_committed_contradiction: material factual contradiction of committed move, authoritative scene state, ...
- nar_action_intention_distortion: material alteration of what a character did, attempted, intended, ...
- nar_psychological_invention: material unsupported affirmative interior claims. Apply the closed-world rule: ...
- nar_framing_distortion: tone, metaphor, causal framing, or descriptive treatment that materially changes source meaning ...
```

---

## PC. Plot cognition (auxiliary)

### PC.1 `plot_cognition_epistemic_eval`

#### A. `buildEpistemicProjectionEvalPrompt` (verbatim)

```
You are the Layer-B Character epistemic projection evaluator.
Return ONLY one JSON object (no markdown fences, no commentary) with schema hg_epistemic_projection_eval_v1.
Required field: verdict — exactly one of: pass, withhold, rewrite_required, evaluator_unavailable.
Include rationale and/or forensic_rationale (string).
Optional: leak_indicators (array of strings).
When verdict is rewrite_required, include regeneration_guidance object with:
  schema: "hg_regeneration_guidance_v1"
  safe_constraints: non-empty string array
  violation_class: one of third_party_private_knowledge, withheld_basis_exposure, global_cognition_leak, over_specific_prospective, relationship_boundary, other
Do NOT use alternate fields such as allowed, permitted, leakage, or epistemic_leakage.
Do NOT wrap the verdict in alternate JSON shapes.
Minimal pass example: {"schema":"hg_epistemic_projection_eval_v1","verdict":"pass","rationale":"Candidate stays within permitted envelope."}
Minimal withhold example: {"schema":"hg_epistemic_projection_eval_v1","verdict":"withhold","rationale":"Candidate leaks private knowledge."}
```

### PC.2 `plot_cognition_init`

See `buildPlotCognitionInitPrompt` in `plot-cognition-init-envelope.mjs` L27–44 (full verbatim in source).

### PC.3 `plot_cognition_update` / replan

Large schema-scaffolding prompt in `plot-cognition-update-envelope.mjs` including `plotCognitionUpdateEnvelopeSemantics()` block (L19–34 verbatim):

```
Execution-envelope semantics (#61 — do not confuse strategic revision with package revision):
- replan_required (on update_proposal): true when authoritative developments materially invalidate prior_operative_cognition and a replacement/restructured plan is required.
- update_evaluation.overall_result=accept: the generated update package itself is internally complete and acceptable for commit. This MAY coexist with replan_required=true.
...
```

### PC.4 `character_advisory_generation`

**Coverage:** dynamic-context-only distinction documented. Prompt assembled by Host plot cognition advisory generation endpoints from prepared projection context; no standalone constant in `live-inference-prompts.mjs`. See `plot-cognition-orchestration.mjs` call sites.

---

## AUX. Auxiliary player/opening paths

### AUX.1 `opening`

**DSH:** `OPENING_PROMPT` = `Write the scene opening prose following the authoritative context and instructions.`

**Host:** `build_opening_generation_instruction()` in `opening_prompt.py` (verbatim):

```
Write a single narrator-style scene opening for the player.
Rules:
- Use only facts already established in the authoritative context below.
- Do not invent new canonical world facts, locations, props, or events.
- Do not resolve future player choices or speak for the player character.
- Present tense, immersive prose, ending on a natural hook for the player's first reply.

Scene premise (authoritative): {premise_block}
Present characters: {cast_label}

{OPENING_VISIBILITY_OUTPUT_INSTRUCTION}
```

### AUX.2 `opening_segmentation`

Manifest includes `OPENING_SEGMENTATION_OUTPUT_INSTRUCTION` (`narrative_visibility_prompt.py` L76–104 verbatim in source).

### AUX.3 `player_visibility_triage`

**DSH task + user wrapper:**

`PLAYER_VISIBILITY_TRIAGE_TASK_PROMPT`:
```
Evaluate whether the player-authored turn is affirmatively safe for uniform projection to all present Characters without semantic decomposition. When any span may be internal, concealed, directed, private, authorial exposition, or ambiguous, answer false.
```

User prompt = task + `\n\nPLAYER SOURCE:\n` + player content.

**Manifest:** `PLAYER_VISIBILITY_TRIAGE_OUTPUT_INSTRUCTION` (`narrative_visibility_prompt.py` L152–192 verbatim in source).

### AUX.4 `player_decomposition`

**DSH:** `PLAYER_DECOMPOSITION_TASK_PROMPT`:
```
Decompose the player-authored turn into semantic perceptual units with verbatim excerpts only.
```

**Manifest:** `PLAYER_SEMANTIC_DECOMPOSITION_OUTPUT_INSTRUCTION` (`narrative_visibility_prompt.py` L107–146 verbatim in source).

**Retry headers (attempt 2):** `ATTEMPT_2_OUTPUT_RETRY:` + guidance from `RETRY_GUIDANCE` map in `player-decomposition-phase.mjs`.

---

## HARNESS. Non-production

| Path | Note |
|------|------|
| `scenario-harness/certification-evaluator.mjs` | `storyteller_certification_eval` — rubric for tier-2 certification |
| `scenario-harness/instrumented-inference.mjs` | Wraps production substrate; no alternate prompts |

---

## F-136-02 verbatim duplication evidence (Director / Character)

### Director — side-by-side

| Text element | DSH `LIVE_DIRECTOR_PROMPT` | Host `inference_instruction` |
|--------------|---------------------------|------------------------------|
| JSON-only framing | **Yes:** "Respond with ONLY one JSON object. No markdown, no commentary." | **No** |
| Key list | **Yes:** typed keys `(string)`, `(boolean)` | Partial: names only |
| `tension_shift` enum | "Set tension_shift to exactly escalate, soften, or steady." | "tension_shift must be escalate, soften, or steady." |
| `environment_event` empty string | "use an empty string instead of repeating a recent accepted environment development" | "use an empty string rather than repeating a recent accepted environment development" |
| Actor selection guidance | **Yes:** "Select next_actor from the eligible cast in context." | **No** |
| `end_round` default | **Yes:** "Set end_round false unless the scene should stop." | **No** |

**Identical/overlapping core:** All five JSON keys + tension_shift enum + environment_event optional/repeat rule.

**Both model-facing in same inference:** Yes — manifest contributions registered first; DSH user prompt last.

**Drift risk:** Independent edits to `live-inference-prompts.mjs` vs `director_context.py`.

**Purpose split (observed):** DSH carries transport/format strictness; Host carries domain instruction in manifest lane for forensic manifest capture.

### Character — side-by-side

| Text element | DSH `LIVE_CHARACTER_PROMPT` | Host `inference_instruction` |
|--------------|----------------------------|------------------------------|
| JSON-only framing | **Yes** | **No** (starts "Output only valid JSON") |
| Full example JSON shape | **Yes** (inline example with placeholders) | **No** |
| `action` vs `description` key rule | **Yes:** explicit | **Yes:** "key action" |
| `risk_level` lowercase enum | **Yes** | **No** |
| Beat sequence validity | **Yes** | **Yes** (wording differs slightly) |
| `semantic_evaluation` in schema | **Yes** in example | **Yes:** "and semantic_evaluation" |

---

## F-136-03 classification challenge (Character chain depth)

| Claim type | Evidence status |
|------------|-----------------|
| **Observed call count (production Character turn)** | Objective: orientation → mediation → (optional epistemic eval + advisory gen) → move → semantic eval = 3–5+ `runEphemeralInference` calls traceable in `character-phase.mjs` / `character-cognition-substrate.mjs` |
| **Token/context volume** | Partially evidenced: each call carries full or partial manifest; exact token counts **not** measured in #136 |
| **Latency/cost** | **Not directly evidenced** in #136 static inspection; #112 controlled experiments cover PVR not full cognition chain |
| **Demonstrated quality harm from depth** | **Not evidenced** — no controlled A/B skip tests in this assessment |
| **Inferred risk** | Additional calls increase cost surface and failure modes; skip flags exist (`skipStorytellerCognition`, projection lifecycle conditional) |
| **Unknown benefit** | Orientation/mediation may reduce knowledge-boundary errors — **runtime evidence required** |

**Revised classification:** F-136-03 reclassified from **`architectural debt`** to **`observation`** (documented call-depth structure) with **runtime-evidence uncertainty** for cost/quality tradeoff. Not a confirmed defect.

---

## F-136-08 / F-136-10 scope containment

| Finding | #136 role | Remediation ownership |
|---------|-----------|----------------------|
| F-136-08 Player PVR reliability | Visible in auxiliary prompt corpus (§AUX.3–4); informs system map | **#112** and successors — not #136 implementation |
| F-136-10 Narrator env cognition duplication | Cross-reference only; prompt corpus shows cognition + obligation text paths (§N.1–2) | **#131** — not absorbed into #136 |

---

## Shared sources index

| File | Inference kinds consuming |
|------|---------------------------|
| `live-inference-prompts.mjs` | director_turn, character_turn, narrator_presentation |
| `narrative_visibility_prompt.py` | narrator_presentation, opening, opening_segmentation, player_decomposition, player_visibility_triage |
| `narrator_render_instruction.py` | narrator_presentation (via Host manifest) |
| `opening_prompt.py` | opening (Host manifest) |
| `*-envelope.mjs` | respective cognition/mediation/proposal kinds |
| `director_context.py` / `character_context.py` | director_turn / character_turn Host instructions |
| `director_semantic_qa_context.py` / `narrator_semantic_qa_context.py` | QA manifest rubrics |
| `semantic_evaluation_context.py` | character_semantic_evaluation Host rubric |
