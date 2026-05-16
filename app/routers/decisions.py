import logging
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from app.models.decision import Decision, DecisionStatus, DataSource
from app.models.schemas import (
    SubmitDecisionRequest, SubmitDecisionResponse,
    AuditTrailResponse, ApproveDecisionRequest, RejectDecisionRequest,
    ExecuteDecisionRequest, RollbackDecisionRequest
)
from app.services.cosmos_service import CosmosService
from app.services.pipeline import run_classification_pipeline
from app.services.approval_service import ApprovalService
from app.services.execution_service import ExecutionService

router = APIRouter(prefix="/decisions", tags=["Decisions"])
logger = logging.getLogger(__name__)


@router.post("/submit", response_model=SubmitDecisionResponse, status_code=202)
def submit_decision(request: SubmitDecisionRequest, background_tasks: BackgroundTasks):
    try:
        decision = Decision(
            agent_id=request.agent_id,
            action_type=request.action_type,
            description=request.description,
            payload=request.payload,
            context=request.context,
            status=DecisionStatus.SUBMITTED
        )
        for ds in request.data_sources:
            decision.data_sources.append(DataSource(
                name=ds.name,
                last_synced_at=ds.last_synced_at,
                max_age_hours=ds.max_age_hours
            ))

        cosmos = CosmosService()
        cosmos.save_decision(decision)
        cosmos.append_audit_event(
            decision_id=decision.decision_id,
            event_type="decision_submitted",
            actor=decision.agent_id,
            to_status=DecisionStatus.SUBMITTED,
            details={"action_type": decision.action_type}
        )
        background_tasks.add_task(run_classification_pipeline, decision.decision_id)

        return SubmitDecisionResponse(
            decision_id=decision.decision_id,
            status=decision.status.value,
            message="Decision submitted. Classification running.",
            submitted_at=decision.submitted_at
        )
    except Exception as e:
        logger.error(f"submit_decision error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{decision_id}/approve")
def approve_decision(decision_id: str, request: ApproveDecisionRequest):
    try:
        service = ApprovalService()
        decision = service.approve(decision_id, request.approver_id, request.reason)
        return {
            "decision_id": decision_id,
            "status": decision.status.value,
            "approvals_collected": sum(
                1 for a in decision.approvals if a.action == "approved"
            ),
            "required_approvals": decision.required_approvals
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{decision_id}/reject")
def reject_decision(decision_id: str, request: RejectDecisionRequest):
    try:
        service = ApprovalService()
        decision = service.reject(decision_id, request.approver_id, request.reason)
        return {
            "decision_id": decision_id,
            "status": decision.status.value,
            "rejected_by": request.approver_id,
            "reason": request.reason
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{decision_id}/execute")
def execute_decision(decision_id: str, request: ExecuteDecisionRequest):
    """Execute an approved decision."""
    try:
        service = ExecutionService()
        decision = service.execute(decision_id)
        return {
            "decision_id": decision_id,
            "status": decision.status.value,
            "execution_result": decision.execution_result,
            "rollback_available": decision.rollback_available,
            "snapshot_id": decision.snapshot_id,
            "completed_at": decision.completed_at
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"execute_decision error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{decision_id}/rollback")
def rollback_decision(decision_id: str, request: RollbackDecisionRequest):
    """Rollback a completed decision to its pre-action state."""
    try:
        service = ExecutionService()
        decision = service.rollback(decision_id, request.requested_by, request.reason)
        return {
            "decision_id": decision_id,
            "status": decision.status.value,
            "rolled_back_by": request.requested_by,
            "reason": request.reason,
            "snapshot_id": decision.snapshot_id
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"rollback_decision error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ttl/expire")
def trigger_ttl_expiry():
    try:
        service = ApprovalService()
        service.expire_pending_decisions()
        return {"message": "TTL expiry check completed."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
def list_decisions(
    agent_id: str = Query(default=None),
    status: str = Query(default=None)
):
    try:
        cosmos = CosmosService()
        decisions = cosmos.list_decisions(agent_id=agent_id, status=status)
        return {"decisions": [d.to_cosmos_item() for d in decisions]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{decision_id}")
def get_decision(decision_id: str):
    try:
        cosmos = CosmosService()
        decision = cosmos.get_decision(decision_id)
        return decision.to_cosmos_item()
    except Exception:
        raise HTTPException(status_code=404, detail=f"Decision not found: {decision_id}")


@router.get("/{decision_id}/audit", response_model=AuditTrailResponse)
def get_audit_trail(decision_id: str):
    try:
        cosmos = CosmosService()
        trail = cosmos.get_audit_trail(decision_id)
        return AuditTrailResponse(decision_id=decision_id, events=trail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/stats/summary")
def get_stats():
    """Decision counts by status. Used by monitoring dashboard."""
    try:
        cosmos = CosmosService()
        return cosmos.get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))