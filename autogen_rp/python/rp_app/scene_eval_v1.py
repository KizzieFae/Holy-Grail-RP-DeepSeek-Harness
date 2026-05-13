"""Minimal offline scene evaluation (GitHub Issue #66 v1; bundle v2 — #141).

Descriptive judgments only over existing audit artifacts. Does not read
``context_snapshot``. Does not use character audit derived dimensions,
Audit v2 checks, narrator/prose heuristics, or LLM audit layers.

Includes a mechanical ``move_schema_version`` / ``beats[]`` shape judgment for
character rows (GitHub #141). See governance issue #66 for intent; judgments
are not runtime gates.

Terminology (**GitHub #211**): ``SCENE_EVAL_VERSION`` / emitted ``scene_eval_version``
``\"2\"`` means the **Issue #66 output bundle revision** (includes #141 predicates).
It does **not** mean Issue **#69** ``scene_eval_v2`` / ``run_scene_eval_v2``, which is
**specified but not shipped** — see ``AUDIT_DOCUMENTATION.md`` (*Offline evaluation
layer (Issue #69 — scene_eval_v2)*).
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Final

from audit_support_manifest import diff_support_manifests
from issue29_investigation import load_character_audit_rows

SCENE_EVAL_VERSION: Final[str] = "2"

PREDICATE_PAIRWISE: Final[str] = "support_manifest.non_envelope_pairwise_delta"
PREDICATE_PAIRWISE_VER: Final[str] = "1"

PREDICATE_STRUCT: Final[str] = "structured_eval.progression_retry_metrics_mirror"
PREDICATE_STRUCT_VER: Final[str] = "1"

PREDICATE_INTEGRITY: Final[str] = "session.character_rows_integrity"
PREDICATE_INTEGRITY_VER: Final[str] = "1"

PREDICATE_MOVE_SHAPE: Final[str] = "parsed_output.move_schema_shape"
PREDICATE_MOVE_SHAPE_VER: Final[str] = "1"


def _get_support_manifest(row: dict[str, Any]) -> dict[str, Any] | None:
    md = row.get("metadata")
    if not isinstance(md, dict):
        return None
    sm = md.get("support_manifest")
    return sm if isinstance(sm, dict) else None


def _manifest_diff_includes_non_envelope(diff: dict[str, Any]) -> bool:
    """True if diff involves any unit type other than prompt_envelope (Issue #29)."""

    def _types(entries: Any) -> set[str]:
        out: set[str] = set()
        if not isinstance(entries, list):
            return out
        for e in entries:
            if isinstance(e, dict) and isinstance(e.get("type"), str):
                out.add(e["type"])
        return out

    for key in ("support_absent", "support_new"):
        for t in _types(diff.get(key)):
            if t != "prompt_envelope":
                return True
    for e in diff.get("support_changed") or []:
        if isinstance(e, dict) and e.get("type") != "prompt_envelope":
            return True
    return False


def _judgment(
    *,
    predicate_id: str,
    predicate_version: str,
    result: str,
    subject: dict[str, Any] | None,
    summary: str,
    limitations: list[str],
) -> dict[str, Any]:
    return {
        "predicate_id": predicate_id,
        "predicate_version": predicate_version,
        "result": result,
        "subject": subject,
        "summary": summary,
        "limitations": list(limitations),
    }


def _integrity_judgments(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if rows:
        return []
    return [
        _judgment(
            predicate_id=PREDICATE_INTEGRITY,
            predicate_version=PREDICATE_INTEGRITY_VER,
            result="inconclusive",
            subject=None,
            summary="No character *_full.json rows were loaded for this session directory.",
            limitations=[
                "Mechanical check only; empty input prevents other predicates from applying.",
                "Not a verdict on system correctness.",
            ],
        )
    ]


def _pairwise_judgments(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not rows:
        return out

    by_bot: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        name = str(r.get("bot_name") or "").strip()
        if not name:
            continue
        by_bot[name].append(r)

    lim_base = [
        "Descriptive only; fired does not indicate a defect or continuity failure.",
        "Compares adjacent character rows for the same bot_name in loader order only; "
        "does not interpolate missing turns.",
        "Does not use context_snapshot or heuristic audit layers.",
    ]

    for bot_name, bot_rows in sorted(by_bot.items()):
        if len(bot_rows) < 2:
            continue
        for i in range(len(bot_rows) - 1):
            prev, curr = bot_rows[i], bot_rows[i + 1]
            path_obj = curr.get("_path")
            path_str = str(path_obj) if path_obj is not None else ""
            subj: dict[str, Any] = {
                "bot_name": bot_name,
                "round": int(curr.get("round_number") or 0),
                "turn": int(curr.get("turn_number") or 0),
                "path": path_str,
            }
            mp = _get_support_manifest(prev)
            mc = _get_support_manifest(curr)
            if mp is None or mc is None:
                out.append(
                    _judgment(
                        predicate_id=PREDICATE_PAIRWISE,
                        predicate_version=PREDICATE_PAIRWISE_VER,
                        result="inconclusive",
                        subject=subj,
                        summary=(
                            "Adjacent rows: missing metadata.support_manifest on one or both sides."
                        ),
                        limitations=lim_base
                        + [
                            "Required manifest data absent; no pairwise diff applied.",
                        ],
                    )
                )
                continue

            diff = diff_support_manifests(mp, mc)
            if _manifest_diff_includes_non_envelope(diff):
                out.append(
                    _judgment(
                        predicate_id=PREDICATE_PAIRWISE,
                        predicate_version=PREDICATE_PAIRWISE_VER,
                        result="fired",
                        subject=subj,
                        summary=(
                            "Adjacent rows for this actor show a non-prompt_envelope "
                            "support manifest diff."
                        ),
                        limitations=lim_base,
                    )
                )
            else:
                out.append(
                    _judgment(
                        predicate_id=PREDICATE_PAIRWISE,
                        predicate_version=PREDICATE_PAIRWISE_VER,
                        result="clear",
                        subject=subj,
                        summary=(
                            "Adjacent rows: no non-prompt_envelope support manifest diff observed."
                        ),
                        limitations=lim_base
                        + [
                            "clear is not proof of correctness or full audit coverage.",
                        ],
                    )
                )
    return out


def _move_schema_shape_judgments(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Mechanical check: v2 rows must carry non-empty ``beats[]`` in ``parsed_output``."""
    lim = [
        "Mechanical shape only; does not validate beat schemas or speech content.",
        "Legacy rows without move_schema_version 2 are counted but not required to have beats.",
    ]
    if not rows:
        return []

    v2_count = 0
    v2_bad = 0
    legacy_count = 0
    for r in rows:
        po = r.get("parsed_output")
        if not isinstance(po, dict):
            continue
        try:
            msv = int(str(po.get("move_schema_version", 0) or 0) or 0)
        except (TypeError, ValueError):
            msv = 0
        if msv == 2:
            v2_count += 1
            beats = po.get("beats")
            if not isinstance(beats, list) or len(beats) == 0:
                v2_bad += 1
        else:
            legacy_count += 1

    if v2_bad:
        return [
            _judgment(
                predicate_id=PREDICATE_MOVE_SHAPE,
                predicate_version=PREDICATE_MOVE_SHAPE_VER,
                result="fired",
                subject=None,
                summary=(
                    f"{v2_bad} character row(s) declare move_schema_version 2 but lack "
                    f"non-empty beats[]."
                ),
                limitations=lim,
            )
        ]

    parts: list[str] = []
    if v2_count:
        parts.append(f"{v2_count} row(s) with move_schema_version 2 and non-empty beats[]")
    if legacy_count:
        parts.append(
            f"{legacy_count} row(s) legacy or non-v2 parsed_output (root dialogue/action ok)"
        )
    summary = "; ".join(parts) if parts else "No character parsed_output classified"
    return [
        _judgment(
            predicate_id=PREDICATE_MOVE_SHAPE,
            predicate_version=PREDICATE_MOVE_SHAPE_VER,
            result="clear",
            subject=None,
            summary=summary + ".",
            limitations=lim,
        )
    ]


def _structured_eval_judgments(structured_eval_path: Path | None) -> list[dict[str, Any]]:
    lim = [
        "Descriptive mirror of structured_eval fields only; not a failure or quality signal.",
        "Does not interpret retries as regressions or scene health.",
    ]
    if structured_eval_path is None:
        return [
            _judgment(
                predicate_id=PREDICATE_STRUCT,
                predicate_version=PREDICATE_STRUCT_VER,
                result="inconclusive",
                subject=None,
                summary="structured_eval_path was not provided.",
                limitations=lim
                + [
                    "No structured_eval file loaded.",
                ],
            )
        ]

    path = structured_eval_path.expanduser().resolve()
    if not path.is_file():
        return [
            _judgment(
                predicate_id=PREDICATE_STRUCT,
                predicate_version=PREDICATE_STRUCT_VER,
                result="inconclusive",
                subject=None,
                summary=f"structured_eval path is not a file: {path}",
                limitations=lim,
            )
        ]

    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError) as e:
        return [
            _judgment(
                predicate_id=PREDICATE_STRUCT,
                predicate_version=PREDICATE_STRUCT_VER,
                result="inconclusive",
                subject=None,
                summary=f"Could not read or parse structured_eval JSON: {e}",
                limitations=lim,
            )
        ]

    if not isinstance(data, dict):
        return [
            _judgment(
                predicate_id=PREDICATE_STRUCT,
                predicate_version=PREDICATE_STRUCT_VER,
                result="inconclusive",
                subject=None,
                summary="structured_eval root is not a JSON object.",
                limitations=lim,
            )
        ]

    metrics = data.get("metrics")
    if not isinstance(metrics, dict) or "progression_retries_triggered" not in metrics:
        return [
            _judgment(
                predicate_id=PREDICATE_STRUCT,
                predicate_version=PREDICATE_STRUCT_VER,
                result="inconclusive",
                subject=None,
                summary=(
                    "structured_eval.metrics.progression_retries_triggered is missing "
                    "or metrics is not an object."
                ),
                limitations=lim,
            )
        ]

    prt = metrics["progression_retries_triggered"]
    parts = [f"progression_retries_triggered is {prt!r} in structured_eval.metrics"]

    events = data.get("sim_progression_metrics_events")
    if isinstance(events, list):
        n_retry = sum(
            1 for e in events if isinstance(e, dict) and e.get("kind") == "progression_retry"
        )
        parts.append(
            f"sim_progression_metrics_events contains {n_retry} "
            f"entr{'y' if n_retry == 1 else 'ies'} with kind progression_retry"
        )

    return [
        _judgment(
            predicate_id=PREDICATE_STRUCT,
            predicate_version=PREDICATE_STRUCT_VER,
            result="fired",
            subject=None,
            summary="; ".join(parts) + ".",
            limitations=lim,
        )
    ]


def run_scene_eval_v1(
    session_dir: Path | str,
    *,
    structured_eval_path: Path | str | None = None,
) -> dict[str, Any]:
    """Run Issue #66 v1 evaluation over one audit session directory.

    Loads character rows only via ``load_character_audit_rows``. Optional
    ``structured_eval`` JSON (e.g. from ``build_structured_eval_payload``) may
    be supplied for a descriptive metrics mirror judgment.

    Returns a dict with ``scene_eval_version``, paths, and ``judgments``.
    The ``scene_eval_version`` field is ``SCENE_EVAL_VERSION`` (currently ``\"2\"``):
    **Issue #66 bundle revision**, not Issue **#69** ``scene_eval_v2`` (see module
    docstring and ``AUDIT_DOCUMENTATION.md``).
    """
    sd = Path(session_dir).expanduser().resolve()
    sep: Path | None = None
    if structured_eval_path is not None:
        sep = Path(structured_eval_path).expanduser()

    rows = load_character_audit_rows(sd)
    judgments: list[dict[str, Any]] = []
    judgments.extend(_integrity_judgments(rows))
    judgments.extend(_pairwise_judgments(rows))
    judgments.extend(_move_schema_shape_judgments(rows))
    judgments.extend(_structured_eval_judgments(sep))

    return {
        "scene_eval_version": SCENE_EVAL_VERSION,
        "session_dir": str(sd),
        "structured_eval_path": str(sep) if sep is not None else None,
        "judgments": judgments,
    }
