"""Character move parse ingress: duplicate-key–safe JSON, v2-only validate (#137, #143).

Rejects before schema detection if JSON has duplicate object keys. Unknown
``move_schema_version`` (other than ``2``) rejects. Root JSON without
``move_schema_version`` rejects (v1-shaped ingress removed in #143). Success
path returns a plain ``dict`` that is canonical v2 per ``ARCHITECTURE.md``
(``move_schema_version: 2``).
"""

from __future__ import annotations

import json
from typing import Any, Literal

ParseFailureClass = Literal["ok", "unrecoverable", "schema_recoverable"]

from character_move_adapters import CanonicalV2Move
from issue240_semantic_evaluation import (
    issue240_v2_root_allowlist_extra,
    validate_issue240_semantic_evaluation_ingress,
)

# Structural caps (parser boundary only; Issue #137).
MAX_V2_BEATS = 64
MAX_V2_TEXT_CODEPOINTS = 8192
MAX_V2_AUDIENCE_ITEMS = 32
MAX_V2_SEMANTIC_PROPOSALS = 8
MAX_V2_PROPOSAL_TEXT_CODEPOINTS = 256

V2_ROOT_ALLOWLIST = frozenset(
    {
        "move_schema_version",
        "beats",
        "motivation",
        "scene_state_updates",
        "semantic_proposals",
    }
)

V2_SPEECH_AUDIBILITY = frozenset({"public", "directed", "private"})
V2_ACTION_RECIPIENT_SCOPES = frozenset(
    {"public", "present", "directed", "private", "environmental"}
)
V2_PROPOSAL_KINDS = frozenset({"off_focal", "reentry", "excursion_lifecycle"})
V2_EXCURSION_OPERATIONS = frozenset({"open", "update", "close"})
V2_PROPOSAL_ITEM_KEYS = frozenset({"kind", "character", "operation"})


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


def _validate_semantic_proposals_v2(m: dict[str, Any]) -> str:
    """Structural validation for governed A1 ``semantic_proposals`` (GitHub #230)."""
    sp = m.get("semantic_proposals", None)
    if sp is None:
        return ""
    if not isinstance(sp, list):
        return "semantic_proposals must be a JSON array when present"
    if len(sp) > MAX_V2_SEMANTIC_PROPOSALS:
        return f"semantic_proposals exceeds cap ({MAX_V2_SEMANTIC_PROPOSALS})"
    for i, item in enumerate(sp):
        if not isinstance(item, dict):
            return f"semantic_proposals[{i}] must be an object"
        unknown = [k for k in item if k not in V2_PROPOSAL_ITEM_KEYS]
        if unknown:
            return f"unknown fields on semantic_proposals[{i}]: {unknown}"
        kind = item.get("kind")
        if kind not in V2_PROPOSAL_KINDS:
            return f"invalid semantic_proposals[{i}].kind: {kind!r}"
        char = str(item.get("character", "") or "").strip()
        if not char:
            return f"semantic_proposals[{i}].character must be non-empty"
        if len(char) > MAX_V2_PROPOSAL_TEXT_CODEPOINTS:
            return "semantic_proposals character string exceeds cap"
        op = item.get("operation", None)
        if kind == "excursion_lifecycle":
            if not isinstance(op, str) or op not in V2_EXCURSION_OPERATIONS:
                return (
                    f"semantic_proposals[{i}] requires operation "
                    "open|update|close for excursion_lifecycle"
                )
            if len(op) > MAX_V2_PROPOSAL_TEXT_CODEPOINTS:
                return "semantic_proposals operation string exceeds cap"
        elif op is not None:
            return f"semantic_proposals[{i}] must not include operation for kind {kind!r}"
    return ""


def validate_canonical_v2(m: dict[str, Any]) -> str:
    """Return error message or ``""`` if valid. Does not copy."""
    if m.get("move_schema_version") != 2:
        return "move_schema_version must be 2"
    for p in ("action", "dialogue", "audibility", "audience"):
        if p in m:
            return f"prohibited root key: {p!r}"
    allowlist = V2_ROOT_ALLOWLIST | issue240_v2_root_allowlist_extra()
    extra = set(m.keys()) - allowlist
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
            recipients = b.get("recipients")
            if recipients is not None:
                if not isinstance(recipients, dict):
                    return "action beat recipients must be an object"
                scope = str(recipients.get("scope", "") or "").strip().lower()
                if scope not in V2_ACTION_RECIPIENT_SCOPES:
                    return f"invalid action recipients scope: {scope!r}"
                chars = recipients.get("characters", [])
                if not isinstance(chars, list):
                    return "action beat recipients.characters must be an array"
                named = [str(name).strip() for name in chars if str(name).strip()]
                if scope in ("directed", "private") and not named:
                    return f"{scope} action requires non-empty recipients.characters"
                if scope in ("public", "present", "environmental") and named:
                    return f"{scope} action must not include non-empty recipients.characters"
                for name in chars:
                    if not isinstance(name, str):
                        return "recipients.characters must be a JSON array of strings"
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
    err_ev = validate_issue240_semantic_evaluation_ingress(m)
    if err_ev:
        return err_ev
    err_sp = _validate_semantic_proposals_v2(m)
    if err_sp:
        return err_sp
    return ""


