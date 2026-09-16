## LH-0 final turn-alignment verification complete

**Candidate:** `de77f96` (two-clock turn-alignment)  
**Run:** `data/investigation_runs/issue201-lh0-turn-aligned-verification-2026-09-16T00-12-36-622Z`  
**Record:** `governance/records/issue-201-lh0-turn-alignment-2026-09-16.md`

### Timing root cause — fixed

Fixture clock (`lh0FixtureTurnIndex`) now governs obligation eligibility and post-commit classification; runtime `cognitionTurnIndex` retained for manifest binding only.

### Deterministic gates

- Timing validation: 19/19 PASS
- Semantic validation: 28/28 PASS

### Final tranche A–J (one arm each, no retries)

| Arm | A–D | E/F/G/H | LH-1A |
|-----|-----|---------|-------|
| LH-A | n/a (control) | n/a | n/a |
| LH-B/C/D | **PASS** | **FAIL** | **No** |

### Key evidence

- T1–T4: deferred obligations withheld from Character (char_due 0)
- T5: guest-policy fork — projection + semantic receipt **before** cognition (`LH0-OBL-DEFERRED`, `LH0-OBL-LATER`)
- T6: receipt continues; curfew fork links to `LH0-OBL-IMMEDIATE` (director consumer only — fixture limitation)

### Interpretation

Prior E/F/H failures were timing-contaminated. Post-alignment, seam A–D pass but Character did not produce frozen choice-class behavior despite correct semantic receipt at T5. Counterfactual: same outcome/indeterminate vs LH-A.

**LH-0 instrument substantially complete. LH-1A NOT ready. K6 independently reportable.**

Governance decision required on LH-0 completion vs fixture/evidence-contract follow-up.
