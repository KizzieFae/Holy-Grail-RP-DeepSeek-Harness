"""Scene opener management for RP app.

Handles loading, selecting, and managing scene opening messages
for narrator-mediated scene starts.
"""

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

_V2 = Path(__file__).resolve().parents[2]
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain.paths import characters_data_dir, scene_templates_data_dir  # noqa: E402
from scene_template import SceneTemplateManager, TemplateInitialMessage  # noqa: E402


@dataclass
class SceneOpener:
    """A scene opening message asset."""

    id: str
    source: str  # 'character', 'general', or 'custom'
    owner: Optional[str]  # character name if character-specific
    label: str
    text: str
    tags: list[str]
    location: Optional[str] = None
    time: Optional[str] = None
    # Passthrough from Opener JSON (AUTHORED_SOURCE_CONTRACT §6); not inferred from `text`.
    description: Optional[str] = None


def _opener_description_from_json(opener_data: dict[str, Any]) -> Optional[str]:
    """File `description` only: absent, empty, or non-string -> None (no synthesis)."""
    raw = opener_data.get("description")
    if raw is None:
        return None
    if not isinstance(raw, str):
        return None
    s = raw.strip()
    return s if s else None


class OpenerManager:
    """Manages scene opening message assets."""

    def __init__(
        self, characters_dir: str | Path = None, templates_dir: str | Path = None
    ) -> None:
        """Initialize the opener manager.

        Args:
            characters_dir: Directory containing character files with openers.
        """
        if characters_dir is None:
            self.characters_dir = characters_data_dir()
        else:
            self.characters_dir = Path(characters_dir)
        if templates_dir is None:
            self.templates_dir = scene_templates_data_dir()
        else:
            self.templates_dir = Path(templates_dir)

    def _load_opener_file(
        self, opener_file: Path, *, source: str, owner: str
    ) -> list[SceneOpener]:
        openers: list[SceneOpener] = []
        if opener_file.exists():
            try:
                with open(opener_file, "r", encoding="utf-8") as f:
                    opener_data = json.load(f)

                text = opener_data.get("text", "").strip()
                if text:
                    opener = SceneOpener(
                        id=str(opener_data.get("id", "default") or "default"),
                        source=source,
                        owner=owner,
                        label=opener_data.get(
                            "label", f"{owner.replace('_', ' ').title()} Default"
                        ),
                        text=text,
                        tags=opener_data.get("tags", []),
                        location=opener_data.get("location"),
                        time=opener_data.get("time"),
                        description=_opener_description_from_json(opener_data),
                    )
                    openers.append(opener)
            except Exception:
                pass
        return openers

    def get_character_openers(self, character_file: str) -> list[SceneOpener]:
        """Get available openers for a specific character.

        Looks for files named:
        - <name>_initial_message.json (in autogen_characters folder)
        - Supports composite names like "Marlene_and_Willow_initial_message.json"

        Returns list of openers found for this character.
        """
        char_name = character_file.replace(".json", "")
        opener_file = self.characters_dir / f"{char_name}_initial_message.json"
        return self._load_opener_file(opener_file, source="character", owner=char_name)

    def get_template_openers(
        self, template_id: str, template_manager: SceneTemplateManager | None = None
    ) -> list[SceneOpener]:
        """Get available openers for a scene template.

        Checks in priority order:
        1. Explicit initial_messages declared in the template JSON
        2. File named {template_id}_initial_message.json (legacy fallback)

        Returns list of openers found for this template.
        """
        normalized_template_id = str(template_id or "").replace(".json", "").strip()
        if not normalized_template_id:
            return []

        openers: list[SceneOpener] = []

        # First: try explicit initial_messages from template
        if template_manager is None:
            template_manager = SceneTemplateManager(self.templates_dir)
        try:
            template = template_manager.load_template(normalized_template_id)
            for msg_ref in template.initial_messages:
                opener_file = self.templates_dir / msg_ref.file
                loaded = self._load_opener_file(
                    opener_file,
                    source="template",
                    owner=normalized_template_id,
                )
                if loaded:
                    # Override label with explicit label from template
                    for opener in loaded:
                        opener.label = msg_ref.label or opener.label
                    openers.extend(loaded)
        except Exception:
            # Template may not exist or initial_messages may be malformed
            pass

        # Second: fallback to legacy filename convention
        if not openers:
            opener_file = (
                self.templates_dir / f"{normalized_template_id}_initial_message.json"
            )
            openers = self._load_opener_file(
                opener_file, source="template", owner=normalized_template_id
            )

        return openers

    def get_default_character_opener(
        self, character_file: str
    ) -> Optional[SceneOpener]:
        """Get the default opener for a character.

        Returns the first (and typically only) opener found.
        """
        openers = self.get_character_openers(character_file)
        return openers[0] if openers else None

    def get_default_template_opener(self, template_id: str) -> Optional[SceneOpener]:
        openers = self.get_template_openers(template_id)
        return openers[0] if openers else None

    def _format_label(self, char_name: str) -> str:
        """Convert character filename to human-readable label."""
        # Replace underscores with spaces, clean up
        name = char_name.replace("_", " ").replace("-", " ")
        # Title case
        return name.title()


def _normalize_owner_identifier(value: str) -> str:
    return (
        str(value or "")
        .replace(".json", "")
        .replace("_", " ")
        .replace("-", " ")
        .strip()
        .lower()
    )


