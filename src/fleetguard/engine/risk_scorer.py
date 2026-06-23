"""Risk scorer orchestrator: aggregates all registered rules."""

import asyncio
from fleetguard.engine.base import RiskContext, RiskVerdict, RiskRule


class RiskScorer:
    """Runs all registered rules and aggregates scores."""

    def __init__(self, rules: list[RiskRule]):
        self.rules = rules

    async def score(self, ctx: RiskContext) -> tuple[int, list[str], list[str], str]:
        """
        Evaluate all rules and aggregate results.

        Returns:
            (total_score, all_labels, all_reasons, severity)
            severity: "low" (0-29), "medium" (30-59), "high" (60-79), "critical" (80-100)
        """
        total = 0
        all_labels: list[str] = []
        all_reasons: list[str] = []

        # Run all rules concurrently
        verdicts = await asyncio.gather(
            *(rule.evaluate(ctx) for rule in self.rules),
            return_exceptions=True,
        )

        for verdict in verdicts:
            if isinstance(verdict, Exception):
                continue
            total += verdict.score
            all_labels.extend(verdict.labels)
            all_reasons.extend(verdict.reasons)

        # Cap at 100, deduplicate labels
        total = min(total, 100)
        all_labels = list(dict.fromkeys(all_labels))
        all_reasons = list(dict.fromkeys(all_reasons))

        # Severity band
        if total >= 80:
            severity = "critical"
        elif total >= 60:
            severity = "high"
        elif total >= 30:
            severity = "medium"
        else:
            severity = "low"

        return total, all_labels, all_reasons, severity


# Default scorer instance with all rules registered
_default_scorer: RiskScorer | None = None


def get_risk_scorer() -> RiskScorer:
    global _default_scorer
    if _default_scorer is None:
        from fleetguard.engine.rules import get_all_rules
        _default_scorer = RiskScorer(get_all_rules())
    return _default_scorer
