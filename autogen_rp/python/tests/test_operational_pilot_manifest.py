"""Operational retrieval pilot: manifest compiles and loads (no runtime behavior change)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from authored_index_compile import compile_authored_index
from retrieved_context_select import load_authored_retrieval_index

_PY = Path(__file__).resolve().parent.parent
OPERATIONAL_MANIFEST = _PY / "data" / "retrieval" / "manifests" / "operational_pilot.json"


@pytest.mark.skipif(not OPERATIONAL_MANIFEST.is_file(), reason="operational pilot manifest missing")
def test_operational_pilot_manifest_compiles_v3(tmp_path: Path) -> None:
    out = tmp_path / "pilot.json"
    stats = compile_authored_index(OPERATIONAL_MANIFEST, out, schema_version=3)
    assert stats["schema_version"] == 3
    assert stats["characters"] == 3
    assert stats["templates"] == 2
    raw = out.read_text(encoding="utf-8")
    assert '"schema_version": 3' in raw
    idx = load_authored_retrieval_index(str(out))
    assert idx is not None
    assert idx.schema_version == 3
    assert set(idx.characters.keys()) == {"Harley_Quinn", "Magpie", "Poison_Ivy"}
    assert "arkham_asylum_cell_intake" in idx.templates
    assert "arkham_asylum_mess_hall_arena" in idx.templates
