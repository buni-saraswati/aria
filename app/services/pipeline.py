import logging
from app.models.decision import Decision, DecisionStatus, RouteDecision
from app.services.cosmos_service import CosmosService
from app.services.freshness import FreshnessValidator
from app.services.classifier import Classifier
from app.services.rules_engine import RulesEngine
from app.services.approval_service import ApprovalService
from app.telemetry import tracer

logger = logging.getLogger(__name__)


def run_classification_pipeline(decision_id: str):
    with tracer.start_as_current_span("pipeline.run") as pipeline_span:
        pipeline_span.set_attribute("decision_id", decision_id)
        cosmos = CosmosService()

        try:
            decision = cosmos.get_decision(decision_id)
            pipeline_span.set_attribute("agent_id", decision.agent_id)
            pipeline_span.set_attribute("action_type", decision.action_type)

            # Step 1: Freshness
            with tracer.start_as_current_span("pipeline.freshness_check"):
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
                    pipeline_span.set_attribute("outcome", "rejected_stale_data")
                    return

                decision.freshness_passed = True
                cosmos.update_decision(decision)
                cosmos.append_audit_event(
                    decision_id=decision_id,
                    event_type="freshness_check_passed",
                    actor="aria-pipeline",
                    details={"sources_checked": [ds.name for ds in decision.data_sources]}
                )

            # Step 2: AI Classification
            with tracer.start_as_current_span("pipeline.ai_classification") as clf_span:
                classifier = Classifier()
                ai_result = classifier.classify(decision)

                clf_span.set_attribute("reversibility", ai_result.reversibility.value)
                clf_span.set_attribute("impact", ai_result.impact.value)
                clf_span.set_attribute("confidence", ai_result.confidence)

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

            # Step 3: Rules Engine
            with tracer.start_as_current_span("pipeline.rules_engine") as rules_span:
                rules_engine = RulesEngine()
                rules_result = rules_engine.apply(decision, ai_result)
                final = rules_result.final_classification

                rules_span.set_attribute("rules_fired_count", len(rules_result.rules_fired))
                rules_span.set_attribute("rules_fired", str(rules_result.rules_fired))

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

            # Step 4: Finalize
            decision.classification = final
            decision.route = final.route

            if final.route == RouteDecision.AUTO_APPROVE:
                decision.status = DecisionStatus.AUTO_APPROVED

            elif final.route == RouteDecision.NEEDS_APPROVAL:
                decision.status = DecisionStatus.PENDING_APPROVAL
                decision.required_approvals = (
                    2 if final.impact.value == "critical" else 1
                )
                approval_service = ApprovalService()
                decision = approval_service.set_expiry(decision)

            elif final.route == RouteDecision.HARD_BLOCK:
                decision.status = DecisionStatus.REJECTED

            pipeline_span.set_attribute("final_route", final.route.value)
            pipeline_span.set_attribute("final_status", decision.status.value)

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
                    "suggested_approvers": final.suggested_approvers,
                    "expires_at": decision.expires_at
                }
            )

            logger.info(f"Pipeline done: {decision_id} → {decision.status.value}")

        except Exception as e:
            pipeline_span.set_attribute("error", str(e))
            pipeline_span.record_exception(e)
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