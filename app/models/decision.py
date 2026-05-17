from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone
from typing import Optional
import uuid


class Reversibility(str, Enum):
    REVERSIBLE = "reversible"
    IRREVERSIBLE = "irreversible"
    UNKNOWN = "unknown"


class ImpactLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DecisionStatus(str, Enum):
    SUBMITTED = "submitted"
    VALIDATING = "validating"
    CLASSIFIED = "classified"
    AUTO_APPROVED = "auto_approved"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class RouteDecision(str, Enum):
    AUTO_APPROVE = "auto_approve"
    NEEDS_APPROVAL = "needs_approval"
    HARD_BLOCK = "hard_block"


@dataclass
class DataSource:
    name: str
    last_synced_at: Optional[str]
    max_age_hours: float = 6.0

    def is_stale(self) -> bool:
        if not self.last_synced_at:
            return True
        last_sync = datetime.fromisoformat(self.last_synced_at.replace("Z", "+00:00"))
        age_hours = (datetime.now(timezone.utc) - last_sync).total_seconds() / 3600
        return age_hours > self.max_age_hours


@dataclass
class ClassificationResult:
    reversibility: Reversibility
    impact: ImpactLevel
    risk_reason: str
    suggested_approvers: list[str]
    confidence: float
    route: RouteDecision


@dataclass
class ApprovalRecord:
    approver_id: str
    action: str
    reason: Optional[str]
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class Decision:
    decision_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = ""
    action_type: str = ""
    description: str = ""
    payload: dict = field(default_factory=dict)
    context: str = ""
    data_sources: list[DataSource] = field(default_factory=list)
    freshness_passed: Optional[bool] = None
    stale_sources: list[str] = field(default_factory=list)
    classification: Optional[ClassificationResult] = None
    status: DecisionStatus = DecisionStatus.SUBMITTED
    route: Optional[RouteDecision] = None
    approvals: list[ApprovalRecord] = field(default_factory=list)
    required_approvals: int = 1
    expires_at: Optional[str] = None
    counterfactual: Optional[dict] = None
    snapshot_id: Optional[str] = None
    execution_result: Optional[dict] = None
    rollback_available: bool = False
    submitted_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: Optional[str] = None
    completed_at: Optional[str] = None

    def to_cosmos_item(self) -> dict:
        return {
            "id": self.decision_id,
            "decision_id": self.decision_id,
            "agent_id": self.agent_id,
            "action_type": self.action_type,
            "description": self.description,
            "payload": self.payload,
            "context": self.context,
            "counterfactual": self.counterfactual,
            "data_sources": [
                {
                    "name": ds.name,
                    "last_synced_at": ds.last_synced_at,
                    "max_age_hours": ds.max_age_hours
                }
                for ds in self.data_sources
            ],
            "freshness_passed": self.freshness_passed,
            "stale_sources": self.stale_sources,
            "classification": {
                "reversibility": self.classification.reversibility.value,
                "impact": self.classification.impact.value,
                "risk_reason": self.classification.risk_reason,
                "suggested_approvers": self.classification.suggested_approvers,
                "confidence": self.classification.confidence,
                "route": self.classification.route.value
            } if self.classification else None,
            "status": self.status.value,
            "route": self.route.value if self.route else None,
            "approvals": [
                {
                    "approver_id": a.approver_id,
                    "action": a.action,
                    "reason": a.reason,
                    "timestamp": a.timestamp
                }
                for a in self.approvals
            ],
            "required_approvals": self.required_approvals,
            "expires_at": self.expires_at,
            "snapshot_id": self.snapshot_id,
            "execution_result": self.execution_result,
            "rollback_available": self.rollback_available,
            "submitted_at": self.submitted_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at
        }

    @classmethod
    def from_cosmos_item(cls, item: dict) -> "Decision":
        d = cls()
        d.decision_id = item["decision_id"]
        d.agent_id = item.get("agent_id", "")
        d.action_type = item.get("action_type", "")
        d.description = item.get("description", "")
        d.payload = item.get("payload", {})
        d.context = item.get("context", "")
        d.freshness_passed = item.get("freshness_passed")
        d.stale_sources = item.get("stale_sources", [])
        d.status = DecisionStatus(item["status"])
        d.route = RouteDecision(item["route"]) if item.get("route") else None
        d.required_approvals = item.get("required_approvals", 1)
        d.expires_at = item.get("expires_at")
        d.snapshot_id = item.get("snapshot_id")
        d.execution_result = item.get("execution_result")
        d.rollback_available = item.get("rollback_available", False)
        d.submitted_at = item.get("submitted_at", "")
        d.updated_at = item.get("updated_at")
        d.completed_at = item.get("completed_at")
        d.counterfactual = item.get("counterfactual")
        d.data_sources = [
            DataSource(
                name=ds["name"],
                last_synced_at=ds.get("last_synced_at"),
                max_age_hours=ds.get("max_age_hours", 6.0)
            )
            for ds in item.get("data_sources", [])
        ]
        clf = item.get("classification")
        if clf:
            d.classification = ClassificationResult(
                reversibility=Reversibility(clf["reversibility"]),
                impact=ImpactLevel(clf["impact"]),
                risk_reason=clf["risk_reason"],
                suggested_approvers=clf.get("suggested_approvers", []),
                confidence=clf.get("confidence", 1.0),
                route=RouteDecision(clf["route"])
            )
        d.approvals = [
            ApprovalRecord(
                approver_id=a["approver_id"],
                action=a["action"],
                reason=a.get("reason"),
                timestamp=a["timestamp"]
            )
            for a in item.get("approvals", [])
        ]
        return d