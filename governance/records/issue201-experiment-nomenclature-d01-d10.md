# Issue #201 — Canonical Package D Experiment Nomenclature (D-01–D-10)

**Date:** 2026-09-14  
**Authority:** Reconciles `governance/records/issue-201-packages-abc-investigation-2026-09-14.md` (original definitions) with Stage-1/Stage-2 execution labels.  
**Rule:** Historical records are not rewritten; mislabels are documented here.

---

## Canonical mapping table

| ID | Original definition (Packages A–C) | Current intended definition | Executed? | Aliases / mislabels discovered |
|----|-----------------------------------|----------------------------|-----------|--------------------------------|
| **D-01** | Storyteller preamble stack skip (`skipStorytellerCognition` + plot resume) | Full preamble bypass: `skipStorytellerCognition` + `skipPlotCognitionOrchestration` | **Yes** — Stage-2 **EXP-1** | Stage-1 ranked as D-01; matches |
| **D-02** | Plot cognition init skip on opening | Plot cognition init/update bypass (subset of D-01) | **No** | Not separately executed; folded into D-01/EXP-1 |
| **D-03** | Character orientation skip | Character knowledge cognition bypass: `skipCharacterKnowledgeCognition` | **Yes** — Stage-2 **EXP-3** | Stage-1 incorrectly mapped EXP-3 to "D-01-partial / Storyteller-only" — **superseded** by Governance Stage-2 mandate |
| **D-04** | Narrator env cognition tiering / skip | Env cognition cost/value isolation | **No** | Needs investigation hook |
| **D-05** | Librarian S2a @character bypass | Mediation bypass at character lane | **No** | Distinct from D-03 orientation-mediated mediation |
| **D-06** | Director semantic QA off | `directorSemanticQaEnabled: false` | **Yes** — Stage-2 **EXP-2** | Matches |
| **D-07** | Character semantic eval off | Disable character semantic evaluation | **No** | High risk; not authorized |
| **D-08** | Combined compact topology (A3) | Full topology reduction experiment | **No** | Largest blast radius |
| **D-09** | PVR tiering vs full decomposition | Uniform+verify path only | **No** | Not authorized |
| **D-10** | Post-commit parallel join slimming (`narrator-only critical; defer plot/S4`) | **`skipLibrarianProposalGeneration`** / post-commit join cost (Stage-1 harness note) | **No** | **Mislabel risk:** Stage-2 tranche report prose said "D-10 post-commit join" referring to Stage-1 rank #6 (`skipLibrarianProposalGeneration`), which is the **operational hook name** for the Packages A–C D-10 concept (post-commit parallel join). Same experiment; different surface names. Not a different experiment. |

---

## Stage-2 tranche EXP ↔ D-ID mapping (authoritative for executed work)

| Tranche EXP | Canonical D-ID | `roundOptions` |
|-------------|----------------|----------------|
| EXP-1 | D-01 | `skipStorytellerCognition` + `skipPlotCognitionOrchestration` |
| EXP-2 | D-06 | `directorSemanticQaEnabled: false` |
| EXP-3 | D-03 | `skipCharacterKnowledgeCognition` |

---

## Corrections applied

1. **Stage-1 record §8** listed EXP-3 as Storyteller-only (D-01-partial) — **historical only**; Governance Stage-2 replaced with D-03 orientation bypass.
2. **D0 baseline record §26** third tranche item still said "Storyteller-only" — superseded; see refinement record.
3. **"D-10 post-commit join"** in Stage-2 report = **D-10** per Packages A–C; implementation hook = `skipLibrarianProposalGeneration` (Stage-1 rank table).

---

## Not executed / not next without Governance gate

D-02, D-04, D-05, D-07, D-08, D-09, D-10, Storyteller-only partial, Librarian bypass, PVR tiering, compact topology.
