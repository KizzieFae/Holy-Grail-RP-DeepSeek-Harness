"""Shared opening-strategy helpers (Streamlit + headless) — Issue #165 split."""

from __future__ import annotations

from typing import Any

from scene_opener import OpenerManager, SceneOpener, resolve_scene_opener_from_canonical_ref

from bootstrap_context_inputs import _strip
from bootstrap_interpretation import BootstrapCompositionError

OPENING_STRATEGIES = frozenset(
    {"template_asset", "character_asset", "template_static_text", "generated"}
)


def _normalize_template_opener_selection_to_asset_id(
    *,
    opener_manager: OpenerManager,
    template_id: str,
    specific_opener_id: str | None,
) -> str:
    """Map UI/harness selection to opener JSON ``id`` (id-only refs)."""
    openers = opener_manager.get_template_openers(template_id)
    if not openers:
        raise BootstrapCompositionError(
            f"no template openers available for template {template_id!r}"
        )
    sel = _strip(specific_opener_id)
    if not sel:
        if len(openers) != 1:
            raise BootstrapCompositionError(
                "template opener selection required when multiple template openers exist"
            )
        return str(openers[0].id)
    by_id = [o for o in openers if o.id == sel]
    if len(by_id) == 1:
        return str(by_id[0].id)
    by_label = [o for o in openers if o.label == sel]
    if len(by_label) == 1:
        return str(by_label[0].id)
    raise BootstrapCompositionError(
        f"ambiguous or unknown template opener selection {sel!r} for {template_id!r}"
    )


def lock_headless_opening_strategy_intent(
    *,
    opening_description: str,
    scene_setup: dict[str, Any] | None,
) -> tuple[str, str | None]:
    if _strip(opening_description):
        return "template_static_text", None
    opening_text = _strip(scene_setup.get("opening_text") if scene_setup else None)
    if opening_text:
        return "template_static_text", None
    raise BootstrapCompositionError(
        "headless scene-start requires non-empty opening_description or template opening_text"
    )


def _resolve_opening_text_after_lock(
    *,
    strategy: str,
    opening_ref: str | None,
    opener_manager: OpenerManager,
    static_text_operand: str,
) -> tuple[str, SceneOpener | None]:
    if strategy in ("template_asset", "character_asset"):
        if not opening_ref:
            raise BootstrapCompositionError("asset strategy requires opening_ref")
        opener = resolve_scene_opener_from_canonical_ref(opener_manager, opening_ref)
        if opener is None:
            raise BootstrapCompositionError(
                f"opener asset resolution failed for ref {opening_ref!r}"
            )
        text = _strip(opener.text)
        if not text:
            raise BootstrapCompositionError(
                f"opener asset has empty text for ref {opening_ref!r}"
            )
        return text, opener
    if strategy == "template_static_text":
        t = _strip(static_text_operand)
        if not t:
            raise BootstrapCompositionError("template_static_text requires non-empty text")
        return t, None
    raise BootstrapCompositionError(f"unexpected strategy for asset resolve: {strategy!r}")
