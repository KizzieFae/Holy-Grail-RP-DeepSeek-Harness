"""Phase 3.1: manifest-driven authored index compiler."""

from __future__ import annotations

import json
import shutil
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
    compile_authored_index(manifest, out1, schema_version=2)
    compile_authored_index(manifest, out2, schema_version=2)
    assert out1.read_text(encoding="utf-8") == out2.read_text(encoding="utf-8")


def test_compile_allowlist_excludes_unlisted_keys(tmp_path: Path) -> None:
    base = Path(__file__).resolve().parent / "fixtures" / "compile_sample"
    manifest = base / "manifest.json"
    out = tmp_path / "idx.json"
    compile_authored_index(manifest, out, schema_version=2)
    raw = json.loads(out.read_text(encoding="utf-8"))
    refs = [c["source_ref"] for c in raw["characters"]["Zeta"]]
    assert any("voice_notes" in r for r in refs)
    assert not any("secret_field" in r for r in refs)


def test_compile_skips_ooc_even_in_source(tmp_path: Path) -> None:
    base = Path(__file__).resolve().parent / "fixtures" / "compile_ooc"
    manifest = base / "manifest.json"
    out = tmp_path / "idx.json"
    compile_authored_index(manifest, out, schema_version=2)
    raw = json.loads(out.read_text(encoding="utf-8"))
    flat = json.dumps(raw)
    assert "OOC_LEAK" not in flat


def test_compile_no_compiled_at_timestamp(tmp_path: Path) -> None:
    base = Path(__file__).resolve().parent / "fixtures" / "compile_sample"
    out = tmp_path / "idx.json"
    compile_authored_index(base / "manifest.json", out, schema_version=2)
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
    compile_authored_index(base / "manifest.json", out, schema_version=2)
    raw = json.loads(out.read_text(encoding="utf-8"))
    assert raw["schema_version"] == 2
    assert "lore" in raw
    assert "knowledge_id" not in json.dumps(raw["characters"])


def test_compile_schema_version_invalid_raises(tmp_path: Path) -> None:
    base = Path(__file__).resolve().parent / "fixtures" / "compile_sample"
    with pytest.raises(ValueError, match="schema_version"):
        compile_authored_index(base / "manifest.json", tmp_path / "x.json", schema_version=99)


def test_compile_v3_deterministic_twice_identical(tmp_path: Path) -> None:
    base = Path(__file__).resolve().parent / "fixtures" / "compile_sample"
    manifest = base / "manifest.json"
    out1 = tmp_path / "v3a.json"
    out2 = tmp_path / "v3b.json"
    compile_authored_index(manifest, out1, schema_version=3)
    compile_authored_index(manifest, out2, schema_version=3)
    assert out1.read_text(encoding="utf-8") == out2.read_text(encoding="utf-8")


def test_compile_v3_matches_golden_fixture(tmp_path: Path) -> None:
    base = Path(__file__).resolve().parent / "fixtures" / "compile_sample"
    manifest = base / "manifest.json"
    golden_path = base / "expected_index_v3.json"
    out = tmp_path / "v3.json"
    compile_authored_index(manifest, out, schema_version=3)
    assert json.loads(out.read_text(encoding="utf-8")) == json.loads(
        golden_path.read_text(encoding="utf-8")
    )


def test_compile_v3_each_chunk_has_canonical_fields(tmp_path: Path) -> None:
    base = Path(__file__).resolve().parent / "fixtures" / "compile_sample"
    out = tmp_path / "v3.json"
    compile_authored_index(base / "manifest.json", out, schema_version=3)
    raw = json.loads(out.read_text(encoding="utf-8"))
    assert raw["schema_version"] == 3
    assert "compile_metadata" in raw
    required = {"knowledge_id", "knowledge_type", "authority_class", "visibility", "subject_scope"}
    for ch in raw["characters"]["Zeta"]:
        assert required <= ch.keys()
    for ch in raw["templates"]["tpl_x"]:
        assert required <= ch.keys()
    for ch in raw["setup_notes"]:
        assert required <= ch.keys()
    for ch in raw["lore"]:
        assert required <= ch.keys()


def test_compile_v3_strict_fallback_unknown_key(tmp_path: Path) -> None:
    char_dir = tmp_path / "characters"
    char_dir.mkdir()
    (char_dir / "q.json").write_text(json.dumps({"mystery_field": "opaque"}), encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "type": "character",
                        "path": "characters/q.json",
                        "character_id": "Q",
                        "allowlist_keys": ["mystery_field"],
                    }
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    out = tmp_path / "out.json"
    stats = compile_authored_index(manifest, out, schema_version=3)
    raw = json.loads(out.read_text(encoding="utf-8"))
    assert stats["compile_metadata"]["fallback_uses"] == 1
    ch = raw["characters"]["Q"][0]
    assert ch["knowledge_type"] == "lore_reference"
    assert ch["authority_class"] == "reference_only"
    assert "strict_fallback" in stats["compile_metadata"]["warnings"][0]


