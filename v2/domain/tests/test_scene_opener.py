import sys
from pathlib import Path


from scene_opener import (
    OpenerManager,
    SceneOpener,
    resolve_opening_text,
    resolve_scene_opener,
)


def test_resolve_opening_text_prefers_selected_opener_over_template_text() -> None:
    opener = SceneOpener(
        id="default",
        source="character",
        owner="celina",
        label="Celina Legacy Rescue",
        text="Celina's authored opener.",
        tags=["legacy_opener"],
    )

    result = resolve_opening_text(
        {"opening_text": "Template opening text."},
        opener,
    )

    assert result == "Celina's authored opener."
    assert opener.description is None


def test_resolve_opening_text_uses_template_text_when_no_opener_is_selected() -> None:
    result = resolve_opening_text(
        {"opening_text": "Template opening text."},
        None,
    )

    assert result == "Template opening text."


def test_opener_manager_loads_template_owned_initial_message(tmp_path: Path) -> None:
    opener_path = tmp_path / "arkham_asylum_cell_intake_initial_message.json"
    opener_path.write_text(
        """
{
  "label": "Arkham Cell Intake",
  "text": "A steel door slams and the new arrival is left inside the cell.",
  "description": "Intake cell opener for new arrivals.",
  "tags": ["arkham", "cell", "intake"],
  "location": "Arkham Asylum - Female Ward Cell",
  "time": "Night"
}
""".strip(),
        encoding="utf-8",
    )

    manager = OpenerManager(characters_dir=tmp_path, templates_dir=tmp_path)

    openers = manager.get_template_openers("arkham_asylum_cell_intake")

    assert len(openers) == 1
    assert openers[0].source == "template"
    assert openers[0].owner == "arkham_asylum_cell_intake"
    assert openers[0].label == "Arkham Cell Intake"
    assert openers[0].description == "Intake cell opener for new arrivals."
    assert openers[0].location == "Arkham Asylum - Female Ward Cell"


def test_opener_manager_description_absent_when_missing_or_blank(tmp_path: Path) -> None:
    path_missing = tmp_path / "t_a_initial_message.json"
    path_missing.write_text(
        '{"id": "a", "text": "Hello", "label": "L"}',
        encoding="utf-8",
    )
    path_whitespace = tmp_path / "t_b_initial_message.json"
    path_whitespace.write_text(
        '{"id": "b", "text": "Hello2", "label": "L2", "description": "   "}',
        encoding="utf-8",
    )
    path_non_str = tmp_path / "t_c_initial_message.json"
    path_non_str.write_text(
        '{"id": "c", "text": "Hello3", "label": "L3", "description": 99}',
        encoding="utf-8",
    )
    m = OpenerManager(characters_dir=tmp_path, templates_dir=tmp_path)
    assert m.get_template_openers("t_a")[0].description is None
    assert m.get_template_openers("t_b")[0].description is None
    assert m.get_template_openers("t_c")[0].description is None


def test_resolve_scene_opener_uses_template_owned_opener_when_template_mode_selected(
    tmp_path: Path,
) -> None:
    opener_path = tmp_path / "arkham_asylum_shower_predation_initial_message.json"
    opener_path.write_text(
        """
{
  "label": "Arkham Shower Predation",
  "text": "Steam gathers under harsh lights as the new arrival steps into the showers.",
  "tags": ["arkham", "showers"],
  "location": "Arkham Asylum - Female Ward Showers",
  "time": "Shower block"
}
""".strip(),
        encoding="utf-8",
    )

    manager = OpenerManager(characters_dir=tmp_path, templates_dir=tmp_path)

    opener = resolve_scene_opener(
        opener_manager=manager,
        selected_chars=["harley_quinn", "poison_ivy"],
        scene_owner="Harley Quinn",
        opening_mode="template",
        scene_template_id="arkham_asylum_shower_predation",
        specific_opener_id="default",
        custom_text=None,
    )

    assert opener is not None
    assert opener.source == "template"
    assert (
        opener.text
        == "Steam gathers under harsh lights as the new arrival steps into the showers."
    )


def test_resolve_scene_opener_matches_display_name_to_character_filename(
    tmp_path: Path,
) -> None:
    opener_path = tmp_path / "harley_quinn_initial_message.json"
    opener_path.write_text(
        """
{
  "label": "Harley Default",
  "text": "Harley is already grinning by the time the new girl steps inside.",
  "tags": ["harley", "legacy_opener"]
}
""".strip(),
        encoding="utf-8",
    )

    manager = OpenerManager(characters_dir=tmp_path, templates_dir=tmp_path)

    opener = resolve_scene_opener(
        opener_manager=manager,
        selected_chars=["harley_quinn", "poison_ivy"],
        scene_owner="Harley Quinn",
        opening_mode="character",
        scene_template_id=None,
        specific_opener_id="default",
        custom_text=None,
    )

    assert opener is not None
    assert opener.source == "character"
    assert opener.owner == "harley_quinn"
    assert (
        opener.text
        == "Harley is already grinning by the time the new girl steps inside."
    )
    assert opener.description is None
