# Selector-quality phase — closure reference

## 1. What changed (code-level)

### New module: `rp_app/turn_selection_preference.py`

| Symbol | Responsibility |
|--------|----------------|
| `resolve_participant_key` | Maps a display name or variant string to a canonical agent key from `participant_names` (optional `display_name_for_key`). |
| `build_routing_preference_snapshot` | Builds deterministic advisory fields from `responder_obligation` and `action_responsibility`: `preference_candidate`, `preference_source` (`responder_obligation` \| `action_responsibility` \| `none`), `preference_class` (`advisory` \| `none`), plus booleans for which hints are active. Precedence: if obligation is active with `confidence == "high"` and a valid primary in `available_actors`, that wins; else same for action responsibility. |
| `sanitize_semantic_turn_selection_assessment` | Post-processes the LLM JSON for turn selection: clears `should_flag_direct_address_miss` when `direct_address_target` is empty/unresolvable or resolves to `selected_actor`; in the match case sets `supports_selected_actor` true and normalizes `direct_address_target` to the resolved key. |
| `build_turn_selection_diagnostics_for_audit` | Compact struct for audits: `validated_pick`, optional `final_pick`, routing snapshot fields, `reconciled_issues`, and a `semantic_effective` slice (`supports_selected_actor`, `direct_address_target`, flags, `confidence`). |
| `format_turn_selection_diagnostic_block` | Single human-facing line: `validated_pick`, `final_pick`, optional `routing_note=pick_changed_after_validation`, advisory preference line, `preference_aligned_vs_validated`, and `notes` from reconciled human issues. |

### Modified: `rp_app/app_turn_director.py`

- **`_REPLY_EXPECTATION_SIGNALS`**: `frozenset` of signal names (`explicit_question`, `accusation_or_challenge`, `required_response_to_prior_move`). `responder_obligation` candidates are kept only if the actor’s signals intersect this set (directed address / executor-only stacks no longer activate obligation alone).
- **`_ACTION_RESPONSIBILITY_DIRECTIVE_CUES`**: includes e.g. `turn around` (concrete directive vocabulary alongside existing cues).
- **`_compute_action_responsibility_hint`**: if `responder_obligation.get("active")`, returns the empty responsibility hint immediately (no competing hint).
- **`choose_next_actor`**: builds `routing_snapshot`; passes `routing_preference=routing_snapshot` into semantic assessment; computes `effective_semantic_assessment` via `sanitize_semantic_turn_selection_assessment`; calls `reconcile_turn_selection_issues` with `selected_actor`, `participant_names`, `display_name_for_key`; uses **effective** assessment in `filter_selection_issues_for_human_log`; appends validation + `format_turn_selection_diagnostic_block` **after** progression override and participation fairness (`validated_pick` = Director parse output, `final_pick` = post-processing `next_actor`); records `turn_selection_diagnostics` on selection attribution and audit metadata (`turn_selection_diagnostics`, `semantic_turn_selection_assessment_effective` alongside raw semantic payload).

### Modified: `rp_app/semantic_validation.py`

- **`reconcile_turn_selection_issues`**: Optional kwargs `selected_actor`, `participant_names`, `display_name_for_key`; runs sanitization when names/pick present and no parse error; filters legacy addressee-style strings via `_is_semantic_addressee_style_issue` (prefix `Selected actor ignored direct address preference` or `Addressee advisory mismatch (semantic):`); emits addressee mismatch only when `should_flag_direct_address_miss` remains true and resolved `direct_address_target` ≠ `selected_actor`; still appends repeat-spotlight and semantic non-support strings per effective flags.
- **`assess_turn_selection_decision_semantics`**: Optional `routing_preference`; payload includes it; prompt instructs that preference is advisory, `direct_address_target` must be from `available_actors`, and miss/support flags must align when `decision.next_actor` equals the natural addressee.
- **`filter_selection_issues_for_human_log`**: Unchanged contract in docstring—human log / reason formatting only; does not alter `next_actor`.

### Related (unchanged contract, boundary reference)

- **`validate_turn_selection_decision`** (`response_validation_selection.py`): Deterministic checks (participant membership, `available_next_actors`, offstage, pending forced speaker, continuation override with C2 skip). Produces issue strings; does not implement semantic assessment.

