"""Character move parse ingress: duplicate-key–safe JSON, v1 allowlist, v1→v2, v2 validate (#137).

Rejects before schema detection if JSON has duplicate object keys. Unknown
``move_schema_version`` (other than ``2``) rejects. Success path returns a plain
``dict`` that is canonical v2 per ``ARCHITECTURE.md`` (``move_schema_version: 2``).
"""

from __future__ import annotations

import json
import os
from typing import Any

from character_move_adapters import CanonicalV2Move

# Structural caps (parser boundary only; Issue #137).
MAX_V2_BEATS = 64
MAX_V2_TEXT_CODEPOINTS = 8192
MAX_V2_AUDIENCE_ITEMS = 32

V1_ROOT_ALLOWLIST = frozenset(
    {
        "action",
        "dialogue",
        "motivation",
        "audibility",
        "audience",
        "scene_state_updates",
    }
)

V2_ROOT_ALLOWLIST = frozenset(
    {
        "move_schema_version",
        "beats",
        "motivation",
        "scene_state_updates",
    }
)

V2_SPEECH_AUDIBILITY = frozenset({"public", "directed", "private"})

_MOTIVATION_DEFAULTS: dict[str, str] = {
    "goal": "advance current objective",
    "tactic": "react in character",
    "emotional_driver": "guarded focus",
    "risk_level": "medium",
}


def _is_int_not_bool(x: Any) -> bool:
    return type(x) is int  # True not allowed


def _object_pairs_reject_duplicates(
    pairs: list[tuple[str, Any]]
) -> dict[str, Any]:
    d: dict[str, Any] = {}
    for k, v in pairs:
        if k in d:
            # ValueError: caught by :func:`parse_character_move_content_to_v2` and surfaced as parse error.
            raise ValueError("duplicate key %r" % (k,))
        d[k] = v
    return d


def load_json_object_duplicate_safe(text: str) -> Any:
    """``json.loads`` with duplicate key rejection on every object (via ``object_pairs_hook``)."""
    return json.loads(text, object_pairs_hook=_object_pairs_reject_duplicates)


def unwrap_fenced_json_object(raw: str) -> tuple[str, str]:
    """Return (json_str, err). Strips a single `` ```json ```` or `` ``` `` block, else first … last ``{`` ``}`` slice."""
    content = (raw or "").strip()
    if not content:
        return "", "No JSON object found"
    if "```json" in content:
        start = content.find("```json") + 7
        end = content.find("```", start)
        if end == -1:
            return "", "Unclosed markdown code fence (```json)"
        json_str = content[start:end].strip()
    elif content.startswith("```"):
        start = content.find("```") + 3
        end = content.find("```", start)
        if end == -1:
            return "", "Unclosed markdown code fence (```)"
        json_str = content[start:end].strip()
    else:
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return "", "No JSON object found"
        json_str = content[start : end + 1]
    if not json_str:
        return "", "No JSON object found"
    return json_str, ""


def _legacy_v1_ingress_enabled() -> bool:
    v = (os.environ.get("RP_LEGACY_V1_CHARACTER_MOVE", "1") or "").strip().lower()
    return v not in ("0", "false", "no", "off")


def _v1_synthesize_motivation(data: dict[str, Any]) -> tuple[dict[str, str] | None, str]:
    if "motivation" in data and data["motivation"] is not None:
        raw = data["motivation"]
        if not isinstance(raw, dict):
            return None, "Field 'motivation' must be an object on v1 ingress"
        m: dict[str, Any] = {str(k): raw[k] for k in raw}
    else:
        m = {k: _MOTIVATION_DEFAULTS[k] for k in _MOTIVATION_DEFAULTS}
    for req in ("goal", "tactic", "emotional_driver", "risk_level"):
        m.setdefault(req, _MOTIVATION_DEFAULTS[req])
    for req in ("goal", "tactic", "emotional_driver", "risk_level"):
        if not str(m.get(req, "") or "").strip():
            return None, f"Motivation key {req!r} must be a non-empty string after trim"
    out: dict[str, str] = {k: str(v).strip() for k, v in m.items()}
    return out, ""


