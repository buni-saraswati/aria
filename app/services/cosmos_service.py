import uuid
import logging
from datetime import datetime, timezone
from azure.cosmos import CosmosClient
from azure.core import MatchConditions
from azure.core.exceptions import ResourceModifiedError
from config import Config
from app.models.decision import Decision, DecisionStatus

logger = logging.getLogger(__name__)

COSMOS_INTERNAL_FIELDS = {"_rid", "_self", "_etag", "_attachments", "_ts"}


class CosmosService:
    def __init__(self):
        self.client = CosmosClient(Config.COSMOS_ENDPOINT, Config.COSMOS_KEY)
        self.db = self.client.get_database_client(Config.COSMOS_DATABASE)
        self.decisions = self.db.get_container_client("decisions")
        self.audit_log = self.db.get_container_client("audit-log")

    def _clean(self, item: dict) -> dict:
        return {k: v for k, v in item.items() if k not in COSMOS_INTERNAL_FIELDS}

    def save_decision(self, decision: Decision) -> Decision:
        self.decisions.create_item(decision.to_cosmos_item())
        logger.info(f"Saved: {decision.decision_id}")
        return decision

    def get_decision(self, decision_id: str) -> tuple[Decision, str]:
        """
        Returns (Decision, etag).
        etag is used for optimistic concurrency on updates.
        """
        response = self.decisions.read_item(
            decision_id,
            partition_key=decision_id
        )
        etag = response.get("_etag")
        return Decision.from_cosmos_item(self._clean(response)), etag

    def update_decision(self, decision: Decision, etag: str = None) -> Decision:
        """
        Update a decision.
        If etag provided: uses optimistic concurrency — fails if another
        process modified the document since we last read it.
        If no etag: unconditional update (used in pipeline, single writer).
        """
        decision.updated_at = datetime.now(timezone.utc).isoformat()
        item = decision.to_cosmos_item()

        try:
            if etag:
                self.decisions.replace_item(
                    decision.decision_id,
                    item,
                    etag=etag,
                    match_condition=MatchConditions.IfNotModified
                )
            else:
                self.decisions.replace_item(decision.decision_id, item)

        except ResourceModifiedError:
            raise ConcurrencyError(
                f"Decision {decision.decision_id} was modified by another request. "
                f"Please reload and retry."
            )

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
        return [Decision.from_cosmos_item(self._clean(i)) for i in items]

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
        items = list(self.audit_log.query_items(
            query=query,
            parameters=[{"name": "@decision_id", "value": decision_id}],
            enable_cross_partition_query=True
        ))
        return [self._clean(i) for i in items]

    def get_stats(self) -> dict:
        """Aggregate decision counts by status."""
        # fetch all statuses and count in Python instead
        query = "SELECT c.status FROM c"
        items = list(self.decisions.query_items(
            query=query,
            enable_cross_partition_query=True
        ))

        stats = {}
        for item in items:
            status = item.get("status", "unknown")
            stats[status] = stats.get(status, 0) + 1

        # ensure all known statuses present even if zero
        all_statuses = [s.value for s in DecisionStatus]
        return {s: stats.get(s, 0) for s in all_statuses}


class ConcurrencyError(Exception):
    """Raised when optimistic concurrency check fails."""
    pass