---

## 2. Behavioral guarantees

### Responder obligation vs action responsibility

**Hard rule: when `responder_obligation.active` is true, `action_responsibility` must not compete.**

Enforcement: `_compute_action_responsibility_hint` returns the inactive (empty) responsibility hint whenever `responder_obligation` is active, so no `action_responsibility` payload or director hint is emitted for that beat.

- **`responder_obligation` activates only** when at least one candidate carries a **reply-expectation** signal (`explicit_question`, `accusation_or_challenge`, or `required_response_to_prior_move`). Directed address plus executor-only cues **without** those signals does **not** activate obligation, so **action responsibility** may apply for bounded-action/directive classification when obligation correctly stays inactive.

### Diagnostic consistency

- **Sanitization** removes direct-address miss flags when the semantic target cannot be resolved to a participant key or when it **equals** the validated selected actor; in the equal case **`supports_selected_actor` is forced true** for the effective assessment.
- **Reconciliation** adds **`Addressee advisory mismatch (semantic): preferred X vs selected Y`** only when a resolved preferred addressee **differs** from `selected_actor`.
- **Human-facing diagnostics** distinguish **`validated_pick`** (input to semantic validation: Director’s parsed `next_actor` before later routing layers) and **`final_pick`** after progression override and participation fairness, with **`routing_note=pick_changed_after_validation`** when they differ.
- **Audit / attribution** carry **`turn_selection_diagnostics`** and **`semantic_turn_selection_assessment_effective`** for a stable, structured view; **`semantic_flag_summary`** uses the **effective** assessment where applicable.

### Validation vs enforcement

- **Semantic turn-selection assessment** informs reconciled issue strings and optional **`decision["reason"]`** appendices; per module comments it does **not** change **`next_actor`** or other machine fields except reason text (and low-confidence suppression via `filter_selection_issues_for_human_log` when deterministic issues are empty).
- **Continuity remains the sole authority; these modules do not modify continuity state.**

### Failure modes reduced (by construction)

- **Self-contradictory addressee messaging**: e.g. implying “ignored preference” for the same actor as the validated pick after key resolution.
- **Spurious direct-address miss** when `direct_address_target` is missing or not mappable to a participant key.
- **Misleading single “pick” in logs** when participation fairness or other post-Director steps change `next_actor` without labeling that shift (addressed via validated vs final pick).

### Not guaranteed

- **Non-zero semantic disagreement** (e.g. `Semantic turn_selection review did not support selected actor for current beat`) is **expected and acceptable**: semantic validation is **advisory**, so the model may flag tension with the Director’s choice without that being a defect. **Zero such notes is not a design target.**
- Perfect compliance by the semantic validator with every prompt constraint on every turn.
- Absence of progression or selection failures in all runs—the **diagnostic pipeline** is what is tightened; runtime outcomes remain subject to model and scenario variability.

---

## 3. Design intent (bounded)

- **Responder obligation precedence over action responsibility:** Two advisory channels targeting the “who speaks next” question would conflict when one beat is primarily a **reply** and the other a **compliance/action** frame. Gating action responsibility whenever obligation is active **removes parallel, conflicting Director hints** on the same beat; tightening obligation activation to **reply-expectation signals** keeps **physical/concrete directives** on the **action responsibility** path when obligation correctly stays inactive.

- **Diagnostics restructured:** Routing layers after the Director parse can change `next_actor`; logging a single “pick” conflated **what was validated** with **what the runtime selected**, producing misleading traces. Splitting **`validated_pick` / `final_pick`** and stamping **`routing_note`** when they diverge makes logs and audit structs **aligned with the actual pipeline order**.

- **Semantic validation remains advisory:** Turn selection semantics are **judgment from a separate LLM call**; they are **merged into human-visible reason text** and audits under explicit confidence gating, while **hard routing** (e.g. forced speaker, continuation handling in `choose_next_actor`) and **deterministic validation** remain the structured gate for invalid parses relative to pools and override rules. Keeping semantics **non-overriding** preserves a clear boundary: **structured eligibility and routing first**, **narrative judgment as annotation**, consistent with “validation is advisory only.”
