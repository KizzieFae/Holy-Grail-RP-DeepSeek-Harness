# DEPRECATED — `autogen_rp/python/rp_app` (M12.4)

**Status:** Retired. No substantive modules remain.

## Current architecture

| Layer | Location |
|-------|----------|
| Domain semantics | `v2/domain/modules/` |
| Domain API / Host | `v2/domain_api/` |
| Production runtime | `v2/rp_runtime/` (DSH + supervisor) |
| Launch | `Launch-Holy-Grail-V2.bat` or `npm run app` in `v2/rp_runtime` |

## History

- **M8:** Streamlit `app.py` deprecated as production entry.
- **M12.2:** Domain modules extracted to `v2/domain/modules/`; this directory held import shims.
- **M12.3:** V1 orchestration fenced under `legacy/v1_orchestration/`.
- **M12.4:** Fenced orchestration and all shims deleted. V2 is the sole production path.

## Tests

Domain tests import via `domain.bootstrap.ensure_domain_paths()` (see `autogen_rp/python/tests/conftest.py`).

Historical V1 orchestration evidence: `governance/archive/v1-runtime/`.
