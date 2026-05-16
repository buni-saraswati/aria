import logging
from datetime import datetime, timezone
from app.models.decision import Decision, DecisionStatus
from app.services.cosmos_service import CosmosService
from app.services.snapshot_service import SnapshotService
from app.services.executors import get_executor

logger = logging.getLogger(__name__)


class ExecutionService:
    def __init__(self):
        self.cosmos = CosmosService()
        self.snapshot = SnapshotService()

    def execute(self, decision_id: str) -> Decision:
        """
        Execute an approved decision.
        Flow: validate → snapshot → execute → save result
        """
        decision = self.cosmos.get_decision(decision_id)
        self._validate_executable(decision)

        # mark as executing
        prev_status = decision.status
        decision.status = DecisionStatus.EXECUTING
        self.cosmos.update_decision(decision)
        self.cosmos.append_audit_event(
            decision_id=decision_id,
            event_type="execution_started",
            actor="aria-execution-engine",
            from_status=prev_status,
            to_status=DecisionStatus.EXECUTING
        )

        try:
            # get the right executor for this action type
            executor = get_executor(decision.action_type)

            # run it — returns ExecutionResult with pre_state + output
            result = executor(decision.payload)

            # capture snapshot of pre-action state
            snapshot_id = None
            if result.pre_state:
                snapshot_id = self.snapshot.capture(
                    decision_id=decision_id,
                    state=result.pre_state
                )
                self.cosmos.append_audit_event(
                    decision_id=decision_id,
                    event_type="snapshot_captured",
                    actor="aria-execution-engine",
                    details={"snapshot_id": snapshot_id}
                )

            # save result
            decision.status = DecisionStatus.COMPLETED
            decision.execution_result = result.output
            decision.snapshot_id = snapshot_id
            decision.rollback_available = (
                result.rollback_possible and snapshot_id is not None
            )
            decision.completed_at = datetime.now(timezone.utc).isoformat()

            self.cosmos.update_decision(decision)
            self.cosmos.append_audit_event(
                decision_id=decision_id,
                event_type="execution_completed",
                actor="aria-execution-engine",
                from_status=DecisionStatus.EXECUTING,
                to_status=DecisionStatus.COMPLETED,
                details={
                    "output": result.output,
                    "rollback_available": decision.rollback_available,
                    "snapshot_id": snapshot_id
                }
            )
            logger.info(f"Execution completed: {decision_id}")

        except Exception as e:
            logger.error(f"Execution failed for {decision_id}: {e}")
            decision.status = DecisionStatus.FAILED
            decision.execution_result = {"error": str(e)}
            self.cosmos.update_decision(decision)
            self.cosmos.append_audit_event(
                decision_id=decision_id,
                event_type="execution_failed",
                actor="aria-execution-engine",
                from_status=DecisionStatus.EXECUTING,
                to_status=DecisionStatus.FAILED,
                details={"error": str(e)}
            )
            raise

        return decision

    def rollback(self, decision_id: str, requested_by: str, reason: str) -> Decision:
        """
        Rollback a completed decision by restoring its pre-action snapshot.
        """
        decision = self.cosmos.get_decision(decision_id)
        self._validate_rollback(decision)

        self.cosmos.append_audit_event(
            decision_id=decision_id,
            event_type="rollback_started",
            actor=requested_by,
            from_status=DecisionStatus.COMPLETED,
            details={"reason": reason, "snapshot_id": decision.snapshot_id}
        )

        try:
            # restore snapshot
            snapshot = self.snapshot.restore(decision.snapshot_id)
            restored_state = snapshot.get("state", {})

            # mark as rolled back
            decision.status = DecisionStatus.ROLLED_BACK
            decision.rollback_available = False
            self.cosmos.update_decision(decision)
            self.cosmos.append_audit_event(
                decision_id=decision_id,
                event_type="rollback_completed",
                actor=requested_by,
                from_status=DecisionStatus.COMPLETED,
                to_status=DecisionStatus.ROLLED_BACK,
                details={
                    "reason": reason,
                    "restored_state": restored_state,
                    "snapshot_id": decision.snapshot_id
                }
            )
            logger.info(f"Rollback completed: {decision_id}")

        except Exception as e:
            logger.error(f"Rollback failed for {decision_id}: {e}")
            self.cosmos.append_audit_event(
                decision_id=decision_id,
                event_type="rollback_failed",
                actor=requested_by,
                details={"error": str(e)}
            )
            raise

        return decision

    def _validate_executable(self, decision: Decision):
        """Only approved or auto_approved decisions can be executed."""
        allowed = {DecisionStatus.APPROVED, DecisionStatus.AUTO_APPROVED}
        if decision.status not in allowed:
            raise ValueError(
                f"Decision '{decision.decision_id}' has status "
                f"'{decision.status.value}'. Only approved decisions can be executed."
            )

    def _validate_rollback(self, decision: Decision):
        """Only completed decisions with a snapshot can be rolled back."""
        if decision.status != DecisionStatus.COMPLETED:
            raise ValueError(
                f"Decision '{decision.decision_id}' is '{decision.status.value}'. "
                f"Only completed decisions can be rolled back."
            )
        if not decision.rollback_available:
            raise ValueError(
                f"Decision '{decision.decision_id}' has no rollback available. "
                f"Either no snapshot was captured or the action is irreversible."
            )
        if not decision.snapshot_id:
            raise ValueError(
                f"Decision '{decision.decision_id}' has no snapshot_id."
            )