# Testing Expectations

Use this document together with `python/README.md` when changing Python code.

## Source commands

The Python workspace uses `uv` and `poe`.

Primary references:

- setup and environment: `python/README.md`
- common checks: `python/README.md`

### Default `pytest` scope (Holy Grail fork)

From `python/` (workspace root), **`[tool.pytest.ini_options]`** sets **`testpaths = ["tests"]`** and **`asyncio_mode = "auto"`** in `python/pyproject.toml`.

- **`python -m pytest`** or **`pytest`** with no paths runs **only** `python/tests/` (the Holy Grail RP app regression suite). It does **not** collect vendored `packages/*` tests, which avoids optional third-party import failures (e.g. `anthropic`, `mcp`, `ollama`) on a normal dev run.
- To run **vendored AutoGen package** tests under `packages/`, install optional deps and pass explicit paths, for example:
  - `uv sync --group dev --group autogen-vendored-tests`
  - then `pytest packages/autogen-core/tests/...` (or the target package test dir).
- Regression guard: `python/tests/test_pytest_root_collection.py` subprocess-collects with the default config and asserts only `tests/*` node IDs and no `ERROR collecting packages`.

Common commands from the Python workspace:

- `poe format`
- `poe lint`
- `poe test`
- `poe mypy`
- `poe pyright`
- `poe check`

## Test strategy

- Run the smallest relevant test set first.
- Run broader checks when the change affects shared infrastructure or architecture-sensitive code.
- Do not treat a manual app run or audit session as a substitute for regression tests.
- If a public function or materially changed behavior lacks test coverage, add or update focused tests.

## Python test rules

From `python/README.md` and current repo practice:

- use `pytest`
- prefer fixtures for setup
- use mocks instead of real API or database calls where possible
- use `autogen_ext.models.replay.ReplayChatCompletionClient` for model-client simulation when relevant
- skip real external-service tests when required credentials or services are unavailable

## RP app-specific testing guidance

If a change touches `python/rp_app/`:

- prefer focused regression tests near the affected behavior
- convert repeated audit findings into tests when feasible
- use audited scene reruns as verification for continuity, pacing, and scene-behavior fixes
- check for downstream effects in turn selection, continuity updates, validation, and audit output

## Done criteria

A change is not ready to commit until:

- relevant targeted tests pass
- any broader checks required by the risk level pass
- the diff remains scoped to the intended task
