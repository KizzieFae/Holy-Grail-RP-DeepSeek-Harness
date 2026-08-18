"""Issue #243-A — declarative semantic evaluation profile registry (offline only).

Observational evaluation alignment only. Profiles guide **offline** corpus regression and
future evaluator plugins. They are **not** runtime authority, **not** continuity authority,
and **not** on the #59 runtime-use allowlist.

Profile resolution order (declarative — never infer from beat prose):
1. Scenario manifest ``evaluation_ontology_profile``
2. ``scenario_registry`` map in the profile bundle
3. Default ``generic_net_state_v1``
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

SEMANTIC_EVAL_PROFILES_SCHEMA_VERSION: Final[str] = "semantic_eval_profiles_v1"
DEFAULT_PROFILE_ID: Final[str] = "generic_net_state_v1"

OBSERVATIONAL_EVAL_DISCLAIMER: Final[dict[str, bool | str]] = {
    "observational_only": True,
    "runtime_allowlist": False,
    "continuity_authority": False,
    "runtime_gate": False,
    "purpose": "offline evaluation calibration — not canonical runtime truth",
}

from domain.paths import autogen_python_data_dir

_DEFAULT_PROFILES_PATH = (
    autogen_python_data_dir() / "evaluation" / "semantic_eval_profiles_v1.json"
)


@dataclass(frozen=True)
class SemanticEvalProfile:
    profile_id: str
    title: str
    description: str
    status: str
    limitations: tuple[str, ...]
    placeholder: bool = False


@dataclass(frozen=True)
class SemanticEvalProfileRegistry:
    schema_version: str
    profiles: dict[str, SemanticEvalProfile]
    scenario_registry: dict[str, str]
    default_profile_id: str

    def profile_ids(self) -> frozenset[str]:
        return frozenset(self.profiles.keys())

    def get_profile(self, profile_id: str) -> SemanticEvalProfile:
        pid = str(profile_id or "").strip()
        if pid not in self.profiles:
            raise KeyError(f"unknown semantic evaluation profile: {profile_id!r}")
        return self.profiles[pid]


def default_profiles_path() -> Path:
    return _DEFAULT_PROFILES_PATH


def load_profile_registry(path: Path | None = None) -> SemanticEvalProfileRegistry:
    p = path or default_profiles_path()
    raw = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"profile registry must be a JSON object: {p}")
    schema = str(raw.get("schema_version") or "").strip()
    if schema != SEMANTIC_EVAL_PROFILES_SCHEMA_VERSION:
        raise ValueError(
            f"unsupported profile registry schema {schema!r} in {p} "
            f"(expected {SEMANTIC_EVAL_PROFILES_SCHEMA_VERSION!r})"
        )
    profiles_raw = raw.get("profiles")
    if not isinstance(profiles_raw, dict) or not profiles_raw:
        raise ValueError(f"profiles must be a non-empty object in {p}")
    profiles: dict[str, SemanticEvalProfile] = {}
    for pid, entry in profiles_raw.items():
        if not isinstance(entry, dict):
            raise ValueError(f"profile {pid!r} must be an object")
        profile_id = str(entry.get("profile_id") or pid).strip()
        if profile_id != pid:
            raise ValueError(f"profile key {pid!r} mismatches profile_id {profile_id!r}")
        title = str(entry.get("title") or "").strip()
        description = str(entry.get("description") or "").strip()
        status = str(entry.get("status") or "active").strip()
        lim_raw = entry.get("limitations") or []
        if not isinstance(lim_raw, list):
            raise ValueError(f"profile {profile_id!r}: limitations must be an array")
        limitations = tuple(str(x).strip() for x in lim_raw if str(x).strip())
        placeholder = bool(entry.get("placeholder", False))
        profiles[profile_id] = SemanticEvalProfile(
            profile_id=profile_id,
            title=title,
            description=description,
            status=status,
            limitations=limitations,
            placeholder=placeholder,
        )
    default_id = str(raw.get("default_profile_id") or DEFAULT_PROFILE_ID).strip()
    if default_id not in profiles:
        raise ValueError(f"default_profile_id {default_id!r} not found in profiles")
    scenario_registry_raw = raw.get("scenario_registry") or {}
    if not isinstance(scenario_registry_raw, dict):
        raise ValueError("scenario_registry must be an object when present")
    scenario_registry: dict[str, str] = {}
    for sid, pid in scenario_registry_raw.items():
        scenario_id = str(sid or "").strip()
        profile_id = str(pid or "").strip()
        if not scenario_id or not profile_id:
            raise ValueError("scenario_registry keys and values must be non-empty strings")
        if profile_id not in profiles:
            raise ValueError(
                f"scenario_registry[{scenario_id!r}] references unknown profile {profile_id!r}"
            )
        scenario_registry[scenario_id] = profile_id
    return SemanticEvalProfileRegistry(
        schema_version=schema,
        profiles=profiles,
        scenario_registry=scenario_registry,
        default_profile_id=default_id,
    )


def resolve_evaluation_profile(
    scenario_id: str,
    *,
    manifest_profile: str | None = None,
    registry: SemanticEvalProfileRegistry | None = None,
) -> tuple[str, str]:
    """Return ``(profile_id, resolution_source)``.

    ``resolution_source`` is one of: ``manifest``, ``scenario_registry``, ``default``.
    """
    reg = registry or load_profile_registry()
    sid = str(scenario_id or "").strip()
    mp = str(manifest_profile or "").strip() if manifest_profile is not None else ""
    if mp:
        if mp not in reg.profiles:
            raise ValueError(
                f"evaluation_ontology_profile {mp!r} is not registered "
                f"(scenario {sid!r})"
            )
        return mp, "manifest"
    if sid and sid in reg.scenario_registry:
        return reg.scenario_registry[sid], "scenario_registry"
    return reg.default_profile_id, "default"


def validate_evaluation_ontology_profile_id(profile_id: str, registry: SemanticEvalProfileRegistry | None = None) -> str:
    """Normalize and validate a manifest profile id; raise ValueError if unknown."""
    reg = registry or load_profile_registry()
    pid = str(profile_id or "").strip()
    if not pid:
        raise ValueError("evaluation_ontology_profile must be a non-empty string when present")
    if pid not in reg.profiles:
        raise ValueError(
            f"evaluation_ontology_profile {pid!r} is not registered "
            f"(known: {sorted(reg.profiles.keys())})"
        )
    return pid


def observational_eval_envelope(**extra: Any) -> dict[str, Any]:
    """Standard disclaimer block for evaluation-layer JSON artifacts."""
    out = dict(OBSERVATIONAL_EVAL_DISCLAIMER)
    out.update(extra)
    return out
