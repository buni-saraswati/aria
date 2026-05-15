import logging
from app.models.decision import Decision, DecisionStatus, RouteDecision
from app.services.cosmos_service import CosmosService
from app.services.freshness import FreshnessValidator
from app.services.classifier import Classifier
from app.services.rules_engine import RulesEngine

logger = logging.getLogger(__name__)


def run_classification_pipeline(decision_id: str):
    """
    Background pipeline:
    submitted → freshness check → AI classification → rules engine → final status
    """
    cosmos = CosmosService()

    try:
        decision = cosmos.get_decision(decision_id)

        # ── Step 1: Freshness validation ──────────────────
        decision.status = DecisionStatus.VALIDATING
        cosmos.update_decision(decision)
        cosmos.append_audit_event(
            decision_id=decision_id,
            event_type="freshness_check_started",
            actor="aria-pipeline",
            from_status=DecisionStatus.SUBMITTED,
            to_status=DecisionStatus.VALIDATING
        )

        validator = FreshnessValidator()
        passed, stale_sources = validator.validate(decision)

        if not passed:
            decision.status = DecisionStatus.REJECTED
            decision.freshness_passed = False
            decision.stale_sources = stale_sources
            cosmos.update_decision(decision)
            cosmos.append_audit_event(
                decision_id=decision_id,
                event_type="freshness_check_failed",
                actor="aria-pipeline",
                from_status=DecisionStatus.VALIDATING,
                to_status=DecisionStatus.REJECTED,
                details={"stale_sources": stale_sources}
            )
            return

        decision.freshness_passed = True
        cosmos.update_decision(decision)
        cosmos.append_audit_event(
            decision_id=decision_id,
            event_type="freshness_check_passed",
            actor="aria-pipeline",
            details={"sources_checked": [ds.name for ds in decision.data_sources]}
        )

        # ── Step 2: AI Classification ─────────────────────
        classifier = Classifier()
        ai_result = classifier.classify(decision)

        cosmos.append_audit_event(
            decision_id=decision_id,
            event_type="ai_classification_completed",
            actor="aria-classifier",
            details={
                "reversibility": ai_result.reversibility.value,
                "impact": ai_result.impact.value,
                "route": ai_result.route.value,
                "risk_reason": ai_result.risk_reason,
                "confidence": ai_result.confidence
            }
        )

        # ── Step 3: Rules Engine ──────────────────────────
        rules_engine = RulesEngine()
        rules_result = rules_engine.apply(decision, ai_result)
        final = rules_result.final_classification

        if rules_result.rules_fired:
            cosmos.append_audit_event(
                decision_id=decision_id,
                event_type="rules_engine_applied",
                actor="aria-rules-engine",
                details={
                    "rules_fired": rules_result.rules_fired,
                    "overrides_applied": rules_result.overrides_applied
                }
            )
        else:
            cosmos.append_audit_event(
                decision_id=decision_id,
                event_type="rules_engine_no_match",
                actor="aria-rules-engine",
                details={"message": "No rules matched. AI classification unchanged."}
            )

        # ── Step 4: Save final result ─────────────────────
        decision.classification = final
        decision.route = final.route

        if final.route == RouteDecision.AUTO_APPROVE:
            decision.status = DecisionStatus.AUTO_APPROVED
        elif final.route == RouteDecision.NEEDS_APPROVAL:
            decision.status = DecisionStatus.PENDING_APPROVAL
        elif final.route == RouteDecision.HARD_BLOCK:
            decision.status = DecisionStatus.REJECTED

        cosmos.update_decision(decision)
        cosmos.append_audit_event(
            decision_id=decision_id,
            event_type="classification_finalized",
            actor="aria-pipeline",
            from_status=DecisionStatus.VALIDATING,
            to_status=decision.status,
            details={
                "final_reversibility": final.reversibility.value,
                "final_impact": final.impact.value,
                "final_route": final.route.value,
                "final_risk_reason": final.risk_reason,
                "suggested_approvers": final.suggested_approvers
            }
        )

        logger.info(f"Pipeline done: {decision_id} → {decision.status.value}")

    except Exception as e:
        logger.error(f"Pipeline failed for {decision_id}: {e}")
        try:
            decision = cosmos.get_decision(decision_id)
            decision.status = DecisionStatus.FAILED
            cosmos.update_decision(decision)
            cosmos.append_audit_event(
                decision_id=decision_id,
                event_type="pipeline_error",
                actor="aria-pipeline",
                to_status=DecisionStatus.FAILED,
                details={"error": str(e)}
            )
        except Exception as inner:
            logger.error(f"Could not update failed status: {inner}")