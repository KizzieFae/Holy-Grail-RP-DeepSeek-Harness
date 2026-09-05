"""Issue #125 / G-125-01 — role_private deterministic projection tests."""

from __future__ import annotations

import unittest

from domain_api.contract import UserTurnRecordRequest
from domain_api.kernel import DomainKernel
from perceptual_visibility_contract import METADATA_KEY
from perceptual_visibility_projection import assemble_perceptual_history_entry_for_viewer
from player_decomposition_fixtures import build_player_decomposition_for_content
from player_entitlement_authority import (
    ENTITLEMENT_AUTHORITY_SNAPSHOT_KEY,
    extract_entitlement_authority_snapshot,
    merge_entitlement_snapshot_into_metadata,
)
from player_perceptual_service import (
    attach_player_perceptual_metadata,
    validate_player_perceptual_decomposition,
)
from player_source_accounting import normalize_source_for_indexing


def _build_player_entry(
    *,
    content: str,
    session_cast: list[str],
    role_assignments: dict[str, str],
    scope: str = "public",
    characters: list[str] | None = None,
    roles: list[str] | None = None,
    kind: str = "observable_event",
) -> dict:
    decomposition = build_player_decomposition_for_content(
        content,
        kind=kind,
        scope=scope,
        characters=characters or [],
    )
    if roles is not None:
        decomposition["perceptual_visibility"]["units"][0]["recipients"]["roles"] = list(roles)
    record, audit = validate_player_perceptual_decomposition(
        content=content,
        speaker="Traveler",
        decomposition=decomposition,
    )
    assert audit["accepted"]
    metadata = attach_player_perceptual_metadata(
        {},
        record=record,
        validation_audit=audit,
        entitlement_authority_snapshot=merge_entitlement_snapshot_into_metadata(
            {},
            session_cast=session_cast,
            role_assignments=role_assignments,
        )[ENTITLEMENT_AUTHORITY_SNAPSHOT_KEY],
    )
    return {
        "entry_id": "issue-125-role-private",
        "content": content,
        "metadata": metadata,
    }


