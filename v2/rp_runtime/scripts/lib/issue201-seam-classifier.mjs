/**
 * Issue #201 LH-0 — seam failure classification.
 */
import { SEAM_FAILURE_CLASSES } from './issue201-lifecycle-states.mjs';

/**
 * Classify which seam failed given observed lifecycle evidence.
 * Returns null when no seam failure is indicated (narrative-quality path).
 */
export function classifySeamFailure({
  generated = false,
  persisted = false,
  retrieved = null,
  entitlementBlocked = false,
  entitlementLeak = false,
  projected = false,
  consumerReceived = false,
  consumerUsed = false,
  decisionInfluenced = false,
  observableConsequence = false,
  requiredAnchorIds = [],
  projectedAnchorIds = [],
  k6PairRequired = false,
}) {
  if (!generated) {
    return {
      seam: SEAM_FAILURE_CLASSES.PRODUCER_COGNITION,
      detail: 'persistent cognition did not produce required obligation output',
    };
  }
  if (!persisted) {
    return {
      seam: SEAM_FAILURE_CLASSES.PERSISTENCE,
      detail: 'output generated but not durably retained',
    };
  }
  if (retrieved === false) {
    return {
      seam: SEAM_FAILURE_CLASSES.RETRIEVAL,
      detail: 'persisted information not found when relevant',
    };
  }
  if (entitlementBlocked || entitlementLeak) {
    return {
      seam: SEAM_FAILURE_CLASSES.ENTITLEMENT,
      detail: entitlementLeak
        ? 'information reached unauthorized consumer'
        : 'entitlement incorrectly blocked authorized consumer',
    };
  }
  if (k6PairRequired && requiredAnchorIds.length > 1) {
    const missing = requiredAnchorIds.filter((id) => !projectedAnchorIds.includes(id));
    if (missing.length > 0 && projected) {
      return {
        seam: SEAM_FAILURE_CLASSES.K6_MULTI_ANCHOR,
        detail: `bounded projection omitted required anchor(s): ${missing.join(', ')}`,
        missing_anchor_ids: missing,
      };
    }
  }
  if (!projected) {
    return {
      seam: SEAM_FAILURE_CLASSES.PROJECTION,
      detail: 'authorized information existed but was omitted from consumer package',
    };
  }
  if (!consumerReceived) {
    return {
      seam: SEAM_FAILURE_CLASSES.CONSUMPTION,
      detail: 'projection did not reach authorized consumer receipt',
    };
  }
  if (!consumerUsed) {
    return {
      seam: SEAM_FAILURE_CLASSES.CONSUMPTION,
      detail: 'consumer received but did not reference/use projected content',
    };
  }
  if (!decisionInfluenced) {
    return {
      seam: SEAM_FAILURE_CLASSES.DECISION_INFLUENCE,
      detail: 'consumer used content but decision was not materially affected',
    };
  }
  if (!observableConsequence) {
    return {
      seam: SEAM_FAILURE_CLASSES.NARRATIVE_CONSEQUENCE,
      detail: 'decision changed but intended observable consequence did not materialize',
    };
  }
  return null;
}

export function detectK6ClassCondition({
  requiredAnchorIds = [],
  eligibleAnchorIds = [],
  projectedAnchorIds = [],
  projectionBudget = null,
}) {
  const allEligiblePresent = requiredAnchorIds.every((id) => eligibleAnchorIds.includes(id));
  const projectedSet = new Set(projectedAnchorIds);
  const missingFromProjection = requiredAnchorIds.filter((id) => !projectedSet.has(id));
  const k6Suspected = (
    requiredAnchorIds.length > 1
    && allEligiblePresent
    && missingFromProjection.length > 0
  );
  return {
    k6_class_suspected: k6Suspected,
    required_anchor_ids: requiredAnchorIds,
    eligible_anchor_ids: eligibleAnchorIds,
    projected_anchor_ids: projectedAnchorIds,
    missing_from_projection: missingFromProjection,
    projection_budget: projectionBudget,
    independently_reportable: true,
  };
}
