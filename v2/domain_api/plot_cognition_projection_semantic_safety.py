"""Layer B semantic epistemic-leakage evaluator contract (#62).

Evaluates whether Character-facing advisory text communicates information outside the
Character's permitted epistemic envelope. Does not establish truth, knowledge, facts,
forbidden basis, or author replacement prose.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

from .plot_cognition_projection_contract import (
    BasisExposureResult,
    SemanticEvaluationResult,
    SemanticVerdictKind,
)

LEAK_MARKER_PATTERN = re.compile(r"\[\[LEAK:([^\]]+)\]\]", re.IGNORECASE)
WITHHOLD_MARKER = "[[WITHHOLD]]"
REWRITE_MARKER = "[[REWRITE]]"
UNAVAILABLE_MARKER = "[[EVALUATOR_UNAVAILABLE]]"


class CharacterEpistemicLeakageEvaluator(Protocol):
    def evaluate(
        self,
        *,
        character_id: str,
        candidate_text: str,
        basis_exposure: BasisExposureResult | None,
        known_by_snapshot_id: str,
    ) -> SemanticEvaluationResult:
        """Return a Layer B verdict for proposed Character-facing advisory text."""


@dataclass(frozen=True)
class DeterministicRuleBasedEpistemicEvaluator:
    """Test-oriented deterministic evaluator; production inference belongs to #63."""

    unavailable: bool = False

    def evaluate(
        self,
        *,
        character_id: str,
        candidate_text: str,
        basis_exposure: BasisExposureResult | None,
        known_by_snapshot_id: str,
    ) -> SemanticEvaluationResult:
        del known_by_snapshot_id  # contract surface for #63 evaluators
        if self.unavailable:
            return SemanticEvaluationResult(
                verdict="evaluator_unavailable",
                rationale="semantic evaluator unavailable",
            )
        text = candidate_text or ""
        if UNAVAILABLE_MARKER in text:
            return SemanticEvaluationResult(
                verdict="evaluator_unavailable",
                rationale="candidate requested evaluator unavailable simulation",
            )
        if WITHHOLD_MARKER in text:
            return SemanticEvaluationResult(
                verdict="withhold",
                rationale="deterministic withhold marker detected",
            )
        if REWRITE_MARKER in text:
            return SemanticEvaluationResult(
                verdict="rewrite_required",
                rationale="deterministic rewrite marker detected",
            )
        leaks = tuple(match.group(1).strip() for match in LEAK_MARKER_PATTERN.finditer(text))
        if leaks:
            return SemanticEvaluationResult(
                verdict="withhold",
                rationale="hidden salience or out-of-envelope information detected",
                leak_indicators=leaks,
            )
        lowered = text.lower()
        hidden_salience_markers = (
            "bob secretly",
            "hidden vault",
            "third-party private",
            "charlie's secret",
        )
        for marker in hidden_salience_markers:
            if marker in lowered:
                return SemanticEvaluationResult(
                    verdict="withhold",
                    rationale=f"prospective text leaks hidden salience: {marker}",
                    leak_indicators=(marker,),
                )
        if basis_exposure and basis_exposure.withheld_facet_ids:
            for facet in basis_exposure.withheld_facet_ids:
                stable = facet.split(":", 1)[-1].lower()
                token = facet.replace(":", " ").lower()
                if (stable and stable in lowered) or (token and token in lowered):
                    return SemanticEvaluationResult(
                        verdict="withhold",
                        rationale=f"text exposes withheld basis facet {facet}",
                        leak_indicators=(facet,),
                    )
        return SemanticEvaluationResult(
            verdict="pass",
            rationale="no epistemic leakage detected",
        )


def default_semantic_evaluator() -> CharacterEpistemicLeakageEvaluator:
    return DeterministicRuleBasedEpistemicEvaluator()
