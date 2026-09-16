## LH-0 final consumer-value qualification complete (P1 remediation + one A/B/C/D tranche)

**Candidate:** `4b491e70d5a958aa5a7fb36856f40b50b94122dd`  
**Run:** `data/investigation_runs/issue201-lh0-consumer-value-verification-2026-09-16T01-08-28-579Z`  
**Record:** `governance/records/issue-201-lh0-consumer-value-2026-09-16.md`

### P1 harness fix
Restored authoritative `runPlayerPvr` → `recordUserTurn` → `runA2BeatRound` path. Pre-live gates 15/15 PASS.

### T5 guest-policy fork (frozen neutral question; fact-only persistent payload)

| Arm | Sequence | Trigger | Fact | Semantic | E/F/G/H |
|-----|----------|---------|------|----------|---------|
| LH-A | `LH0-LIVE-lh_a-1789520908588` | ✓ | absent | S1 (no prohibition) | counterfactual |
| LH-B | `LH0-LIVE-lh_b-1789521295393` | ✓ | present | S3 (presentation) | E/F/G/H ✗ (classifier) |
| LH-C | `LH0-LIVE-lh_c-1789521778526` | ✓ | present | S3 | E/F/H ✓, G ✗ |
| LH-D | `LH0-LIVE-lh_d-1789522263172` | ✓ | present | S3 | E/F/H ✓, G ✗ |

**LH-1A readiness:** B/C/D all **No** (universal G failure; LH-B classifier/matrix split).

### Interpretation
- Player→PVR→history→Character input contract **validated** (fixes pre-fix “applicant hasn’t asked” failure mode).
- Persistent arms **can** communicate authoritative guest policy when fact is supplied; LH-A does not.
- LH-B shows semantic/classifier adjudication divergence worth Governance review.
- K6 not remediated; T6 curfew excluded.

**Next:** Governance decision on selective LH-1A vs further evidence-contract work. Issue #201 remains open.