def test_compile_realistic_v3_matches_golden(tmp_path: Path) -> None:
    base = Path(__file__).resolve().parent / "fixtures" / "compile_realistic"
    manifest = base / "manifest.json"
    golden_path = base / "expected_realistic_v3.json"
    out = tmp_path / "realistic_v3.json"
    compile_authored_index(manifest, out, schema_version=3)
    assert json.loads(out.read_text(encoding="utf-8")) == json.loads(
        golden_path.read_text(encoding="utf-8")
    )


def test_compile_realistic_v3_deterministic_twice(tmp_path: Path) -> None:
    base = Path(__file__).resolve().parent / "fixtures" / "compile_realistic"
    manifest = base / "manifest.json"
    out1 = tmp_path / "r1.json"
    out2 = tmp_path / "r2.json"
    compile_authored_index(manifest, out1, schema_version=3)
    compile_authored_index(manifest, out2, schema_version=3)
    assert out1.read_text(encoding="utf-8") == out2.read_text(encoding="utf-8")


def test_compile_realistic_role_slots_sorted_and_payload(tmp_path: Path) -> None:
    base = Path(__file__).resolve().parent / "fixtures" / "compile_realistic"
    out = tmp_path / "r.json"
    compile_authored_index(base / "manifest.json", out, schema_version=3)
    raw = json.loads(out.read_text(encoding="utf-8"))
    tpl = raw["templates"]["mini_tpl"]
    role_refs = [c["source_ref"] for c in tpl if "role_slot" in c["source_ref"]]
    assert role_refs == sorted(role_refs)
    assert role_refs[0].endswith(":alpha")
    alpha = next(c for c in tpl if c["source_ref"].endswith(":alpha"))
    assert alpha["structured_payload"]["role_name"] == "alpha"
    assert alpha["knowledge_type"] == "role_constraint"


def test_compile_realistic_template_initial_messages_pointer_emits_no_rows(tmp_path: Path) -> None:
    base = Path(__file__).resolve().parent / "fixtures" / "compile_realistic"
    out = tmp_path / "r.json"
    compile_authored_index(base / "manifest.json", out, schema_version=3)
    raw = json.loads(out.read_text(encoding="utf-8"))
    for c in raw["templates"]["mini_tpl"]:
        assert "initial_messages" not in c["source_ref"]


def test_compile_realistic_initial_message_uses_setup_note_kind(tmp_path: Path) -> None:
    base = Path(__file__).resolve().parent / "fixtures" / "compile_realistic"
    out = tmp_path / "r.json"
    compile_authored_index(base / "manifest.json", out, schema_version=3)
    raw = json.loads(out.read_text(encoding="utf-8"))
    assert len(raw["setup_notes"]) == 1
    im = raw["setup_notes"][0]
    assert im["source_kind"] == "setup_note"
    assert im["source_ref"].startswith("imsg:")
    assert im["knowledge_type"] == "scene_setup_fact"


def test_compile_v3_nested_profile_rejects_non_string_list_items(tmp_path: Path) -> None:
    char_dir = tmp_path / "characters"
    char_dir.mkdir()
    (char_dir / "bad.json").write_text(
        json.dumps({"voice_profile": {"habits": [1, 2]}}),
        encoding="utf-8",
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "type": "character",
                        "path": "characters/bad.json",
                        "character_id": "Bad",
                        "allowlist_keys": ["voice_profile"],
                    }
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="list at"):
        compile_authored_index(manifest, tmp_path / "out.json", schema_version=3)


def test_compile_v3_dense_narrative_caps_template_truth(tmp_path: Path) -> None:
    base = Path(__file__).resolve().parent / "fixtures" / "compile_sample"
    work = tmp_path / "compile_sample"
    shutil.copytree(base, work)
    manifest_data = json.loads((work / "manifest.json").read_text(encoding="utf-8"))
    for ent in manifest_data["entries"]:
        if ent.get("type") == "template":
            ent["dense_narrative"] = True
    (work / "manifest.json").write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")
    manifest = work / "manifest.json"
    out = tmp_path / "out.json"
    stats = compile_authored_index(manifest, out, schema_version=3)
    raw = json.loads(out.read_text(encoding="utf-8"))
    assert stats["compile_metadata"]["dense_caps"] >= 1
    tone = raw["templates"]["tpl_x"][0]
    assert tone["authority_class"] == "reference_only"
