import logging
from datetime import datetime, timezone, timedelta
from app.models.decision import (
    Decision, DecisionStatus, ApprovalRecord
)
from app.services.cosmos_service import CosmosService, ConcurrencyError
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

APPROVAL_TTL_MINUTES = 30


class ApprovalService:
    def __init__(self):
        self.cosmos = CosmosService()

    def set_expiry(self, decision: Decision) -> Decision:
        expiry = datetime.now(timezone.utc) + timedelta(minutes=APPROVAL_TTL_MINUTES)
        decision.expires_at = expiry.isoformat()
        return decision

    def approve(self, decision_id: str, approver_id: str, reason: str = None) -> Decision:
        """
        Record an approval using optimistic concurrency.
        Raises ConcurrencyError if two approvals land simultaneously.
        """
        decision, etag = self.cosmos.get_decision(decision_id)
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

        try:
            self.cosmos.update_decision(decision, etag=etag)
        except ConcurrencyError:
            raise ConcurrencyError(
                "Another approval was recorded simultaneously. Please reload and retry."
            )

        self.cosmos.append_audit_event(
            decision_id=decision_id,
            event_type="decision_approved" if decision.status == DecisionStatus.APPROVED
                       else "partial_approval_recorded",
            actor=approver_id,
            from_status=DecisionStatus.PENDING_APPROVAL,
            to_status=decision.status,
            details={
                "reason": reason,
                "approvals_collected": approval_count,
                "required": decision.required_approvals
            }
        )
        return decision

    def reject(self, decision_id: str, approver_id: str, reason: str) -> Decision:
        decision, etag = self.cosmos.get_decision(decision_id)
        self._validate_action(decision, approver_id)

        record = ApprovalRecord(
            approver_id=approver_id,
            action="rejected",
            reason=reason
        )
        decision.approvals.append(record)
        decision.status = DecisionStatus.REJECTED

        self.cosmos.update_decision(decision, etag=etag)
        self.cosmos.append_audit_event(
            decision_id=decision_id,
            event_type="decision_rejected",
            actor=approver_id,
            from_status=DecisionStatus.PENDING_APPROVAL,
            to_status=DecisionStatus.REJECTED,
            details={"reason": reason}
        )
        return decision

    def expire_pending_decisions(self):
        now = datetime.now(timezone.utc).isoformat()
        pending = self.cosmos.list_decisions(status=DecisionStatus.PENDING_APPROVAL.value)
        expired_count = 0

        for decision in pending:
            if not decision.expires_at:
                continue
            if decision.expires_at <= now:
                # get fresh etag before updating
                decision, etag = self.cosmos.get_decision(decision.decision_id)
                decision.status = DecisionStatus.REJECTED
                self.cosmos.update_decision(decision, etag=etag)
                NotificationService().notify_expired(decision)  
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

        if expired_count:
            logger.info(f"TTL monitor: expired {expired_count} decisions")

    def _validate_action(self, decision: Decision, approver_id: str):
        if decision.status != DecisionStatus.PENDING_APPROVAL:
            raise ValueError(
                f"Decision '{decision.decision_id}' is '{decision.status.value}', "
                f"not 'pending_approval'."
            )
        already_approved = [
            a for a in decision.approvals
            if a.approver_id == approver_id and a.action == "approved"
        ]
        if already_approved:
            raise ValueError(
                f"Approver '{approver_id}' has already approved this decision."
            )