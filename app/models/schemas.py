from pydantic import BaseModel, Field
from typing import Optional


class DataSourceInput(BaseModel):
    name: str
    last_synced_at: Optional[str] = None
    max_age_hours: float = 6.0


class SubmitDecisionRequest(BaseModel):
    agent_id: str
    action_type: str
    description: str
    payload: dict = Field(default_factory=dict)
    context: str = ""
    data_sources: list[DataSourceInput] = Field(default_factory=list)


class SubmitDecisionResponse(BaseModel):
    decision_id: str
    status: str
    message: str
    submitted_at: str


class AuditTrailResponse(BaseModel):
    decision_id: str
    events: list[dict]


class ApproveDecisionRequest(BaseModel):
    approver_id: str
    reason: Optional[str] = None


class RejectDecisionRequest(BaseModel):
    approver_id: str
    reason: str         

class ExecuteDecisionRequest(BaseModel):
    requested_by: str                  


class RollbackDecisionRequest(BaseModel):
    requested_by: str
    reason: str        

class RuleConditionInput(BaseModel):
    action_types: Optional[list[str]] = None
    payload_field: Optional[str] = None
    operator: Optional[str] = None         # gt, lt, gte, lte, eq, contains
    value: Optional[float | str] = None
    description_contains: Optional[str] = None
    context_contains: Optional[str] = None
    payload_equals: Optional[dict] = None


class RuleOverrideInput(BaseModel):
    impact: Optional[str] = None           # low, medium, high, critical
    reversibility: Optional[str] = None    # reversible, irreversible, unknown
    force_route: Optional[str] = None      # hard_block only
    add_approvers: list[str] = Field(default_factory=list)
    reason: str = ""
class CreateRuleRequest(BaseModel):
    name: str
    description: str
    condition: RuleConditionInput
    override: RuleOverrideInput
    created_by: str


class UpdateRuleRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    condition: Optional[RuleConditionInput] = None
    override: Optional[RuleOverrideInput] = None