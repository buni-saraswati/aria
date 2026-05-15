import logging
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from app.models.decision import Decision, DecisionStatus, DataSource
from app.models.schemas import (
    SubmitDecisionRequest,
    SubmitDecisionResponse,
    AuditTrailResponse
)
from app.services.cosmos_service import CosmosService
from app.services.pipeline import run_classification_pipeline

router = APIRouter(prefix="/decisions", tags=["Decisions"])
logger = logging.getLogger(__name__)


@router.post("/submit", response_model=SubmitDecisionResponse, status_code=202)
def submit_decision(request: SubmitDecisionRequest, background_tasks: BackgroundTasks):
    """Submit an AI action for evaluation by ARIA."""
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

        # fire classification pipeline in background
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


@router.get("/")
def list_decisions(
    agent_id: str = Query(default=None),
    status: str = Query(default=None)
):
    """List decisions with optional filters."""
    try:
        cosmos = CosmosService()
        decisions = cosmos.list_decisions(agent_id=agent_id, status=status)
        return {"decisions": [d.to_cosmos_item() for d in decisions]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{decision_id}")
def get_decision(decision_id: str):
    """Get current state of a decision."""
    try:
        cosmos = CosmosService()
        decision = cosmos.get_decision(decision_id)
        return decision.to_cosmos_item()
    except Exception:
        raise HTTPException(status_code=404, detail=f"Decision not found: {decision_id}")


@router.get("/{decision_id}/audit", response_model=AuditTrailResponse)
def get_audit_trail(decision_id: str):
    """Full immutable audit trail of a decision."""
    try:
        cosmos = CosmosService()
        trail = cosmos.get_audit_trail(decision_id)
        return AuditTrailResponse(decision_id=decision_id, events=trail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))