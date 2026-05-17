import logging
from dataclasses import dataclass, field
from app.models.decision import (
    Decision, ClassificationResult,
    ImpactLevel, Reversibility, RouteDecision
)
from app.models.rule import Rule
from app.services.rules_service import RulesService

logger = logging.getLogger(__name__)

ROUTE_MATRIX = {
    (Reversibility.REVERSIBLE,   ImpactLevel.LOW):      RouteDecision.AUTO_APPROVE,
    (Reversibility.REVERSIBLE,   ImpactLevel.MEDIUM):   RouteDecision.AUTO_APPROVE,
    (Reversibility.REVERSIBLE,   ImpactLevel.HIGH):     RouteDecision.NEEDS_APPROVAL,
    (Reversibility.REVERSIBLE,   ImpactLevel.CRITICAL): RouteDecision.NEEDS_APPROVAL,
    (Reversibility.IRREVERSIBLE, ImpactLevel.LOW):      RouteDecision.NEEDS_APPROVAL,
    (Reversibility.IRREVERSIBLE, ImpactLevel.MEDIUM):   RouteDecision.NEEDS_APPROVAL,
    (Reversibility.IRREVERSIBLE, ImpactLevel.HIGH):     RouteDecision.NEEDS_APPROVAL,
    (Reversibility.IRREVERSIBLE, ImpactLevel.CRITICAL): RouteDecision.HARD_BLOCK,
    (Reversibility.UNKNOWN,      ImpactLevel.LOW):      RouteDecision.NEEDS_APPROVAL,
    (Reversibility.UNKNOWN,      ImpactLevel.MEDIUM):   RouteDecision.NEEDS_APPROVAL,
    (Reversibility.UNKNOWN,      ImpactLevel.HIGH):     RouteDecision.NEEDS_APPROVAL,
    (Reversibility.UNKNOWN,      ImpactLevel.CRITICAL): RouteDecision.HARD_BLOCK,
}

IMPACT_ORDER = {
    ImpactLevel.LOW: 1,
    ImpactLevel.MEDIUM: 2,
    ImpactLevel.HIGH: 3,
    ImpactLevel.CRITICAL: 4
}


@dataclass
class RulesEngineResult:
    rules_fired: list[str] = field(default_factory=list)
    overrides_applied: list[str] = field(default_factory=list)
    final_classification: ClassificationResult = None


class RulesEngine:

    def apply(
        self,
        decision: Decision,
        classification: ClassificationResult
    ) -> RulesEngineResult:
        """
        Load active rules from Cosmos and apply them to the decision.
        Rules escalate only — never downgrade impact.
        """
        rules_service = RulesService()
        active_rules = rules_service.list_rules(enabled_only=True)

        rules_fired = []
        overrides_applied = []
        impact = classification.impact
        reversibility = classification.reversibility
        route_override = None
        extra_approvers = []
        extra_reasons = []

        for rule in active_rules:
            if not self._matches(rule, decision):
                continue

            logger.info(f"Rule fired: '{rule.name}' for {decision.decision_id}")
            rules_fired.append(rule.name)
            ov = rule.override

            # escalate impact only — never downgrade
            if ov.impact:
                new_impact = ImpactLevel(ov.impact)
                if IMPACT_ORDER[new_impact] > IMPACT_ORDER[impact]:
                    overrides_applied.append(
                        f"impact: {impact.value} → {new_impact.value} (rule: {rule.name})"
                    )
                    impact = new_impact

            # override reversibility — only toward irreversible
            if ov.reversibility:
                new_rev = Reversibility(ov.reversibility)
                if new_rev == Reversibility.IRREVERSIBLE:
                    overrides_applied.append(
                        f"reversibility: {reversibility.value} → irreversible (rule: {rule.name})"
                    )
                    reversibility = new_rev

            # force route — only hard_block allowed
            if ov.force_route == "hard_block":
                route_override = RouteDecision.HARD_BLOCK
                overrides_applied.append(f"route: hard_block (rule: {rule.name})")

            if ov.add_approvers:
                extra_approvers.extend(ov.add_approvers)

            if ov.reason:
                extra_reasons.append(ov.reason)

            # track usage asynchronously — don't block on failure
            try:
                rules_service.increment_fired_count(rule.rule_id)
            except Exception:
                pass

        # derive final route
        final_route = route_override or ROUTE_MATRIX.get(
            (reversibility, impact), RouteDecision.NEEDS_APPROVAL
        )

        all_approvers = list(dict.fromkeys(
            classification.suggested_approvers + extra_approvers
        ))

        base_reason = classification.risk_reason
        if extra_reasons:
            base_reason += " | " + " | ".join(extra_reasons)

        final_classification = ClassificationResult(
            reversibility=reversibility,
            impact=impact,
            risk_reason=base_reason,
            suggested_approvers=all_approvers,
            confidence=classification.confidence,
            route=final_route
        )

        return RulesEngineResult(
            rules_fired=rules_fired,
            overrides_applied=overrides_applied,
            final_classification=final_classification
        )

    def _matches(self, rule: Rule, decision: Decision) -> bool:
        """
        Check if a rule's conditions match the decision.
        All specified conditions must match (AND logic).
        """
        c = rule.condition

        try:
            # action_type check
            if c.action_types:
                if decision.action_type not in c.action_types:
                    return False

            # payload field numeric comparison
            if c.payload_field and c.operator and c.value is not None:
                payload_val = decision.payload.get(c.payload_field)
                if payload_val is None:
                    return False
                if not self._compare(float(payload_val), c.operator, float(c.value)):
                    return False

            # description keyword
            if c.description_contains:
                if c.description_contains.lower() not in decision.description.lower():
                    return False

            # context keyword
            if c.context_contains:
                if c.context_contains.lower() not in (decision.context or "").lower():
                    return False

            # payload field equality
            if c.payload_equals:
                for field_name, expected in c.payload_equals.items():
                    if str(decision.payload.get(field_name, "")) != str(expected):
                        return False

        except Exception as e:
            logger.warning(f"Rule '{rule.name}' condition error: {e}")
            return False

        return True

    def _compare(self, actual: float, operator: str, threshold: float) -> bool:
        ops = {
            "gt":  actual > threshold,
            "gte": actual >= threshold,
            "lt":  actual < threshold,
            "lte": actual <= threshold,
            "eq":  actual == threshold,
        }
        return ops.get(operator, False)