def _normalize_v1_to_v2(data: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    action_s = str(data.get("action", "") or "").strip()
    dialogue_s = str(data.get("dialogue", "") or "").strip()
    if not action_s and not dialogue_s:
        return None, "v1 move must have non-empty action and/or dialogue after trim"

    aud_raw = str(data.get("audibility", "") or "").strip().lower()
    if aud_raw and aud_raw not in V2_SPEECH_AUDIBILITY:
        return None, f"Invalid v1 audibility: {aud_raw!r}"
    if aud_raw in V2_SPEECH_AUDIBILITY and aud_raw != "public" and not dialogue_s:
        return None, "v1 non-public audibility requires non-empty dialogue"
    if not dialogue_s and (data.get("audience") is not None and data.get("audience") != []):
        return None, "v1 audience requires non-empty dialogue"

    motivation, err = _v1_synthesize_motivation(data)
    if err or motivation is None:
        return None, err

    raw_aud = data.get("audience")
    audience: list[str] = []
    if isinstance(raw_aud, list):
        audience = [str(a).strip() for a in raw_aud if str(a).strip()]
    elif raw_aud is not None and str(raw_aud).strip():
        audience = [str(raw_aud).strip()]

    beats: list[dict[str, Any]] = []
    if action_s:
        beats.append({"type": "action", "action": action_s})
    if dialogue_s:
        sp: dict[str, Any] = {"type": "speech", "dialogue": dialogue_s}
        if aud_raw in V2_SPEECH_AUDIBILITY:
            sp["audibility"] = aud_raw
        if aud_raw in ("directed", "private"):
            if not audience:
                return None, "directed/private speech requires non-empty audience"
            sp["audience"] = audience
        elif audience:
            return None, "public/omitted audibility must not set audience"
        beats.append(sp)

    out: dict[str, Any] = {
        "move_schema_version": 2,
        "beats": beats,
        "motivation": dict(motivation),
    }

    ssup = data.get("scene_state_updates")
    if ssup is not None:
        if not isinstance(ssup, dict):
            return None, "scene_state_updates must be a JSON object on v1 ingress"
        out["scene_state_updates"] = dict(ssup)

    return out, ""


def _check_caps_v2(m: dict[str, Any]) -> str:
    beats = m.get("beats")
    if not isinstance(beats, list):
        return ""
    if len(beats) > MAX_V2_BEATS:
        return f"beats exceeds cap ({MAX_V2_BEATS})"
    for b in beats:
        if not isinstance(b, dict):
            continue
        t = b.get("type")
        if t == "action":
            s = str(b.get("action", "") or "")
            if len(s) > MAX_V2_TEXT_CODEPOINTS:
                return "action string exceeds cap"
        elif t == "speech":
            s = str(b.get("dialogue", "") or "")
            if len(s) > MAX_V2_TEXT_CODEPOINTS:
                return "dialogue string exceeds cap"
            aud = b.get("audience")
            if isinstance(aud, list) and len(aud) > MAX_V2_AUDIENCE_ITEMS:
                return "audience array exceeds cap"
    return ""


def validate_canonical_v2(m: dict[str, Any]) -> str:
    """Return error message or ``""`` if valid. Does not copy."""
    if m.get("move_schema_version") != 2:
        return "move_schema_version must be 2"
    for p in ("action", "dialogue", "audibility", "audience"):
        if p in m:
            return f"prohibited root key: {p!r}"
    extra = set(m.keys()) - V2_ROOT_ALLOWLIST
    if extra:
        return f"unknown v2 root keys: {sorted(extra)}"

    beats = m.get("beats")
    if not isinstance(beats, list) or len(beats) < 1:
        return "beats must be a non-empty array"
    cap = _check_caps_v2(m)
    if cap:
        return cap

    mot = m.get("motivation")
    if not isinstance(mot, dict):
        return "motivation must be an object"
    for req in ("goal", "tactic", "emotional_driver", "risk_level"):
        v = str(mot.get(req, "") or "").strip()
        if not v:
            return f"motivation missing or empty required key: {req!r}"
    ssup = m.get("scene_state_updates", None)
    if ssup is not None and not isinstance(ssup, dict):
        return "scene_state_updates must be a JSON object when present"

    for b in beats:
        if not isinstance(b, dict):
            return "each beat must be an object"
        bt = b.get("type")
        if bt not in ("action", "speech"):
            return f"invalid beat type: {bt!r}"
        unknown = [k for k in b if k not in _beat_allowed_keys(bt)]
        if unknown:
            return f"unknown fields on {bt!r} beat: {unknown}"
        if bt == "action":
            s = str(b.get("action", "") or "").strip()
            if not s:
                return "action beat requires non-empty action"
        elif bt == "speech":
            s = str(b.get("dialogue", "") or "").strip()
            if not s:
                return "speech beat requires non-empty dialogue"
            eff: str
            if "audibility" in b:
                aud0 = b.get("audibility")
                if not isinstance(aud0, str) or aud0 not in V2_SPEECH_AUDIBILITY:
                    return f"invalid speech audibility: {aud0!r}"
                eff = aud0
            else:
                eff = "public"
            aud_list = b.get("audience", None)
            if eff == "public":
                if isinstance(aud_list, list) and len(aud_list) > 0:
                    return "public speech must not have non-empty audience"
            else:
                if not isinstance(aud_list, list) or len(aud_list) < 1:
                    return "directed/private speech requires non-empty audience array"
            if isinstance(aud_list, list):
                for a in aud_list:
                    if not isinstance(a, str):
                        return "audience must be a JSON array of strings"
    return ""


def _beat_allowed_keys(bt: Any) -> set[str]:
    if bt == "action":
        return {"type", "action"}
    if bt == "speech":
        return {"type", "dialogue", "audibility", "audience"}
    return set()


def _as_canonical_v2_handoff(d: dict[str, Any]) -> CanonicalV2Move:
    m = CanonicalV2Move()
    m.update(d)
    return m


def ingest_character_move_json_object(data: dict[str, Any]) -> tuple[CanonicalV2Move | None, str]:
    """
    Classify, normalize, validate. **Duplicate keys must be rejected in JSON
    load before this is called.**
    """
    if "move_schema_version" in data:
        msv = data["move_schema_version"]
        if not _is_int_not_bool(msv):
            return None, "move_schema_version must be a JSON integer"
        if msv != 2:
            return None, f"Unsupported move_schema_version: {msv!r}"
        for p in ("action", "dialogue", "audibility", "audience"):
            if p in data:
                return None, f"invalid mixed document: root {p!r} not allowed on v2"
        err = validate_canonical_v2(data)
        if err:
            return None, err
        return _as_canonical_v2_handoff(dict(data)), ""

    if not _legacy_v1_ingress_enabled():
        return None, "v1 character move shape rejected (RP_LEGACY_V1_CHARACTER_MOVE=0)"

    extra = set(data.keys()) - V1_ROOT_ALLOWLIST
    if extra:
        return None, f"unknown v1 root keys: {sorted(extra)}"

    norm, err = _normalize_v1_to_v2(data)
    if err or norm is None:
        return None, err or "v1 normalization failed"
    err2 = validate_canonical_v2(norm)
    if err2:
        return None, err2
    return _as_canonical_v2_handoff(norm), ""


def parse_character_move_content_to_v2(content: str) -> tuple[CanonicalV2Move | None, str]:
    """
    Unwrap → JSON parse (duplicate-key safe) → schema path.

    Rejects duplicate keys at ``json.loads`` (before :func:`ingest_character_move_json_object`).
    """
    json_str, uerr = unwrap_fenced_json_object(content)
    if uerr:
        return None, uerr
    try:
        data = load_json_object_duplicate_safe(json_str)
    except (json.JSONDecodeError, ValueError) as e:
        return None, f"Invalid JSON: {e}"
    except Exception as e:
        return None, f"Parse error: {e}"
    if not isinstance(data, dict):
        return None, "JSON payload must be an object"
    return ingest_character_move_json_object(data)
