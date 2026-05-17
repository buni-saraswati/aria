import logging
from datetime import datetime, timezone
from azure.cosmos import CosmosClient
from config import Config
from app.models.rule import Rule, RuleCondition, RuleOverride

logger = logging.getLogger(__name__)

COSMOS_INTERNAL_FIELDS = {"_rid", "_self", "_etag", "_attachments", "_ts"}


class RulesService:
    def __init__(self):
        self.client = CosmosClient(Config.COSMOS_ENDPOINT, Config.COSMOS_KEY)
        self.db = self.client.get_database_client(Config.COSMOS_DATABASE)
        self.rules = self.db.get_container_client("rules")

    def _clean(self, item: dict) -> dict:
        return {k: v for k, v in item.items() if k not in COSMOS_INTERNAL_FIELDS}

    def create_rule(self, rule: Rule) -> Rule:
        self.rules.create_item(rule.to_cosmos_item())
        logger.info(f"Rule created: {rule.rule_id} ({rule.name})")
        return rule

    def get_rule(self, rule_id: str) -> Rule:
        item = self.rules.read_item(rule_id, partition_key=rule_id)
        return Rule.from_cosmos_item(self._clean(item))

    def list_rules(self, enabled_only: bool = False) -> list[Rule]:
        if enabled_only:
            query = "SELECT * FROM c WHERE c.enabled = true ORDER BY c.created_at ASC"
        else:
            query = "SELECT * FROM c ORDER BY c.created_at ASC"

        items = list(self.rules.query_items(
            query=query,
            enable_cross_partition_query=True
        ))
        return [Rule.from_cosmos_item(self._clean(i)) for i in items]

    def update_rule(self, rule_id: str, updates: dict) -> Rule:
        rule = self.get_rule(rule_id)
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()

        if "name" in updates:
            rule.name = updates["name"]
        if "description" in updates:
            rule.description = updates["description"]
        if "condition" in updates:
            c = updates["condition"]
            rule.condition = RuleCondition(**c)
        if "override" in updates:
            o = updates["override"]
            rule.override = RuleOverride(**o)

        rule.updated_at = updates["updated_at"]
        self.rules.replace_item(rule_id, rule.to_cosmos_item())
        logger.info(f"Rule updated: {rule_id}")
        return rule

    def toggle_rule(self, rule_id: str, enabled: bool) -> Rule:
        rule = self.get_rule(rule_id)
        rule.enabled = enabled
        rule.updated_at = datetime.now(timezone.utc).isoformat()
        self.rules.replace_item(rule_id, rule.to_cosmos_item())
        state = "enabled" if enabled else "disabled"
        logger.info(f"Rule {state}: {rule_id}")
        return rule

    def increment_fired_count(self, rule_id: str):
        """Called every time a rule fires — tracks usage."""
        try:
            rule = self.get_rule(rule_id)
            rule.fired_count += 1
            self.rules.replace_item(rule_id, rule.to_cosmos_item())
        except Exception as e:
            logger.warning(f"Could not increment fired_count for {rule_id}: {e}")