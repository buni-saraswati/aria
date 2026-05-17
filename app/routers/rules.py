import logging
from fastapi import APIRouter, HTTPException, Depends
from app.models.rule import Rule, RuleCondition, RuleOverride
from app.models.schemas import CreateRuleRequest, UpdateRuleRequest
from app.services.rules_service import RulesService
from app.auth import require_admin

router = APIRouter(prefix="/rules", tags=["Rules"])
logger = logging.getLogger(__name__)


@router.post("/", status_code=201)
def create_rule(request: CreateRuleRequest, role: str = Depends(require_admin)):
    """Create a new business rule."""
    try:
        rule = Rule(
            name=request.name,
            description=request.description,
            created_by=request.created_by,
            condition=RuleCondition(
                action_types=request.condition.action_types,
                payload_field=request.condition.payload_field,
                operator=request.condition.operator,
                value=request.condition.value,
                description_contains=request.condition.description_contains,
                context_contains=request.condition.context_contains,
                payload_equals=request.condition.payload_equals
            ),
            override=RuleOverride(
                impact=request.override.impact,
                reversibility=request.override.reversibility,
                force_route=request.override.force_route,
                add_approvers=request.override.add_approvers,
                reason=request.override.reason
            )
        )
        service = RulesService()
        service.create_rule(rule)
        return rule.to_cosmos_item()
    except Exception as e:
        logger.error(f"create_rule error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
def list_rules(
    enabled_only: bool = False,
    role: str = Depends(require_admin)
):
    """List all rules."""
    try:
        service = RulesService()
        rules = service.list_rules(enabled_only=enabled_only)
        return {
            "rules": [r.to_cosmos_item() for r in rules],
            "total": len(rules),
            "active": sum(1 for r in rules if r.enabled)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{rule_id}")
def get_rule(rule_id: str, role: str = Depends(require_admin)):
    """Get a single rule."""
    try:
        service = RulesService()
        rule = service.get_rule(rule_id)
        return rule.to_cosmos_item()
    except Exception:
        raise HTTPException(status_code=404, detail=f"Rule not found: {rule_id}")


@router.patch("/{rule_id}")
def update_rule(
    rule_id: str,
    request: UpdateRuleRequest,
    role: str = Depends(require_admin)
):
    """Update rule name, description, conditions, or overrides."""
    try:
        updates = request.model_dump(exclude_none=True)
        if not updates:
            raise HTTPException(status_code=400, detail="No updates provided.")
        service = RulesService()
        rule = service.update_rule(rule_id, updates)
        return rule.to_cosmos_item()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{rule_id}/enable")
def enable_rule(rule_id: str, role: str = Depends(require_admin)):
    """Enable a disabled rule."""
    try:
        service = RulesService()
        rule = service.toggle_rule(rule_id, enabled=True)
        return {"rule_id": rule_id, "enabled": True, "name": rule.name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{rule_id}/disable")
def disable_rule(rule_id: str, role: str = Depends(require_admin)):
    """Disable a rule without deleting it."""
    try:
        service = RulesService()
        rule = service.toggle_rule(rule_id, enabled=False)
        return {"rule_id": rule_id, "enabled": False, "name": rule.name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))