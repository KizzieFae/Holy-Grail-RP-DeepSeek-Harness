# Holy Grail RP — implementation tree

Production implementation for **Holy Grail RP**. The repository root is the product boundary; this directory is the **current implementation root** (literal path name `v2/`).

## Layout

| Path | Role |
|------|------|
| `domain/modules/` | Permanent domain semantics library |
| `domain_api/` | Domain Host — transport-neutral Domain API + authoritative Python kernel |
| `domain/tests/` | Framework-neutral domain behavioral contracts |
| `rp_runtime/` | DSH/Cordis RP orchestration (`HgRoundOrchestrator`, inference client) |
| `tests/` | Integration and repository architecture tests |

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

The supervisor and `Launch-Holy-Grail-RP.bat` use this canonical `.venv`.

## Quick run

```powershell
# Domain contract tests
python -m pytest v2/domain/tests/ -q

# Integration / architecture tests
python -m pytest v2/tests/ -q

# DSH runtime tests (starts Domain Host subprocess)
cd v2/rp_runtime
npm test
```

## Architecture flow

```text
Application client / UI
        ↓
HolyGrailApplicationClient
        ↓
RP runtime (DSH / Cordis)
        ↔
Domain Host (domain_api)
        ↓
domain library + repositories
        ↓
data/  (HG_DATA_DIR)
```

**Principle:** Holy Grail determines what is true. DeepSeek Harness records what happened.
