"""Phase 3.1: manifest-driven authored index compiler."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from authored_index_compile import compile_authored_index


def test_compile_manifest_deterministic_twice_identical(tmp_path: Path) -> None:
    base = Path(__file__).resolve().parent / "fixtures" / "compile_sample"
    manifest = base / "manifest.json"
    out1 = tmp_path / "out1.json"
    out2 = tmp_path / "out2.json"
    compile_authored_index(manifest, out1)
    compile_authored_index(manifest, out2)
    assert out1.read_text(encoding="utf-8") == out2.read_text(encoding="utf-8")


def test_compile_allowlist_excludes_unlisted_keys(tmp_path: Path) -> None:
    base = Path(__file__).resolve().parent / "fixtures" / "compile_sample"
    manifest = base / "manifest.json"
    out = tmp_path / "idx.json"
    compile_authored_index(manifest, out)
    raw = json.loads(out.read_text(encoding="utf-8"))
    refs = [c["source_ref"] for c in raw["characters"]["Zeta"]]
    assert any("voice_notes" in r for r in refs)
    assert not any("secret_field" in r for r in refs)


def test_compile_skips_ooc_even_in_source(tmp_path: Path) -> None:
    base = Path(__file__).resolve().parent / "fixtures" / "compile_ooc"
    manifest = base / "manifest.json"
    out = tmp_path / "idx.json"
    compile_authored_index(manifest, out)
    raw = json.loads(out.read_text(encoding="utf-8"))
    flat = json.dumps(raw)
    assert "OOC_LEAK" not in flat


def test_compile_no_compiled_at_timestamp(tmp_path: Path) -> None:
    base = Path(__file__).resolve().parent / "fixtures" / "compile_sample"
    out = tmp_path / "idx.json"
    compile_authored_index(base / "manifest.json", out)
    raw = json.loads(out.read_text(encoding="utf-8"))
    assert "compiled_at" not in raw


def test_compile_unknown_type_raises(tmp_path: Path) -> None:
    (tmp_path / "x.json").write_text("{}", encoding="utf-8")
    manifest = tmp_path / "m.json"
    manifest.write_text(
        json.dumps(
            {
                "entries": [
                    {"type": "nope", "path": "x.json"},
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unknown"):
        compile_authored_index(manifest, tmp_path / "o.json")


def test_compile_schema_version_two(tmp_path: Path) -> None:
    base = Path(__file__).resolve().parent / "fixtures" / "compile_sample"
    out = tmp_path / "idx.json"
    compile_authored_index(base / "manifest.json", out)
    raw = json.loads(out.read_text(encoding="utf-8"))
    assert raw["schema_version"] == 2
    assert "lore" in raw
