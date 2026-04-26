import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

import ui_sidebar_scene_setup as scene_setup
from scene_template import SceneRoleSlot, SceneTemplate


class FakeStreamlit:
    def __init__(self) -> None:
        self.session_state: dict[str, object] = {}
        self.multiselect_calls: list[dict[str, object]] = []
        self.subheader_calls: list[str] = []

    def subheader(self, title: str, *_args, **_kwargs) -> None:
        self.subheader_calls.append(str(title))
        return None

    def caption(self, *_args, **_kwargs) -> None:
        return None

    def markdown(self, *_args, **_kwargs) -> None:
        return None

    def warning(self, *_args, **_kwargs) -> None:
        return None

    def info(self, *_args, **_kwargs) -> None:
        return None

    def error(self, *_args, **_kwargs) -> None:
        return None

    def divider(self) -> None:
        return None

    def multiselect(
        self,
        label: str,
        *,
        options: list[str],
        default: list[str],
        key: str,
        disabled: bool = False,
    ):
        self.multiselect_calls.append(
            {
                "label": label,
                "options": list(options),
                "default": list(default),
                "key": key,
                "disabled": disabled,
            }
        )
        if key in self.session_state:
            return list(self.session_state[key])
        self.session_state[key] = list(default)
        return list(default)

    def number_input(
        self,
        _label: str,
        *,
        min_value: int,
        max_value: int,
        value: int,
        step: int,
        key: str,
    ) -> int:
        if key in self.session_state:
            stored = int(self.session_state[key])
            stored = max(min_value, min(stored, max_value))
            return stored
        clamped = max(min_value, min(int(value), max_value))
        self.session_state[key] = clamped
        return clamped

    def selectbox(
        self,
        _label: str,
        *,
        options: list[str],
        index: int = 0,
        key: str,
        disabled: bool = False,
    ):
        value = options[index]
        if not disabled:
            self.session_state[key] = value
        return value

    def radio(
        self,
        _label: str,
        *,
        options: list[str],
        index: int = 0,
        format_func=None,
        key: str,
    ):
        value = options[index]
        self.session_state[key] = value
        return value

    def toggle(self, _label: str, *, value: bool, key: str, disabled: bool = False):
        if disabled and key in self.session_state:
            return bool(self.session_state[key])
        self.session_state[key] = bool(value)
        return bool(value)

    def button(self, *_args, **_kwargs) -> bool:
        return False


class FakeTemplateManager:
    def list_templates(self):
        return []


async def _unused_start_scene(_selected_chars: list[str]) -> bool:
    return True


def test_scene_setup_does_not_change_bot_reply_limit_mid_scene(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        scene_setup, "load_character_names", lambda **_kwargs: ["A", "B", "C"]
    )
    monkeypatch.setattr(scene_setup, "render_opening_controls", lambda **_kwargs: None)

    st = FakeStreamlit()
    st.session_state.update(
        {
            "scene_started": True,
            "selected_chars": ["a", "b", "c"],
            "bot_reply_limit": 3,
            "player_character": None,
            "opening_mode": "custom",
            "audit_enabled": False,
        }
    )

    scene_setup.render_scene_setup_controls(
        st_module=st,
        available=["a", "b", "c"],
        character_loader_cls=object(),
        has_player_character_conflict_fn=lambda *_args, **_kwargs: False,
        scene_template_manager_cls=FakeTemplateManager,
        opener_manager_cls=object(),
        resolve_character_file_fn=lambda *_args, **_kwargs: None,
        start_scene_fn=_unused_start_scene,
    )

    assert st.session_state["bot_reply_limit"] == 3
    assert st.multiselect_calls
    call = st.multiselect_calls[0]
    assert call["disabled"] is True
    assert call["default"] == ["a", "b", "c"]
    assert "Scene Owner" not in st.subheader_calls


def test_scene_setup_does_not_seed_bot_reply_limit_when_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Issue #103 Model A: UI does not write ``bot_reply_limit``; Start Scene will."""
    monkeypatch.setattr(
        scene_setup, "load_character_names", lambda **_kwargs: ["A", "B", "C"]
    )
    monkeypatch.setattr(scene_setup, "render_opening_controls", lambda **_kwargs: None)

    st = FakeStreamlit()
    st.session_state.update(
        {
            "scene_started": True,
            "selected_chars": ["a", "b", "c"],
            "bot_reply_limit": None,
            "player_character": None,
            "opening_mode": "custom",
            "audit_enabled": False,
        }
    )

    scene_setup.render_scene_setup_controls(
        st_module=st,
        available=["a", "b", "c"],
        character_loader_cls=object(),
        has_player_character_conflict_fn=lambda *_args, **_kwargs: False,
        scene_template_manager_cls=FakeTemplateManager,
        opener_manager_cls=object(),
        resolve_character_file_fn=lambda *_args, **_kwargs: None,
        start_scene_fn=_unused_start_scene,
    )

    assert st.session_state.get("bot_reply_limit") is None
    assert "Scene Owner" not in st.subheader_calls


