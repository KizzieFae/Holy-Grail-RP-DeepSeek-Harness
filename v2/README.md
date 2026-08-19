# V2 boundary prototype

Narrow vertical slice proving the agreed Python↔DSH architecture boundary.

## Layout

| Path | Role |
|------|------|
| `domain_api/` | Transport-neutral Domain API contract + authoritative Python kernel |
| `domain_api/http_transport.py` | **Prototype-only** HTTP localhost transport |
| `domain/modules/` | Permanent domain semantics library |
| `domain/tests/` | Neutral-domain behavioral contracts (358 tests) |
| `rp_runtime/src/plugins/hg-round-orchestrator/` | **HgRoundOrchestrator** Cordis service (round lifecycle) |
| `rp_runtime/src/lib/` | Shared inference utilities and Domain API client |
| `dsh-pins.toml` | Explicit pinned DSH/Cordis versions |
| `tests/` | V2 integration/authority tests |

## Python environment (Domain Host)

Production startup resolves Python from the **repository-root** virtual environment:

```text
<repo>/.venv/Scripts/python.exe   (Windows)
<repo>/.venv/bin/python             (POSIX)
```

Provision once from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Override explicitly when needed:

```powershell
$env:HG_PYTHON_EXECUTABLE = "C:\path\to\python.exe"
```

The supervisor and `Launch-Holy-Grail-V2.bat` do **not** use `autogen_rp/python/.venv`.

## Quick run

```powershell
# Python authority + domain contract tests (use canonical .venv or active interpreter)
python -m pytest v2/tests/ -q
python -m pytest v2/domain/tests/ -q

# DSH runtime tests (starts Domain Host subprocess via canonical .venv)
cd v2/rp_runtime
npm test
```

## Principle

> Holy Grail determines what is true. DeepSeek Harness records what happened.

See `governance/rp-app/v2-director-character-orchestration.md` for the implementation report.
