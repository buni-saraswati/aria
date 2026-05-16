import logging
from datetime import datetime, timezone, timedelta
from app.models.decision import (
    Decision, DecisionStatus, ApprovalRecord, RouteDecision
)
from app.services.cosmos_service import CosmosService

logger = logging.getLogger(__name__)

APPROVAL_TTL_MINUTES = 30


class ApprovalService:

    def __init__(self):
        self.cosmos = CosmosService()

    def set_expiry(self, decision: Decision) -> Decision:
        """
        Set expiry timestamp when a decision enters pending_approval.
        Called by pipeline after routing decision.
        """
        expiry = datetime.now(timezone.utc) + timedelta(minutes=APPROVAL_TTL_MINUTES)
        decision.expires_at = expiry.isoformat()
        return decision

    def approve(self, decision_id: str, approver_id: str, reason: str = None) -> Decision:
        """Record an approval. If enough approvals collected, mark as approved."""
        decision = self.cosmos.get_decision(decision_id)
        self._validate_action(decision, approver_id)

        record = ApprovalRecord(
            approver_id=approver_id,
            action="approved",
            reason=reason
        )
        decision.approvals.append(record)

        approval_count = sum(1 for a in decision.approvals if a.action == "approved")

        if approval_count >= decision.required_approvals:
            decision.status = DecisionStatus.APPROVED
            self.cosmos.update_decision(decision)
            self.cosmos.append_audit_event(
                decision_id=decision_id,
                event_type="decision_approved",
                actor=approver_id,
                from_status=DecisionStatus.PENDING_APPROVAL,
                to_status=DecisionStatus.APPROVED,
                details={
                    "reason": reason,
                    "approvals_collected": approval_count,
                    "required": decision.required_approvals
                }
            )
            logger.info(f"Decision approved: {decision_id} by {approver_id}")
        else:
            # partial approval — still waiting for more
            self.cosmos.update_decision(decision)
            self.cosmos.append_audit_event(
                decision_id=decision_id,
                event_type="partial_approval_recorded",
                actor=approver_id,
                details={
                    "reason": reason,
                    "approvals_so_far": approval_count,
                    "required": decision.required_approvals
                }
            )
            logger.info(
                f"Partial approval for {decision_id}: "
                f"{approval_count}/{decision.required_approvals}"
            )

        return decision

    def reject(self, decision_id: str, approver_id: str, reason: str) -> Decision:
        """Reject a decision. One rejection is enough regardless of required approvals."""
        decision = self.cosmos.get_decision(decision_id)
        self._validate_action(decision, approver_id)

        record = ApprovalRecord(
            approver_id=approver_id,
            action="rejected",
            reason=reason
        )
        decision.approvals.append(record)
        decision.status = DecisionStatus.REJECTED

        self.cosmos.update_decision(decision)
        self.cosmos.append_audit_event(
            decision_id=decision_id,
            event_type="decision_rejected",
            actor=approver_id,
            from_status=DecisionStatus.PENDING_APPROVAL,
            to_status=DecisionStatus.REJECTED,
            details={"reason": reason}
        )
        logger.info(f"Decision rejected: {decision_id} by {approver_id}")
        return decision

    def expire_pending_decisions(self):
        """
        Called by the TTL background job every minute.
        Auto-rejects decisions that have been pending too long.
        """
        now = datetime.now(timezone.utc).isoformat()
        pending = self.cosmos.list_decisions(status=DecisionStatus.PENDING_APPROVAL.value)
        expired_count = 0

        for decision in pending:
            if not decision.expires_at:
                continue
            if decision.expires_at <= now:
                decision.status = DecisionStatus.REJECTED
                self.cosmos.update_decision(decision)
                self.cosmos.append_audit_event(
                    decision_id=decision.decision_id,
                    event_type="approval_expired",
                    actor="aria-ttl-monitor",
                    from_status=DecisionStatus.PENDING_APPROVAL,
                    to_status=DecisionStatus.REJECTED,
                    details={
                        "reason": f"No response within {APPROVAL_TTL_MINUTES} minutes.",
                        "expired_at": now
                    }
                )
                expired_count += 1
                logger.info(f"Decision expired: {decision.decision_id}")

        if expired_count:
            logger.info(f"TTL monitor: expired {expired_count} decisions")

    def _validate_action(self, decision: Decision, approver_id: str):
        """Raise if the decision isn't in a state that can be approved/rejected."""
        if decision.status != DecisionStatus.PENDING_APPROVAL:
            raise ValueError(
                f"Decision {decision.decision_id} is '{decision.status.value}', "
                f"not 'pending_approval'. Cannot approve/reject."
            )

        # prevent same approver from approving twice
        already_approved = [
            a for a in decision.approvals
            if a.approver_id == approver_id and a.action == "approved"
        ]
        if already_approved:
            raise ValueError(f"Approver '{approver_id}' has already approved this decision.")