# Holy Grail RP — implementation tree

Production implementation for **Holy Grail RP**. The repository root is the product boundary; this directory is the **current implementation root** (literal path name `v2/`).

## Layout

| Path | Role |
|------|------|
| `domain/modules/` | Permanent domain semantics library |
| `domain_api/` | Domain Host — transport-neutral Domain API + authoritative Python kernel |
| `domain/tests/` | Framework-neutral domain behavioral contracts |
| `rp_runtime/` | DSH/Cordis RP orchestration (`HgRoundOrchestrator`, phase executors, inference) |
| `ui/` | Presentation client (`streamlit_app.py` talks HTTP to the Node application API) |
| `tests/` | Integration and repository architecture tests |

## Operator first run

**Normal operators:** use the repository root [README.md](../README.md) **Operator quick start** (Python venv, `pip install -e ".[app]"`, `npm ci`, inference, launch). This file covers the implementation tree and contributor commands only.

## Python environment (Domain Host)

Production startup resolves Python from the **repository-root** virtual environment:

```text
<repo>/.venv/Scripts/python.exe   (Windows)
<repo>/.venv/bin/python             (POSIX)
```

Provision once from the repository root (after creating `.venv`):

```bash
pip install -e ".[app]"
```

Contributors running pytest also need dev dependencies:

```bash
pip install -e ".[app,dev]"
```

Override explicitly when needed:

```powershell
$env:HG_PYTHON_EXECUTABLE = "C:\path\to\python.exe"
```

The supervisor and `Launch-Holy-Grail-RP.bat` use this canonical `.venv`.

Node dependencies for the RP runtime (required before `npm test` or `npm run app`):

```bash
cd v2/rp_runtime
npm ci
```

## Contributor commands

```bash
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
Presentation (v2/ui/streamlit_app.py)
        ↓ HTTP
HolyGrailApplicationClient + DSH runtime (this tree)
        ↓ HTTP (domain-api-client)
Domain Host (domain_api)
        ↓
domain library + SessionRepository / SessionManager
        ↓
data/  (HG_DATA_DIR)
```

Node calls the Domain Host. Python does not call DSH. The UI is presentation-only.

### Commit transaction (#55 C3-F)

`DomainKernel.commit_move` resolves session/round anchors and delegates to `domain_api/commit_move_transaction.py`. That module owns dedup, rollback, transactionally coupled state ordering, and post-durable effects. `ContinuityManager.process_turn` remains the sole continuity mutation authority. `SessionRepository.persist` is the durability gate.

### Character knowledge path (#38)

```text
assemble_character_upstream_contributions
  → Character knowledge-orientation (DSH inference)
  → Character KnowledgeAccessRequest (Host envelope + hard access)
  → Librarian contextual-semantic mediation
  → map_librarian_bundle_to_contributions → prepare_context
  → Character move inference
```

Character orientation sees full pre-Librarian upstream context. Librarian mediation is bounded by per-character epistemic access (viewer/subject binding, hard access, `known_by` filtering, packaging `bound_character_id`). Character packaging rejects `deterministic_fallback`. The retired legacy Character manifest projection (`KnowledgeService.project_context`) is no longer on the live path.

**Principle:** Holy Grail determines what is true. DeepSeek Harness records what happened.
