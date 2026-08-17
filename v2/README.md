# V2 boundary prototype

Narrow vertical slice proving the agreed Python↔DSH architecture boundary.

## Layout

| Path | Role |
|------|------|
| `domain_api/` | Transport-neutral Domain API contract + authoritative Python kernel |
| `domain_api/http_transport.py` | **Prototype-only** HTTP localhost transport |
| `rp_runtime/` | Minimal DSH/Cordis composition + mock LLM + character inference runner |
| `dsh-pins.toml` | Explicit pinned DSH/Cordis versions |
| `tests/` | Python authority/traceability tests |

## Quick run

```powershell
# Python authority tests
cd autogen_rp/python
.\.venv\Scripts\python.exe -m pytest ..\..\v2\tests -q

# DSH boundary tests (starts Domain API subprocess)
cd v2/rp_runtime
npm test
```

## Principle

> Holy Grail determines what is true. DeepSeek Harness records what happened.

See `governance/rp-app/v2-boundary-prototype.md` for the implementation report.