def _beat_allowed_keys(bt: Any) -> set[str]:
    if bt == "action":
        return {"type", "action", "recipients"}
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
    load before this is called.** v2-only: root ``move_schema_version`` is required
    (GitHub #143 removed v1-shaped ingress).
    """
    if "move_schema_version" not in data:
        return (
            None,
            "move_schema_version is required (v2 only; v1 character move ingress removed per GitHub #143)",
        )

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


def parse_character_move_content_to_v2(content: str) -> tuple[CanonicalV2Move | None, str]:
    """
    Unwrap → JSON parse (duplicate-key safe) → schema path.

    Rejects duplicate keys at ``json.loads`` (before :func:`ingest_character_move_json_object`).
    """
    move, err, _fc, _loose = parse_character_move_for_attempt(content)
    return move, err


def has_meaningful_rp_body(data: dict[str, Any]) -> bool:
    """True when beats and motivation are present enough for schema-recoverable repair (#250)."""
    beats = data.get("beats")
    if not isinstance(beats, list) or len(beats) < 1:
        return False
    mot = data.get("motivation")
    if not isinstance(mot, dict):
        return False
    for req in ("goal", "tactic", "emotional_driver", "risk_level"):
        if not str(mot.get(req, "") or "").strip():
            return False
    return True


def classify_ingress_failure(error: str, data: dict[str, Any] | None) -> ParseFailureClass:
    """Classify after JSON load failed strict ingest (repair lane routing only)."""
    err = str(error or "").strip()
    if not err:
        return "ok"
    if data is None or not isinstance(data, dict):
        return "unrecoverable"
    if not has_meaningful_rp_body(data):
        return "unrecoverable"

    unrecoverable_prefixes = (
        "No JSON object found",
        "Unclosed markdown",
        "Invalid JSON:",
        "Parse error:",
        "duplicate key",
        "JSON payload must be an object",
        "move_schema_version is required",
        "move_schema_version must be a JSON integer",
        "Unsupported move_schema_version",
        "invalid mixed document",
        "prohibited root key",
        "beats must be a non-empty array",
        "beats exceeds cap",
        "action string exceeds cap",
        "dialogue string exceeds cap",
        "motivation must be an object",
        "motivation missing or empty required key",
        "each beat must be an object",
        "invalid beat type",
        "action beat requires non-empty action",
        "speech beat requires non-empty dialogue",
        "semantic_proposals: [] is not allowed",
    )
    if any(err.startswith(p) or p in err for p in unrecoverable_prefixes):
        return "unrecoverable"

    recoverable_markers = (
        "unknown fields on semantic_evaluation",
        "unknown fields on semantic_proposals",
        "semantic_evaluation.proposals[",
        "semantic_evaluation and root semantic_proposals",
        "unknown v2 root keys",
        "invalid semantic_evaluation.proposals",
        "semantic_evaluation.decision must be",
        "semantic_evaluation must be a JSON object",
        "semantic_evaluation.proposals must be",
    )
    if any(m in err for m in recoverable_markers):
        return "schema_recoverable"

    if "unknown fields on" in err and "beat" in err:
        return "schema_recoverable"

    return "unrecoverable"


def load_loose_character_move_dict(content: str) -> tuple[dict[str, Any] | None, str]:
    """JSON load only (no strict ingest). For repair-lane classification."""
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
    return data, ""


def parse_character_move_for_attempt(
    content: str,
) -> tuple[CanonicalV2Move | None, str, ParseFailureClass, dict[str, Any] | None]:
    """Strict parse plus failure class and loose dict for #250 repair lane."""
    loose, load_err = load_loose_character_move_dict(content)
    if load_err:
        return None, load_err, "unrecoverable", None
    assert loose is not None
    move, err = ingest_character_move_json_object(loose)
    if not err and move is not None:
        return move, "", "ok", loose
    failure_class = classify_ingress_failure(err or "ingress rejected", loose)
    return None, err or "ingress rejected", failure_class, loose
