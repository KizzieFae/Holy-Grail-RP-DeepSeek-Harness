"""Issue #201 G3-A — spatial validator kernel integration with Arkham template."""

import unittest

from domain_api.contract import PresentationSpatialClaimsValidationRequest
from domain_api.kernel import DomainKernel
from domain_api.session_repository import SessionRepository


class Issue201G3aSpatialKernelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = SessionRepository()
        self.kernel = DomainKernel.for_repository(self.repo)

    def test_arkham_template_authoritative_zones_detect_sample_e_class(self) -> None:
        session = self.kernel.create_session(
            characters=["harley_quinn", "poison_ivy", "magpie"],
            scene_template_id="arkham_asylum_mess_hall_arena",
            role_assignments={
                "harley_quinn": "instigator",
                "poison_ivy": "instigator_accomplice",
                "magpie": "new_arrival",
            },
        )
        hg_scene_id = session.hg_session_id

        valid = self.kernel.validate_presentation_spatial_claims(
            PresentationSpatialClaimsValidationRequest(
                hg_scene_id=hg_scene_id,
                spatial_claims={
                    "schema": "hg_presentation_spatial_claims_v1",
                    "claims": [
                        {
                            "entity_id": "magpie",
                            "relation": "located_at",
                            "zone_id": "across_room",
                        },
                    ],
                },
            )
        )
        self.assertTrue(valid.accepted)

        contradiction = self.kernel.validate_presentation_spatial_claims(
            PresentationSpatialClaimsValidationRequest(
                hg_scene_id=hg_scene_id,
                spatial_claims={
                    "schema": "hg_presentation_spatial_claims_v1",
                    "claims": [
                        {
                            "entity_id": "magpie",
                            "relation": "located_at",
                            "zone_id": "harley_ivy_table",
                        },
                    ],
                },
            )
        )
        self.assertFalse(contradiction.accepted)
        self.assertEqual(contradiction.validation_class, "contradiction")


if __name__ == "__main__":
    unittest.main()
