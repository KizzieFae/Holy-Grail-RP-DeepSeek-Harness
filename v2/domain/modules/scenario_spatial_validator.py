"""Deterministic presentation spatial-claim validation (#201 G3-A).

Validates structured spatial claims against authoritative zone assignments.
Does not scrape arbitrary prose.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

SPATIAL_CLAIMS_SCHEMA = "hg_presentation_spatial_claims_v1"
RELATION_LOCATED_AT = "located_at"
RELATION_CO_LOCATED_WITH = "co_located_with"

ValidationClass = Literal["accepted", "contradiction", "unknown", "malformed"]


@dataclass
class SpatialClaimFinding:
    claim_index: int
    entity_id: str
    finding_class: ValidationClass
    reason: str
    authoritative_zone: str | None = None
    claimed_zone: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_index": self.claim_index,
            "entity_id": self.entity_id,
            "finding_class": self.finding_class,
            "reason": self.reason,
            "authoritative_zone": self.authoritative_zone,
            "claimed_zone": self.claimed_zone,
        }


@dataclass
class SpatialValidationResult:
    accepted: bool
    validation_class: ValidationClass
    reason: str
    findings: list[SpatialClaimFinding] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "validation_class": self.validation_class,
            "reason": self.reason,
            "findings": [item.to_dict() for item in self.findings],
        }


def _normalize_entity_key(value: str) -> str:
    return str(value or "").strip().lower()


def _resolve_entity_zone(
    entity_id: str,
    *,
    character_zones: dict[str, str],
    role_zones: dict[str, str],
    entity_role_map: dict[str, str],
) -> tuple[str | None, str]:
    """Return (zone, resolution_basis)."""
    raw = str(entity_id or "").strip()
    if not raw:
        return None, "empty_entity"

    norm = _normalize_entity_key(raw)
    for char_id, zone in character_zones.items():
        if _normalize_entity_key(char_id) == norm:
            return zone, "character_id"
    for role_name, zone in role_zones.items():
        if _normalize_entity_key(role_name) == norm:
            return zone, "role_name"
    for char_id, role_name in entity_role_map.items():
        if _normalize_entity_key(char_id) == norm or _normalize_entity_key(role_name) == norm:
            zone = character_zones.get(char_id)
            if zone:
                return zone, "entity_role_map"
            role_zone = role_zones.get(role_name)
            if role_zone:
                return role_zone, "entity_role_map_role"
    return None, "unknown_entity"


def parse_spatial_claims_manifest(manifest: dict[str, Any] | None) -> tuple[list[dict[str, Any]] | None, str | None]:
    if manifest is None:
        return [], None
    if not isinstance(manifest, dict):
        return None, "spatial_claims_not_object"
    schema = str(manifest.get("schema") or "").strip()
    if schema and schema != SPATIAL_CLAIMS_SCHEMA:
        return None, f"unsupported_schema:{schema}"
    claims = manifest.get("claims")
    if claims is None:
        return [], None
    if not isinstance(claims, list):
        return None, "claims_not_array"
    return claims, None


def validate_presentation_spatial_claims(
    *,
    spatial_claims: dict[str, Any] | None,
    authoritative_character_zones: dict[str, str] | None,
    authoritative_role_zones: dict[str, str] | None = None,
    entity_role_map: dict[str, str] | None = None,
) -> SpatialValidationResult:
    """Validate structured spatial claims against authoritative zone facts."""
    character_zones = {
        str(k).strip(): str(v).strip()
        for k, v in (authoritative_character_zones or {}).items()
        if str(k).strip() and str(v).strip()
    }
    role_zones = {
        str(k).strip(): str(v).strip()
        for k, v in (authoritative_role_zones or {}).items()
        if str(k).strip() and str(v).strip()
    }
    roles = {
        str(k).strip(): str(v).strip()
        for k, v in (entity_role_map or {}).items()
        if str(k).strip() and str(v).strip()
    }

    claims, parse_error = parse_spatial_claims_manifest(spatial_claims)
    if parse_error:
        return SpatialValidationResult(
            accepted=False,
            validation_class="malformed",
            reason=parse_error,
        )
    if not claims:
        return SpatialValidationResult(
            accepted=True,
            validation_class="accepted",
            reason="no_spatial_claims_to_validate",
        )

    findings: list[SpatialClaimFinding] = []
    for index, claim in enumerate(claims):
        if not isinstance(claim, dict):
            findings.append(SpatialClaimFinding(
                claim_index=index,
                entity_id="",
                finding_class="malformed",
                reason="claim_not_object",
            ))
            continue

        entity_id = str(claim.get("entity_id") or "").strip()
        relation = str(claim.get("relation") or RELATION_LOCATED_AT).strip().lower()
        claimed_zone = str(claim.get("zone_id") or "").strip() or None

        if relation == RELATION_CO_LOCATED_WITH:
            target_entity = str(claim.get("target_entity_id") or "").strip()
            if not entity_id or not target_entity:
                findings.append(SpatialClaimFinding(
                    claim_index=index,
                    entity_id=entity_id or target_entity,
                    finding_class="malformed",
                    reason="co_located_with_requires_two_entities",
                ))
                continue
            zone_a, basis_a = _resolve_entity_zone(
                entity_id,
                character_zones=character_zones,
                role_zones=role_zones,
                entity_role_map=roles,
            )
            zone_b, basis_b = _resolve_entity_zone(
                target_entity,
                character_zones=character_zones,
                role_zones=role_zones,
                entity_role_map=roles,
            )
            if zone_a is None or basis_a == "unknown_entity":
                findings.append(SpatialClaimFinding(
                    claim_index=index,
                    entity_id=entity_id,
                    finding_class="unknown",
                    reason="entity_not_in_authoritative_state",
                ))
                continue
            if zone_b is None or basis_b == "unknown_entity":
                findings.append(SpatialClaimFinding(
                    claim_index=index,
                    entity_id=target_entity,
                    finding_class="unknown",
                    reason="target_entity_not_in_authoritative_state",
                ))
                continue
            if zone_a != zone_b:
                findings.append(SpatialClaimFinding(
                    claim_index=index,
                    entity_id=entity_id,
                    finding_class="contradiction",
                    reason="entities_not_co_located_in_authoritative_state",
                    authoritative_zone=zone_a,
                    claimed_zone=zone_b,
                ))
            continue

        if not entity_id:
            findings.append(SpatialClaimFinding(
                claim_index=index,
                entity_id="",
                finding_class="malformed",
                reason="missing_entity_id",
            ))
            continue
        if not claimed_zone:
            findings.append(SpatialClaimFinding(
                claim_index=index,
                entity_id=entity_id,
                finding_class="malformed",
                reason="located_at_requires_zone_id",
            ))
            continue

        authoritative_zone, basis = _resolve_entity_zone(
            entity_id,
            character_zones=character_zones,
            role_zones=role_zones,
            entity_role_map=roles,
        )
        if authoritative_zone is None:
            finding_class: ValidationClass = (
                "unknown" if basis == "unknown_entity" else "malformed"
            )
            findings.append(SpatialClaimFinding(
                claim_index=index,
                entity_id=entity_id,
                finding_class=finding_class,
                reason="entity_not_in_authoritative_state",
            ))
            continue
        if authoritative_zone != claimed_zone:
            findings.append(SpatialClaimFinding(
                claim_index=index,
                entity_id=entity_id,
                finding_class="contradiction",
                reason="claimed_zone_contradicts_authoritative_zone",
                authoritative_zone=authoritative_zone,
                claimed_zone=claimed_zone,
            ))

    contradictions = [f for f in findings if f.finding_class == "contradiction"]
    malformed = [f for f in findings if f.finding_class == "malformed"]
    if contradictions:
        return SpatialValidationResult(
            accepted=False,
            validation_class="contradiction",
            reason="spatial_claim_contradicts_authoritative_state",
            findings=findings,
        )
    if malformed:
        return SpatialValidationResult(
            accepted=False,
            validation_class="malformed",
            reason="malformed_spatial_claims",
            findings=findings,
        )
    return SpatialValidationResult(
        accepted=True,
        validation_class="accepted",
        reason="spatial_claims_consistent_or_unknown",
        findings=findings,
    )
