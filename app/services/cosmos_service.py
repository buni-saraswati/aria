import uuid
import logging
from datetime import datetime, timezone
from azure.cosmos import CosmosClient
from config import Config
from app.models.decision import Decision, DecisionStatus

logger = logging.getLogger(__name__)


class CosmosService:
    def __init__(self):
        self.client = CosmosClient(Config.COSMOS_ENDPOINT, Config.COSMOS_KEY)
        self.db = self.client.get_database_client(Config.COSMOS_DATABASE)
        self.decisions = self.db.get_container_client("decisions")
        self.audit_log = self.db.get_container_client("audit-log")

    def save_decision(self, decision: Decision) -> Decision:
        self.decisions.create_item(decision.to_cosmos_item())
        logger.info(f"Saved: {decision.decision_id}")
        return decision

    def get_decision(self, decision_id: str) -> Decision:
        item = self.decisions.read_item(decision_id, partition_key=decision_id)
        return Decision.from_cosmos_item(item)

    def update_decision(self, decision: Decision) -> Decision:
        decision.updated_at = datetime.now(timezone.utc).isoformat()
        self.decisions.replace_item(decision.decision_id, decision.to_cosmos_item())
        logger.info(f"Updated: {decision.decision_id} → {decision.status.value}")
        return decision

    def list_decisions(self, agent_id: str = None, status: str = None) -> list[Decision]:
        filters, params = [], []
        if agent_id:
            filters.append("c.agent_id = @agent_id")
            params.append({"name": "@agent_id", "value": agent_id})
        if status:
            filters.append("c.status = @status")
            params.append({"name": "@status", "value": status})

        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        query = f"SELECT * FROM c {where} ORDER BY c.submitted_at DESC OFFSET 0 LIMIT 50"

        items = list(self.decisions.query_items(
            query=query,
            parameters=params if params else None,
            enable_cross_partition_query=True
        ))
        return [Decision.from_cosmos_item(i) for i in items]

    def append_audit_event(
        self,
        decision_id: str,
        event_type: str,
        actor: str,
        details: dict = None,
        from_status: DecisionStatus = None,
        to_status: DecisionStatus = None
    ):
        event = {
            "id": str(uuid.uuid4()),
            "decision_id": decision_id,
            "event_type": event_type,
            "actor": actor,
            "from_status": from_status.value if from_status else None,
            "to_status": to_status.value if to_status else None,
            "details": details or {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.audit_log.create_item(event)

    def get_audit_trail(self, decision_id: str) -> list[dict]:
        query = """
            SELECT * FROM c
            WHERE c.decision_id = @decision_id
            ORDER BY c.timestamp ASC
        """
        return list(self.audit_log.query_items(
            query=query,
            parameters=[{"name": "@decision_id", "value": decision_id}],
            enable_cross_partition_query=True
        ))