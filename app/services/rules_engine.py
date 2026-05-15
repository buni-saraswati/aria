import logging
from dataclasses import dataclass, field
from typing import Callable
from app.models.decision import (
    Decision, ClassificationResult,
    ImpactLevel, Reversibility, RouteDecision
)

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


# ─────────────────────────────────────────
# Rule definition
# ─────────────────────────────────────────

@dataclass
class RuleOverride:
    """What a rule changes when it fires."""
    impact: ImpactLevel = None
    reversibility: Reversibility = None
    route: RouteDecision = None           # if set, bypasses the route matrix
    add_approvers: list[str] = field(default_factory=list)
    reason: str = ""                      # appended to risk_reason


@dataclass
class Rule:
    """
    A single business rule.
    condition: a function that takes a Decision and returns True if rule applies.
    override:  what to change when it fires.
    """
    name: str
    description: str
    condition: Callable[[Decision], bool]
    override: RuleOverride
    enabled: bool = True


# ─────────────────────────────────────────
# Rule definitions
# Add/remove/modify rules here — no code
# changes needed anywhere else
# ─────────────────────────────────────────

def _get_amount(decision: Decision) -> float:
    """Safely extract amount from payload."""
    return float(decision.payload.get("amount", 0))


RULES: list[Rule] = [

    Rule(
        name="large_transfer_threshold",
        description="Any transfer above $10,000 is always critical and irreversible.",
        condition=lambda d: (
            d.action_type in ("wire_transfer", "bank_transfer", "payment")
            and _get_amount(d) > 10_000
        ),
        override=RuleOverride(
            impact=ImpactLevel.CRITICAL,
            reversibility=Reversibility.IRREVERSIBLE,
            reason="Transfer exceeds $10,000 threshold."
        )
    ),

    Rule(
        name="mass_communication_block",
        description="Sending to more than 100 recipients is always high impact.",
        condition=lambda d: (
            d.action_type in ("send_email", "send_notification", "broadcast")
            and int(d.payload.get("recipient_count", 0)) > 100
        ),
        override=RuleOverride(
            impact=ImpactLevel.HIGH,
            reversibility=Reversibility.IRREVERSIBLE,
            add_approvers=["Communications Manager"],
            reason="Mass communication to more than 100 recipients."
        )
    ),

    Rule(
        name="production_data_protection",
        description="Any action mentioning production environment needs approval.",
        condition=lambda d: (
            "production" in d.description.lower()
            or "production" in d.context.lower()
            or d.payload.get("environment") == "production"
        ),
        override=RuleOverride(
            impact=ImpactLevel.HIGH,
            add_approvers=["Engineering Lead"],
            reason="Action targets production environment."
        )
    ),

    Rule(
        name="new_vendor_payment",
        description="Payments to new/unverified vendors need Finance Manager approval.",
        condition=lambda d: (
            d.action_type in ("wire_transfer", "payment")
            and d.payload.get("vendor_status") == "new"
        ),
        override=RuleOverride(
            impact=ImpactLevel.HIGH,
            add_approvers=["Finance Manager"],
            reason="Payment to a new/unverified vendor."
        )
    ),

    Rule(
        name="policy_document_modification",
        description="Modifying policy documents always requires approval.",
        condition=lambda d: (
            d.action_type in ("modify_document", "update_policy", "delete_document")
            and "policy" in d.description.lower()
        ),
        override=RuleOverride(
            reversibility=Reversibility.IRREVERSIBLE,
            impact=ImpactLevel.HIGH,
            add_approvers=["Compliance Officer"],
            reason="Policy document modification requires compliance review."
        )
    ),

    Rule(
        name="data_deletion_hard_block",
        description="Deleting any data record is always a hard block.",
        condition=lambda d: d.action_type in (
            "delete_record", "delete_data", "purge", "drop_table"
        ),
        override=RuleOverride(
            reversibility=Reversibility.IRREVERSIBLE,
            impact=ImpactLevel.CRITICAL,
            route=RouteDecision.HARD_BLOCK,
            reason="Data deletion is always blocked — requires manual process."
        )
    ),

]


# ─────────────────────────────────────────
# Rules Engine
# ─────────────────────────────────────────

@dataclass
class RulesEngineResult:
    rules_fired: list[str]              # names of rules that matched
    overrides_applied: list[str]        # what changed
    final_classification: ClassificationResult


class RulesEngine:

    def apply(
        self,
        decision: Decision,
        classification: ClassificationResult
    ) -> RulesEngineResult:
        """
        Apply all enabled rules against the decision.
        Rules can escalate impact, change reversibility, force a route,
        or add approvers. Rules never de-escalate (can't lower impact).
        """
        rules_fired = []
        overrides_applied = []

        # work on mutable copies
        impact = classification.impact
        reversibility = classification.reversibility
        route_override = None
        extra_approvers = []
        extra_reasons = []

        for rule in RULES:
            if not rule.enabled:
                continue

            try:
                if not rule.condition(decision):
                    continue
            except Exception as e:
                logger.warning(f"Rule '{rule.name}' condition error: {e}")
                continue

            logger.info(f"Rule fired: '{rule.name}' for decision {decision.decision_id}")
            rules_fired.append(rule.name)
            ov = rule.override

            # escalate impact only, never downgrade
            if ov.impact and _impact_level(ov.impact) > _impact_level(impact):
                overrides_applied.append(
                    f"impact: {impact.value} → {ov.impact.value} (rule: {rule.name})"
                )
                impact = ov.impact

            # override reversibility if rule is more conservative
            if ov.reversibility:
                if ov.reversibility == Reversibility.IRREVERSIBLE:
                    overrides_applied.append(
                        f"reversibility: {reversibility.value} → irreversible (rule: {rule.name})"
                    )
                    reversibility = ov.reversibility

            # route override — only hard_block can be forced directly
            if ov.route == RouteDecision.HARD_BLOCK:
                route_override = RouteDecision.HARD_BLOCK
                overrides_applied.append(f"route: hard_block (rule: {rule.name})")

            if ov.add_approvers:
                extra_approvers.extend(ov.add_approvers)

            if ov.reason:
                extra_reasons.append(ov.reason)

        # derive final route
        if route_override:
            final_route = route_override
        else:
            final_route = ROUTE_MATRIX.get(
                (reversibility, impact),
                RouteDecision.NEEDS_APPROVAL
            )

        # merge approvers (deduplicate)
        all_approvers = list(dict.fromkeys(
            classification.suggested_approvers + extra_approvers
        ))

        # build final risk reason
        base_reason = classification.risk_reason
        if extra_reasons:
            base_reason = base_reason + " | " + " | ".join(extra_reasons)

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


def _impact_level(impact: ImpactLevel) -> int:
    """Convert impact to int for comparison."""
    return {
        ImpactLevel.LOW: 1,
        ImpactLevel.MEDIUM: 2,
        ImpactLevel.HIGH: 3,
        ImpactLevel.CRITICAL: 4
    }.get(impact, 0)