from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, timezone
import uuid


@dataclass
class RuleCondition:
    """
    Defines when a rule fires.
    All non-None fields must match for the rule to apply.
    """
    # match on action_type — list means "any of these"
    action_types: Optional[list[str]] = None

    # match on payload field
    payload_field: Optional[str] = None
    operator: Optional[str] = None        # gt, lt, gte, lte, eq, contains
    value: Optional[float | str] = None

    # match on description/context keyword
    description_contains: Optional[str] = None
    context_contains: Optional[str] = None

    # match on payload field equality
    payload_equals: Optional[dict] = None  # {"vendor_status": "new"}


@dataclass
class RuleOverride:
    """What a rule changes when it fires."""
    impact: Optional[str] = None           # escalate to this impact
    reversibility: Optional[str] = None    # override reversibility
    force_route: Optional[str] = None      # force hard_block
    add_approvers: list[str] = field(default_factory=list)
    reason: str = ""


@dataclass
class Rule:
    rule_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    enabled: bool = True
    condition: RuleCondition = field(default_factory=RuleCondition)
    override: RuleOverride = field(default_factory=RuleOverride)
    created_by: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: Optional[str] = None
    fired_count: int = 0                   # how many times this rule has fired

    def to_cosmos_item(self) -> dict:
        return {
            "id": self.rule_id,
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "enabled": self.enabled,
            "condition": {
                "action_types": self.condition.action_types,
                "payload_field": self.condition.payload_field,
                "operator": self.condition.operator,
                "value": self.condition.value,
                "description_contains": self.condition.description_contains,
                "context_contains": self.condition.context_contains,
                "payload_equals": self.condition.payload_equals
            },
            "override": {
                "impact": self.override.impact,
                "reversibility": self.override.reversibility,
                "force_route": self.override.force_route,
                "add_approvers": self.override.add_approvers,
                "reason": self.override.reason
            },
            "created_by": self.created_by,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "fired_count": self.fired_count
        }

    @classmethod
    def from_cosmos_item(cls, item: dict) -> "Rule":
        cond = item.get("condition", {})
        ov = item.get("override", {})
        r = cls()
        r.rule_id = item["rule_id"]
        r.name = item.get("name", "")
        r.description = item.get("description", "")
        r.enabled = item.get("enabled", True)
        r.created_by = item.get("created_by", "")
        r.created_at = item.get("created_at", "")
        r.updated_at = item.get("updated_at")
        r.fired_count = item.get("fired_count", 0)
        r.condition = RuleCondition(
            action_types=cond.get("action_types"),
            payload_field=cond.get("payload_field"),
            operator=cond.get("operator"),
            value=cond.get("value"),
            description_contains=cond.get("description_contains"),
            context_contains=cond.get("context_contains"),
            payload_equals=cond.get("payload_equals")
        )
        r.override = RuleOverride(
            impact=ov.get("impact"),
            reversibility=ov.get("reversibility"),
            force_route=ov.get("force_route"),
            add_approvers=ov.get("add_approvers", []),
            reason=ov.get("reason", "")
        )
        return r