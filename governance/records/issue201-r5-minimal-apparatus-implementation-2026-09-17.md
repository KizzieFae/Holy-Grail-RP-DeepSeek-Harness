# Issue #201 — Minimal R5 Apparatus Implementation Record

**Date:** 2026-09-17  
**Subphase:** R5 persistence-unique discrimination apparatus (mock/deterministic only)  
**Live R5-A1/B1:** NOT authorized  

## Selected fork

**`FORK-R5-TRIAL-MEAL-ALCOVE`** — trial-week staff meals in pantry alcove vs household dining table during formal guest meals.

## Rejected

- **`FORK-R5-SERVICE-THRESHOLD`** (portico/delivery) — stimulus/establishment leakage risk per Governance.

## Qualification

```
node v2/rp_runtime/scripts/issue201-r5-seam-verification.mjs --qualify
node --test v2/rp_runtime/tests/issue201-r5-apparatus.test.mjs
```

G1–G8: PASS (deterministic). Horizon: **14 turns** (decision T14; aging via six-turn transcript slice excluding establishment).

## Frozen hashes

| Artifact | SHA-256 |
|----------|---------|
| Fixture | `896377dcc6a6cd1de9e92db262fb65c7cffb66f7764b8eddc4a47498d67d4068` |
| Policy | `bbf280f06a57466709e351ce57a86ea9188dfc63e70624a3752dceb66dfadc82` |
| Causal design | `26abbc25a866e52ca31b6caba49be614560b37bdc4a589f4128841d38d569b13` |

## Live entry (when authorized)

Extend LH-1B runner with R5 campaign plan (`buildR5CampaignPlan`) — not wired for live in this commit.