def test_fresh_pre_start_uses_empty_npc_multiselect_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Issue #104: no implicit sorted two-NPC default; pre-start default is empty."""
    monkeypatch.setattr(
        scene_setup, "load_character_names", lambda **_kwargs: ["A", "B", "C"]
    )
    monkeypatch.setattr(scene_setup, "render_opening_controls", lambda **_kwargs: None)

    st = FakeStreamlit()
    st.session_state.update(
        {
            "scene_started": False,
            "bot_reply_limit": None,
            "player_character": None,
            "opening_mode": "custom",
            "audit_enabled": False,
        }
    )

    scene_setup.render_scene_setup_controls(
        st_module=st,
        available=["a", "b", "c"],
        character_loader_cls=object(),
        has_player_character_conflict_fn=lambda *_args, **_kwargs: False,
        scene_template_manager_cls=FakeTemplateManager,
        opener_manager_cls=object(),
        resolve_character_file_fn=lambda *_args, **_kwargs: None,
        start_scene_fn=_unused_start_scene,
    )

    assert st.multiselect_calls
    assert st.multiselect_calls[0]["default"] == []


def test_scene_setup_pre_start_leaves_bot_reply_limit_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Multiple NPC changes before Start Scene do not require seeding the limit (Issue #103)."""
    monkeypatch.setattr(
        scene_setup, "load_character_names", lambda **_kwargs: ["A", "B", "C"]
    )
    monkeypatch.setattr(scene_setup, "render_opening_controls", lambda **_kwargs: None)

    st = FakeStreamlit()
    st.session_state.update(
        {
            "scene_started": False,
            "npc_selection": ["a", "b", "c"],
            "bot_reply_limit": None,
            "player_character": None,
            "opening_mode": "custom",
            "audit_enabled": False,
        }
    )
    st.session_state["npc_selection"] = ["a", "b", "c"]

    scene_setup.render_scene_setup_controls(
        st_module=st,
        available=["a", "b", "c"],
        character_loader_cls=object(),
        has_player_character_conflict_fn=lambda *_args, **_kwargs: False,
        scene_template_manager_cls=FakeTemplateManager,
        opener_manager_cls=object(),
        resolve_character_file_fn=lambda *_args, **_kwargs: None,
        start_scene_fn=_unused_start_scene,
    )

    assert st.session_state.get("bot_reply_limit") is None


def test_scene_setup_syncs_scene_owner_without_scene_owner_ui(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Issue #102: internal scene_owner defaults to first cast display name pre-start (explicit selection)."""
    monkeypatch.setattr(
        scene_setup, "load_character_names", lambda **_kwargs: ["Alpha", "Beta", "Gamma"]
    )
    monkeypatch.setattr(scene_setup, "render_opening_controls", lambda **_kwargs: None)

    st = FakeStreamlit()
    st.session_state.update(
        {
            "scene_started": False,
            "npc_selection": ["a", "b", "c"],
            "player_character": None,
            "opening_mode": "custom",
            "audit_enabled": False,
        }
    )

    scene_setup.render_scene_setup_controls(
        st_module=st,
        available=["a", "b", "c"],
        character_loader_cls=object(),
        has_player_character_conflict_fn=lambda *_args, **_kwargs: False,
        scene_template_manager_cls=FakeTemplateManager,
        opener_manager_cls=object(),
        resolve_character_file_fn=lambda *_args, **_kwargs: None,
        start_scene_fn=_unused_start_scene,
    )

    assert st.session_state["scene_owner"] == "Alpha"
    assert "Scene Owner" not in st.subheader_calls


def test_scene_setup_preserves_scene_owner_when_still_in_cast(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        scene_setup, "load_character_names", lambda **_kwargs: ["Alpha", "Beta", "Gamma"]
    )
    monkeypatch.setattr(scene_setup, "render_opening_controls", lambda **_kwargs: None)

    st = FakeStreamlit()
    st.session_state.update(
        {
            "scene_started": False,
            "npc_selection": ["a", "b", "c"],
            "scene_owner": "Gamma",
            "player_character": None,
            "opening_mode": "custom",
            "audit_enabled": False,
        }
    )

    scene_setup.render_scene_setup_controls(
        st_module=st,
        available=["a", "b", "c"],
        character_loader_cls=object(),
        has_player_character_conflict_fn=lambda *_args, **_kwargs: False,
        scene_template_manager_cls=FakeTemplateManager,
        opener_manager_cls=object(),
        resolve_character_file_fn=lambda *_args, **_kwargs: None,
        start_scene_fn=_unused_start_scene,
    )

    assert st.session_state["scene_owner"] == "Gamma"


def test_issue128_role_assignment_pool_appends_player_not_in_bot_multiselect() -> None:
    """Player file is excluded from NPC options but included in template role-assignment pool."""
    bot = ["npc_a.json"]
    player = "user_pc.json"
    available = ["npc_a.json", "user_pc.json"]
    assert scene_setup._template_role_assignment_char_files(
        bot_selected_char_files=bot,
        player_char_file=player,
        available_char_files=available,
    ) == ["npc_a.json", "user_pc.json"]


def test_issue128_role_assignment_pool_without_player_unchanged() -> None:
    bot = ["a.json", "b.json"]
    assert scene_setup._template_role_assignment_char_files(
        bot_selected_char_files=bot,
        player_char_file=None,
        available_char_files=bot,
    ) == bot


def test_issue128_role_assignment_pool_skips_unknown_player_file() -> None:
    assert scene_setup._template_role_assignment_char_files(
        bot_selected_char_files=["a.json"],
        player_char_file="missing.json",
        available_char_files=["a.json"],
    ) == ["a.json"]


class FakeStreamlitIssue128(FakeStreamlit):
    """Selectbox picks concrete roles for template assignment keys (placeholder is option index 0)."""

    def selectbox(
        self,
        label: str,
        *,
        options: list[str],
        index: int = 0,
        key: str,
        disabled: bool = False,
    ):
        if key.startswith("scene_role_assignment_"):
            role_choices = [o for o in options if o]
            if "user_pc" in key and "applicant" in role_choices:
                pick = "applicant"
            elif "host" in role_choices:
                pick = "host"
            else:
                pick = role_choices[0]
            if not disabled:
                self.session_state[key] = pick
            return pick
        value = options[index]
        if not disabled:
            self.session_state[key] = value
        return value


class FakeTemplateManagerIssue128:
    def list_templates(self):
        return [
            SceneTemplate(
                template_id="demo_tpl",
                premise="p",
                opening_text="",
                role_slots=[
                    SceneRoleSlot(
                        role_name="host",
                        required=True,
                        presence_constraint="flexible",
                    ),
                    SceneRoleSlot(
                        role_name="applicant",
                        required=True,
                        presence_constraint="must_remain",
                    ),
                ],
                anchor_role_name="applicant",
            )
        ]


def test_issue128_template_role_rows_include_player_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Role selectboxes are rendered for bots plus the player file (separate from NPC multiselect)."""
    load_calls: list[list[str]] = []

    def _track_names(*, selected_chars: list[str], character_loader_cls: object) -> list[str]:
        load_calls.append(list(selected_chars))
        return [f"NAME:{fn}" for fn in selected_chars]

    monkeypatch.setattr(scene_setup, "load_character_names", _track_names)
    monkeypatch.setattr(scene_setup, "render_opening_controls", lambda **_kwargs: None)

    st = FakeStreamlitIssue128()
    st.session_state.update(
        {
            "scene_started": False,
            "npc_selection": ["npc_a.json"],
            "selected_scene_template_id": "demo_tpl",
            "player_character": "user_pc.json",
            "opening_mode": "custom",
            "audit_enabled": False,
        }
    )

    scene_setup.render_scene_setup_controls(
        st_module=st,
        available=["npc_a.json", "user_pc.json"],
        character_loader_cls=object(),
        has_player_character_conflict_fn=lambda *_a, **_k: False,
        scene_template_manager_cls=FakeTemplateManagerIssue128,
        opener_manager_cls=object(),
        resolve_character_file_fn=lambda *_a, **_k: None,
        start_scene_fn=_unused_start_scene,
    )

    assert st.multiselect_calls[0]["options"] == ["npc_a.json"]
    assert load_calls[0] == ["npc_a.json"]
    assert load_calls[1] == ["npc_a.json", "user_pc.json"]
    assert st.session_state["scene_role_assignments"] == {
        "npc_a.json": "host",
        "user_pc.json": "applicant",
    }
