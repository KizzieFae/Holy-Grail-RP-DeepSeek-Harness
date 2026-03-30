# Registry Validation Report

## Scope

This document records completion of the current registry-backed resolved-outcome phase for structured scene facts in Holy Grail RP.

Validated aspects:

- `lodging.sleep_surface`
- `communication.housing_call`
- `medical.suppressant_formulation`
- `access.location_entry`

## System Summary

The resolved-outcome system is a registry-driven architecture for durable scene facts. Each aspect is defined as a registry row that supplies its candidate parser, slot identity rule, value contract, promotion behavior, and outcome identifiers. The engine applies those definitions generically, without per-aspect orchestration or continuity special-casing.

At runtime, structured move output is parsed into aspect candidates, validated against the aspect contract, and compared against the current active slot state. When a candidate is accepted, continuity stores it as a resolved outcome. Continuity is the source of truth; scene grounding is a read-only projection of the currently active outcomes into prompt-facing settled facts.

## Aspect Coverage

| Aspect | Type | Slot model | Value shape |
|--------|------|------------|-------------|
| `lodging.sleep_surface` | Assignment | `aspect_id::subject_id` | `{ "surface_id": bounded surface id }` |
| `communication.housing_call` | Terminal event | `aspect_id::scene` | `{ "status": "completed" | "failed" }` |
| `medical.suppressant_formulation` | Subject-bound attribute | `aspect_id::subject_id` | `{ "status": "compatible" | "incompatible" }` |
| `access.location_entry` | Normative permission | `aspect_id::subject_id::location_id` | `{ "location_id": bounded location id, "status": "allowed" | "denied" }` |

Together these cover four major state classes:

- assignment state
- terminal event state
- subject-scoped attribute state
- deontic permission state

## Validation Summary

### Automated coverage

Targeted tests were added or updated across continuity, grounding, prompt/schema, and character-loading paths. Validation covered:

- promotion of valid structured outcomes
- identical-value no-op behavior
- supersession within a slot
- slot isolation across subjects and subject-location pairs
- grounding rebuild from active resolved outcomes
- bounded-schema validation for structured move fields

The full Python test suite was run after the implementations and passed for the completed phase.

### Live validation

Live validation confirmed that the implemented aspects behave correctly in runtime conditions:

- `lodging.sleep_surface` validated assignment-style settlement and slot replacement
- `communication.housing_call` validated continuity-owned terminal settlement and removal of competing lexical emission for new turns
- `medical.suppressant_formulation` validated subject-scoped attribute promotion and subject isolation
- `access.location_entry` validated bounded permission state, scene-slot validation, and runtime supersession

### Edge-case stress pass

The focused stress pass for `access.location_entry` confirmed that the refined emission discipline holds under adversarial phrasing:

- ambiguity did not promote
- control language did not promote
- soft discouragement did not promote
- mixed permission promoted only when a clear bounded state existed
- explicit permission and denial still promoted reliably
- invalid `location_id` values were not remapped and were rejected as `invalid_location_id`
- conflicting speakers produced correct same-slot supersession with one active slot remaining

## Key Guarantees

The current system is validated to provide the following guarantees within scope:

- Registry-driven processing: aspect behavior is supplied by registry definitions rather than engine branches
- Deterministic slot identity: each aspect has a stable slot model that determines replacement boundaries
- Continuity truth ownership: active resolved outcomes are the authoritative scene-state record
- No-op behavior: reasserting the identical active value does not create duplicate active state
- Supersession correctness: a new different value for the same slot replaces the prior active outcome
- Slot isolation: changes in one subject or subject-location slot do not leak into another slot
- Grounding consistency: prompt-facing settled facts rebuild from active outcomes and reflect current state cleanly
- Schema boundedness: aspect value domains remain intentionally narrow and validated at parse/promotion time
- No engine special-casing: the four validated aspect types work inside the same generic resolved-outcome flow

## Known Limitations

The current phase is stable, but intentionally bounded:

- Structured promotion still depends on model emission discipline at generation time
- Ambiguity must continue to be preserved by prompt instructions rather than inferred into settled state
- There is no general revocation system in this phase; replacement is modeled through supersession within a slot
- Grounding exposes current active facts, not full historical outcome chains
- The `supersedes` chain is authoritative in continuity, but grounding is optimized for present-state clarity rather than full historical trace display
- Bounded schemas are intentional and do not attempt to encode richer causality, authority, duration, or justification metadata

## Conclusion

The registry-based resolved-outcome system is validated and stable for the current scope.

Across four aspect classes, the system now demonstrates:

- generic registry-backed processing
- deterministic slotting and replacement behavior
- continuity-owned durable truth
- clean grounding projection
- bounded, testable structured contracts

This completes validation of the current registry aspect model across the major state types targeted for this phase.
