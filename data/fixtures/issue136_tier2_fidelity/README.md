# Issue #136 Tier-2 fidelity validation fixtures

**Adjudicator-facing only.** Truth records and validation character cards for the #136 Tier-2 semantic campaign.

These files define supported / ambiguous / unsupported behavioral envelopes for forensic adjudication. They are **not** injected into model-facing prompts or manifests.

## Layout

- `truth/` — per-fixture adjudication truth (evaluator-facing)
- `cards/` — validation-only character cards copied into harness `HG_DATA_DIR/characters/` at campaign runtime

## Usage

See `governance/records/issue-136-tier2-campaign-spec.md` and `v2/rp_runtime/scripts/run-issue136-tier2-campaign.mjs`.
