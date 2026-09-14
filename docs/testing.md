# Testing

Use this document when changing Python or RP runtime code in Holy Grail RP.

---

## Default pytest scope

From the **repository root**:

| Suite | Command | Scope |
|-------|---------|-------|
| Domain contracts | `python -m pytest v2/domain/tests/ -q` | `v2/domain/modules/` semantics |
| Integration | `python -m pytest v2/tests/ -q` | Domain Host, architecture invariants |
| RP runtime | `cd v2/rp_runtime && npm test` | DSH orchestration (starts Domain Host subprocess) |

**Known xfail:** `v2/tests/test_presence_descriptive_exit_regression.py` — descriptive-exit presence regression (tracked separately).

---

## Environment

Provision the canonical interpreter once:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Optional overrides: `HG_PYTHON_EXECUTABLE`, `HG_DATA_DIR`, `HG_SESSIONS_DIR`.

Live inference tests require `DEEPSEEK_API_KEY` when exercising real provider paths.

---

## Test strategy

- Run the **smallest relevant suite** first.
- Expand to integration or runtime tests when touching Domain Host wiring, DSH orchestration, or cross-module contracts.
- Do not treat a manual UI session as a substitute for regression tests.
- Add focused tests when changing public behavior without coverage.

---

## Manifest projection policy parity (#134, #206)

Python `manifest_projection_policy.py` and Node `manifest-projection-policy.mjs` must stay synchronized. The parity invariant is enforced in **both** normal validation paths:

| Path | Command |
|------|---------|
| Domain suite | `python -m pytest v2/domain/tests/test_manifest_policy_parity.py -q` |
| RP runtime suite | `cd v2/rp_runtime && node --test tests/manifest-policy-parity.test.mjs` (also runs under `npm test`) |

Run the relevant path (or both) when editing either policy module.

---

## Domain library guidance

When changing `v2/domain/modules/`:

- Prefer tests beside behavior in `v2/domain/tests/`.
- For continuity, orchestration, or validation fixes, check downstream effects on turn selection, session persistence, and audit output shape.
- For scenario manifest changes, extend manifest regression tests under `v2/domain/tests/test_*manifest*.py`.
- For #40 B2 issue-pressure semantic overlay changes, run `python -m pytest v2/domain/tests/test_librarian_proposal_b2_issue_pressure.py -q` plus `test_librarian_proposal_s4b.py` and `test_director_context_digests.py` regressions.

---

## RP runtime guidance

Domain Host integration tests start a supervised Python subprocess via `startDomainApi` / `startDomainHost`. Pass the active Node test context as `options.t` so teardown is registered immediately (`t.after`) even when assertions fail. Prefer `reserveLocalPort()` over ad-hoc random port windows to avoid collisions with stale local hosts.

Semantic evaluation orchestration tests: `v2/rp_runtime/tests/semantic-evaluation.test.mjs`, `semantic-evaluation-orchestration.test.mjs`. Run with `node --test` on those files for fast deterministic coverage without starting the full npm suite.

When changing Character phase or semantic evaluation:

- Run `node --test tests/semantic-evaluation*.test.mjs` from `v2/rp_runtime/`.
- Run integration round tests (`two-character-round.test.mjs`, `execution-evidence.test.mjs`) when trace or evidence indexing changes.
- Bounded real-provider semantic validation: `semantic-evaluation-live-pass.test.mjs` (requires `DEEPSEEK_API_KEY`; run from `v2/rp_runtime/` with `node --test tests/semantic-evaluation-live-pass.test.mjs`).
- **Perceptual-grounding semantic validation** (R02b/R14 against authorized inventory): `node scripts/issue199-supplemental-semantic-validation.mjs` from `v2/rp_runtime/` (requires `DEEPSEEK_API_KEY`; durable report under `governance/records/`).
- **Inverse Player-action-authority semantic validation** (R16 objective regression vs ignorance/deception/distinct requirement): `node scripts/issue200-inverse-r16-live-validation.mjs` from `v2/rp_runtime/` (requires `DEEPSEEK_API_KEY`; durable report under `governance/records/`).
- Deterministic pressure-freshness regression (no provider): `python -m pytest v2/domain/tests/test_issue_200_scene_pressure_freshness.py -q`.

Post-#28 forensic completeness (#28):

- Run `node --test tests/execution-evidence-forensic.test.mjs tests/participation-round.test.mjs tests/director-semantic-qa-orchestration.test.mjs tests/narrator-semantic-qa-orchestration.test.mjs` from `v2/rp_runtime/`.
- Validate CLI chains on fresh session evidence: `python tools/investigation/list_execution_evidence.py <hg_session_id> --chain participation --round <hg_round_id>`.

---

Scenario manifest contracts and structured eval profiles are tested in the domain suite. See [SCENARIO_VALIDATION_FRAMEWORK.md](../SCENARIO_VALIDATION_FRAMEWORK.md).

---

## Done criteria

A change is ready when:

- relevant targeted tests pass;
- broader suites pass when risk warrants it;
- the diff stays scoped to the intended task;
- current docs are updated when paths or commands change.