class Issue125RolePrivateProjectionTests(unittest.TestCase):
    def test_role_private_roles_only_entitles_role_holders(self) -> None:
        content = "Only the priest would recognize the blessing."
        entry = _build_player_entry(
            content=content,
            session_cast=["Celina", "Ayame", "Harley"],
            role_assignments={"Celina": "priest", "Ayame": "witness", "Harley": "guest"},
            scope="role_private",
            roles=["priest"],
        )
        present = ["Celina", "Ayame", "Harley"]

        celina = assemble_perceptual_history_entry_for_viewer(
            entry,
            viewer_character="Celina",
            present_characters=present,
            source_kind="player",
        )
        ayame = assemble_perceptual_history_entry_for_viewer(
            entry,
            viewer_character="Ayame",
            present_characters=present,
            source_kind="player",
        )

        self.assertIn("blessing", celina.content or "")
        self.assertIsNone(ayame.content)
        self.assertEqual(celina.exclusion_reasons, {})
        self.assertEqual(ayame.exclusion_reasons.get("u1"), "recipient_ineligible")

    def test_role_private_multiple_holders_same_role(self) -> None:
        content = "Staff-only operational detail."
        entry = _build_player_entry(
            content=content,
            session_cast=["Alice", "Bob", "Carol"],
            role_assignments={"Alice": "staff", "Bob": "staff", "Carol": "guest"},
            scope="role_private",
            roles=["staff"],
        )
        present = ["Alice", "Bob", "Carol"]

        alice = assemble_perceptual_history_entry_for_viewer(
            entry, viewer_character="Alice", present_characters=present, source_kind="player"
        )
        bob = assemble_perceptual_history_entry_for_viewer(
            entry, viewer_character="Bob", present_characters=present, source_kind="player"
        )
        carol = assemble_perceptual_history_entry_for_viewer(
            entry, viewer_character="Carol", present_characters=present, source_kind="player"
        )

        self.assertIn("operational", alice.content or "")
        self.assertIn("operational", bob.content or "")
        self.assertIsNone(carol.content)

    def test_role_private_unknown_role_fails_closed(self) -> None:
        content = "Unknown role recipient."
        entry = _build_player_entry(
            content=content,
            session_cast=["Alice", "Bob"],
            role_assignments={"Alice": "staff"},
            scope="role_private",
            roles=["archivist"],
        )
        alice = assemble_perceptual_history_entry_for_viewer(
            entry,
            viewer_character="Alice",
            present_characters=["Alice", "Bob"],
            source_kind="player",
        )
        self.assertIsNone(alice.content)

    def test_role_private_mixed_characters_and_roles(self) -> None:
        content = "Mixed recipient content."
        entry = _build_player_entry(
            content=content,
            session_cast=["Alice", "Bob", "Carol"],
            role_assignments={"Alice": "staff", "Bob": "guest", "Carol": "staff"},
            scope="role_private",
            characters=["Bob"],
            roles=["staff"],
        )
        present = ["Alice", "Bob", "Carol"]

        alice = assemble_perceptual_history_entry_for_viewer(
            entry, viewer_character="Alice", present_characters=present, source_kind="player"
        )
        bob = assemble_perceptual_history_entry_for_viewer(
            entry, viewer_character="Bob", present_characters=present, source_kind="player"
        )
        carol = assemble_perceptual_history_entry_for_viewer(
            entry, viewer_character="Carol", present_characters=present, source_kind="player"
        )

        self.assertIn("Mixed", alice.content or "")
        self.assertIn("Mixed", bob.content or "")
        self.assertIn("Mixed", carol.content or "")

    def test_role_private_characters_only_without_roles(self) -> None:
        content = "Explicit private line."
        entry = _build_player_entry(
            content=content,
            session_cast=["Alice", "Bob"],
            role_assignments={"Alice": "staff", "Bob": "guest"},
            scope="role_private",
            characters=["Alice"],
            roles=[],
        )
        bob = assemble_perceptual_history_entry_for_viewer(
            entry,
            viewer_character="Bob",
            present_characters=["Alice", "Bob"],
            source_kind="player",
        )
        alice = assemble_perceptual_history_entry_for_viewer(
            entry,
            viewer_character="Alice",
            present_characters=["Alice", "Bob"],
            source_kind="player",
        )
        self.assertIn("Explicit", alice.content or "")
        self.assertIsNone(bob.content)

    def test_role_private_speech_uses_same_resolution_primitive(self) -> None:
        content = '"Staff channel only."'
        entry = _build_player_entry(
            content=content,
            session_cast=["Alice", "Bob"],
            role_assignments={"Alice": "staff", "Bob": "guest"},
            scope="role_private",
            roles=["staff"],
            kind="speech",
        )
        alice = assemble_perceptual_history_entry_for_viewer(
            entry,
            viewer_character="Alice",
            present_characters=["Alice", "Bob"],
            source_kind="player",
        )
        bob = assemble_perceptual_history_entry_for_viewer(
            entry,
            viewer_character="Bob",
            present_characters=["Alice", "Bob"],
            source_kind="player",
        )
        self.assertIn("Staff channel", alice.content or "")
        self.assertIsNone(bob.content)
        self.assertNotIn("u1", bob.authority_narrowed_unit_ids)

    def test_temporal_stability_uses_commit_time_snapshot(self) -> None:
        content = "Role-bound secret."
        snapshot_roles = {"Celina": "staff", "Ayame": "witness"}
        entry = _build_player_entry(
            content=content,
            session_cast=["Celina", "Ayame"],
            role_assignments=snapshot_roles,
            scope="role_private",
            roles=["staff"],
        )
        present = ["Celina", "Ayame"]

        celina_before = assemble_perceptual_history_entry_for_viewer(
            entry, viewer_character="Celina", present_characters=present, source_kind="player"
        )
        ayame_before = assemble_perceptual_history_entry_for_viewer(
            entry, viewer_character="Ayame", present_characters=present, source_kind="player"
        )
        self.assertIn("secret", celina_before.content or "")
        self.assertIsNone(ayame_before.content)

        # Later scene_state reassignment must not affect historical projection.
        kernel = DomainKernel.for_fixture_store()
        created = kernel.create_session(cast=["Celina", "Ayame"])
        fixture = kernel.store.require(created.hg_scene_id)
        assert fixture.manager.scene_state is not None
        fixture.manager.scene_state.role_assignments = {
            "Ayame": "staff",
            "Celina": "witness",
        }

        celina_after = assemble_perceptual_history_entry_for_viewer(
            entry,
            viewer_character="Celina",
            present_characters=present,
            source_kind="player",
        )
        ayame_after = assemble_perceptual_history_entry_for_viewer(
            entry,
            viewer_character="Ayame",
            present_characters=present,
            source_kind="player",
        )
        self.assertEqual(celina_before.included_unit_ids, celina_after.included_unit_ids)
        self.assertEqual(ayame_before.excluded_unit_ids, ayame_after.excluded_unit_ids)

    def test_missing_snapshot_rejects_player_projection(self) -> None:
        content = "Hello everyone."
        decomposition = build_player_decomposition_for_content(content)
        record, audit = validate_player_perceptual_decomposition(
            content=content,
            speaker="Traveler",
            decomposition=decomposition,
        )
        self.assertTrue(audit["accepted"])
        entry = {
            "entry_id": "missing-snapshot",
            "content": content,
            "metadata": {METADATA_KEY: record.to_dict()},
        }
        assembly = assemble_perceptual_history_entry_for_viewer(
            entry,
            viewer_character="Alice",
            present_characters=["Alice"],
            source_kind="player",
        )
        self.assertIsNone(assembly.content)
        self.assertEqual(assembly.degraded_path, "missing_entitlement_authority_snapshot")

    def test_record_user_turn_attaches_required_snapshot(self) -> None:
        content = "Traveler checks the room."
        decomposition = build_player_decomposition_for_content(content)
        kernel = DomainKernel.for_fixture_store()
        created = kernel.create_session(cast=["Alice", "Bob"])
        fixture = kernel.store.require(created.hg_scene_id)
        assert fixture.manager.scene_state is not None
        fixture.manager.scene_state.role_assignments = {"Alice": "host", "Bob": "guest"}

        entry = kernel.record_user_turn(
            UserTurnRecordRequest.from_content(
                hg_session_id=created.hg_scene_id,
                content=content,
                speaker="Traveler",
                player_decomposition=decomposition,
            )
        )
        metadata = entry.get("metadata") if isinstance(entry.get("metadata"), dict) else {}
        snapshot = extract_entitlement_authority_snapshot(metadata)
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot["session_cast"], ["Alice", "Bob"])
        self.assertEqual(snapshot["role_assignments"], {"Alice": "host", "Bob": "guest"})

    def test_role_identifier_matching_is_exact_after_strip(self) -> None:
        content = "Case-sensitive role gate."
        entry = _build_player_entry(
            content=content,
            session_cast=["Alice"],
            role_assignments={"Alice": "Staff"},
            scope="role_private",
            roles=["staff"],
        )
        alice = assemble_perceptual_history_entry_for_viewer(
            entry,
            viewer_character="Alice",
            present_characters=["Alice"],
            source_kind="player",
        )
        self.assertIsNone(alice.content)


if __name__ == "__main__":
    unittest.main()
