"""Tests for scenario_spatial_validator (#201 G3-A)."""

import unittest

from domain.modules.scenario_spatial_validator import (
    RELATION_CO_LOCATED_WITH,
    RELATION_LOCATED_AT,
    SPATIAL_CLAIMS_SCHEMA,
    validate_presentation_spatial_claims,
)


class ScenarioSpatialValidatorTests(unittest.TestCase):
    def test_valid_same_location(self) -> None:
        result = validate_presentation_spatial_claims(
            spatial_claims={
                "schema": SPATIAL_CLAIMS_SCHEMA,
                "claims": [
                    {
                        "entity_id": "harley_quinn",
                        "relation": RELATION_LOCATED_AT,
                        "zone_id": "harley_ivy_table",
                    },
                ],
            },
            authoritative_character_zones={
                "harley_quinn": "harley_ivy_table",
                "poison_ivy": "harley_ivy_table",
                "magpie": "across_room",
            },
            entity_role_map={
                "harley_quinn": "instigator",
                "poison_ivy": "instigator_accomplice",
                "magpie": "new_arrival",
            },
        )
        self.assertTrue(result.accepted)
        self.assertEqual(result.validation_class, "accepted")

    def test_contradictory_entity_location_sample_e_class(self) -> None:
        result = validate_presentation_spatial_claims(
            spatial_claims={
                "schema": SPATIAL_CLAIMS_SCHEMA,
                "claims": [
                    {
                        "entity_id": "magpie",
                        "relation": RELATION_LOCATED_AT,
                        "zone_id": "harley_ivy_table",
                    },
                ],
            },
            authoritative_character_zones={
                "harley_quinn": "harley_ivy_table",
                "poison_ivy": "harley_ivy_table",
                "magpie": "across_room",
            },
            entity_role_map={"magpie": "new_arrival"},
        )
        self.assertFalse(result.accepted)
        self.assertEqual(result.validation_class, "contradiction")
        self.assertEqual(result.findings[0].authoritative_zone, "across_room")
        self.assertEqual(result.findings[0].claimed_zone, "harley_ivy_table")

    def test_unknown_entity_not_contradiction(self) -> None:
        result = validate_presentation_spatial_claims(
            spatial_claims={
                "schema": SPATIAL_CLAIMS_SCHEMA,
                "claims": [
                    {
                        "entity_id": "unknown_npc",
                        "relation": RELATION_LOCATED_AT,
                        "zone_id": "harley_ivy_table",
                    },
                ],
            },
            authoritative_character_zones={"magpie": "across_room"},
        )
        self.assertTrue(result.accepted)
        self.assertEqual(result.findings[0].finding_class, "unknown")

    def test_co_located_with_valid(self) -> None:
        result = validate_presentation_spatial_claims(
            spatial_claims={
                "schema": SPATIAL_CLAIMS_SCHEMA,
                "claims": [
                    {
                        "entity_id": "harley_quinn",
                        "relation": RELATION_CO_LOCATED_WITH,
                        "target_entity_id": "poison_ivy",
                    },
                ],
            },
            authoritative_character_zones={
                "harley_quinn": "harley_ivy_table",
                "poison_ivy": "harley_ivy_table",
            },
        )
        self.assertTrue(result.accepted)

    def test_co_located_with_contradiction(self) -> None:
        result = validate_presentation_spatial_claims(
            spatial_claims={
                "schema": SPATIAL_CLAIMS_SCHEMA,
                "claims": [
                    {
                        "entity_id": "magpie",
                        "relation": RELATION_CO_LOCATED_WITH,
                        "target_entity_id": "harley_quinn",
                    },
                ],
            },
            authoritative_character_zones={
                "harley_quinn": "harley_ivy_table",
                "magpie": "across_room",
            },
        )
        self.assertFalse(result.accepted)
        self.assertEqual(result.validation_class, "contradiction")

    def test_multiple_entities_mixed(self) -> None:
        result = validate_presentation_spatial_claims(
            spatial_claims={
                "schema": SPATIAL_CLAIMS_SCHEMA,
                "claims": [
                    {
                        "entity_id": "harley_quinn",
                        "relation": RELATION_LOCATED_AT,
                        "zone_id": "harley_ivy_table",
                    },
                    {
                        "entity_id": "magpie",
                        "relation": RELATION_LOCATED_AT,
                        "zone_id": "across_room",
                    },
                ],
            },
            authoritative_character_zones={
                "harley_quinn": "harley_ivy_table",
                "magpie": "across_room",
            },
        )
        self.assertTrue(result.accepted)

    def test_empty_claims_passes(self) -> None:
        result = validate_presentation_spatial_claims(
            spatial_claims={"schema": SPATIAL_CLAIMS_SCHEMA, "claims": []},
            authoritative_character_zones={"magpie": "across_room"},
        )
        self.assertTrue(result.accepted)

    def test_malformed_claims(self) -> None:
        result = validate_presentation_spatial_claims(
            spatial_claims={"schema": SPATIAL_CLAIMS_SCHEMA, "claims": "not-a-list"},
            authoritative_character_zones={},
        )
        self.assertFalse(result.accepted)
        self.assertEqual(result.validation_class, "malformed")

    def test_role_name_resolution(self) -> None:
        result = validate_presentation_spatial_claims(
            spatial_claims={
                "schema": SPATIAL_CLAIMS_SCHEMA,
                "claims": [
                    {
                        "entity_id": "new_arrival",
                        "relation": RELATION_LOCATED_AT,
                        "zone_id": "across_room",
                    },
                ],
            },
            authoritative_character_zones={"magpie": "across_room"},
            authoritative_role_zones={"new_arrival": "across_room"},
            entity_role_map={"magpie": "new_arrival"},
        )
        self.assertTrue(result.accepted)


if __name__ == "__main__":
    unittest.main()
