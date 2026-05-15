import logging
from app.models.decision import Decision, DecisionStatus

logger = logging.getLogger(__name__)


class FreshnessValidator:

    def validate(self, decision: Decision) -> tuple[bool, list[str]]:
        """
        Check all data sources attached to the decision.
        Returns (passed, list_of_stale_source_names)
        """
        if not decision.data_sources:
            # no data sources declared → passes by default
            return True, []

        stale = [ds.name for ds in decision.data_sources if ds.is_stale()]

        if stale:
            logger.warning(f"Stale sources for {decision.decision_id}: {stale}")
            return False, stale

        logger.info(f"Freshness check passed for {decision.decision_id}")
        return True, []