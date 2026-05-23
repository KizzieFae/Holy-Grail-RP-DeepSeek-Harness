"""Tests for Issue #243-A semantic evaluation profile registry."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from semantic_eval_profiles import (  # noqa: E402
    DEFAULT_PROFILE_ID,
    load_profile_registry,
    observational_eval_envelope,
    resolve_evaluation_profile,
    validate_evaluation_ontology_profile_id,
)


def test_load_profile_registry_default_path() -> None:
    reg = load_profile_registry()
    assert reg.schema_version == "semantic_eval_profiles_v1"
    assert DEFAULT_PROFILE_ID in reg.profiles
    assert "dorm_studio_single_space" in reg.profiles
    assert reg.profiles["dorm_studio_single_space"].placeholder is False
    assert "multi_room_excursion_v1" in reg.profiles
    assert reg.profiles["multi_room_excursion_v1"].placeholder is True


def test_resolve_evaluation_profile_manifest_wins() -> None:
    reg = load_profile_registry()
    pid, source = resolve_evaluation_profile(
        "unknown_scenario",
        manifest_profile="generic_net_state_v1",
        registry=reg,
    )
    assert pid == "generic_net_state_v1"
    assert source == "manifest"


def test_resolve_evaluation_profile_scenario_registry() -> None:
    reg = load_profile_registry()
    pid, source = resolve_evaluation_profile(
        "audit_i225_willow_must_remain_v2_offstage_cycles",
        registry=reg,
    )
    assert pid == "dorm_studio_single_space"
    assert source == "scenario_registry"


def test_resolve_evaluation_profile_default_fallback() -> None:
    reg = load_profile_registry()
    pid, source = resolve_evaluation_profile("cert_i234_proposal_accept_off_focal", registry=reg)
    assert pid == DEFAULT_PROFILE_ID
    assert source == "default"


def test_validate_unknown_profile_raises() -> None:
    with pytest.raises(ValueError, match="not registered"):
        validate_evaluation_ontology_profile_id("nonexistent_profile_xyz")


def test_observational_eval_envelope_disclaimer() -> None:
    env = observational_eval_envelope(extra_field=True)
    assert env["observational_only"] is True
    assert env["runtime_allowlist"] is False
    assert env["continuity_authority"] is False
    assert env["runtime_gate"] is False
    assert env["extra_field"] is True


def test_registry_rejects_bad_schema(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"schema_version": "nope", "profiles": {}}), encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported profile registry schema"):
        load_profile_registry(bad)