def resolve_scene_opener(
    opener_manager: OpenerManager,
    selected_chars: list[str],
    scene_owner: str,
    opening_mode: str,
    scene_template_id: Optional[str] = None,
    specific_opener_id: Optional[str] = None,
    custom_text: Optional[str] = None,
) -> Optional[SceneOpener]:
    """Resolve which opener to use based on selection criteria.

    Priority:
    1. Custom text (if opening_mode is 'custom' and text provided)
    2. Specific opener selection (if opening_mode is not 'custom' and specific_opener_id provided)
    3. Owner's default opener (if opening_mode is 'character')
    4. Template opener (if opening_mode is 'template')

    Returns:
        SceneOpener to use, or None if should fall back to generation
    """
    # Mode: Custom text
    if opening_mode == "custom" and custom_text and custom_text.strip():
        return SceneOpener(
            id="custom",
            source="custom",
            owner=None,
            label="Custom Opener",
            text=custom_text.strip(),
            tags=[],
        )

    if opening_mode == "template" and scene_template_id:
        if specific_opener_id:
            openers = opener_manager.get_template_openers(scene_template_id)
            for opener in openers:
                if (
                    opener.id == specific_opener_id
                    or opener.label == specific_opener_id
                ):
                    return opener
        return opener_manager.get_default_template_opener(scene_template_id)

    # Mode: Character opener
    if opening_mode == "character":
        # Find owner character file
        owner_file = None
        normalized_scene_owner = _normalize_owner_identifier(scene_owner)
        for char_file in selected_chars:
            normalized_char_file = _normalize_owner_identifier(char_file)
            if (
                normalized_scene_owner == normalized_char_file
                or normalized_scene_owner in normalized_char_file
            ):
                owner_file = char_file
                break

        if owner_file:
            # If specific opener selected, find it
            if specific_opener_id:
                openers = opener_manager.get_character_openers(owner_file)
                for opener in openers:
                    if (
                        opener.id == specific_opener_id
                        or opener.label == specific_opener_id
                    ):
                        return opener

            # Otherwise use default
            return opener_manager.get_default_character_opener(owner_file)

    # Mode: General opener (not yet implemented - would need general openers folder)
    # For now, fall through to None

    # Fallback: no opener available
    return None


def resolve_opening_text(
    scene_setup: Optional[dict[str, Any]],
    opener: Optional[SceneOpener],
) -> str:
    if opener and opener.text.strip():
        return opener.text.strip()

    if scene_setup and str(scene_setup.get("opening_text", "") or "").strip():
        return str(scene_setup.get("opening_text", "") or "").strip()

    return ""


# --- Issue #94: canonical opener refs (id-only; labels never appear in ref) ---

_TEMPLATE_OPENER_PREFIX = "template_opener:"
_CHARACTER_OPENER_PREFIX = "character_opener:"


def build_template_opener_ref(template_id: str, opener_asset_id: str) -> str:
    tid = str(template_id or "").replace(".json", "").strip()
    oid = str(opener_asset_id or "").strip()
    if not tid or not oid:
        raise ValueError("template_id and opener_asset_id required for template opener ref")
    return f"{_TEMPLATE_OPENER_PREFIX}{tid}:{oid}"


def build_character_opener_ref(character_card_stem: str, opener_asset_id: str) -> str:
    stem = str(character_card_stem or "").replace(".json", "").strip()
    oid = str(opener_asset_id or "").strip()
    if not stem or not oid:
        raise ValueError("character_card_stem and opener_asset_id required")
    return f"{_CHARACTER_OPENER_PREFIX}{stem}:{oid}"


def resolve_scene_opener_from_canonical_ref(
    opener_manager: OpenerManager,
    ref: str,
) -> Optional[SceneOpener]:
    """Load opener by canonical ref; returns None only if ref malformed (caller may treat as failure)."""
    r = str(ref or "").strip()
    if r.startswith(_TEMPLATE_OPENER_PREFIX):
        rest = r[len(_TEMPLATE_OPENER_PREFIX) :]
        tid, _, asset_id = rest.partition(":")
        if not tid or not asset_id:
            return None
        openers = opener_manager.get_template_openers(tid)
        for o in openers:
            if o.id == asset_id:
                return o
        return None
    if r.startswith(_CHARACTER_OPENER_PREFIX):
        rest = r[len(_CHARACTER_OPENER_PREFIX) :]
        stem, _, asset_id = rest.partition(":")
        if not stem or not asset_id:
            return None
        char_file = f"{stem}.json"
        openers = opener_manager.get_character_openers(char_file)
        for o in openers:
            if o.id == asset_id:
                return o
        return None
    return None


def template_intent_has_opener_assets(template_id: str, opener_manager: OpenerManager) -> bool:
    """True if template declares or legacy file provides at least one opener asset path."""
    normalized_template_id = str(template_id or "").replace(".json", "").strip()
    if not normalized_template_id:
        return False
    try:
        template_manager = SceneTemplateManager(opener_manager.templates_dir)
        template = template_manager.load_template(normalized_template_id)
        if template.initial_messages:
            return True
    except Exception:
        pass
    legacy = (
        opener_manager.templates_dir / f"{normalized_template_id}_initial_message.json"
    )
    return legacy.is_file()
