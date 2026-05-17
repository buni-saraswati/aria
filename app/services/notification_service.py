import logging
import requests
from config import Config
from app.models.decision import Decision, ImpactLevel

logger = logging.getLogger(__name__)

# impact → colour for Slack/Teams message
IMPACT_COLOR = {
    "low":      "#27AE60",
    "medium":   "#F39C12",
    "high":     "#E67E22",
    "critical": "#C0392B"
}

IMPACT_EMOJI = {
    "low":      "🟢",
    "medium":   "🟡",
    "high":     "🟠",
    "critical": "🔴"
}


class NotificationService:

    def notify_pending_approval(self, decision: Decision):
        """
        Notify approvers when a decision needs human review.
        Sends to configured webhook (Slack, Teams, or custom).
        Falls back to log if webhook not configured.
        """
        if not Config.NOTIFICATION_ENABLED or not Config.NOTIFICATION_WEBHOOK_URL:
            self._log_notification(decision)
            return

        try:
            impact = decision.classification.impact.value if decision.classification else "unknown"
            emoji = IMPACT_EMOJI.get(impact, "⚪")
            approvers = (
                decision.classification.suggested_approvers
                if decision.classification else []
            )
            risk_reason = (
                decision.classification.risk_reason
                if decision.classification else "No classification available"
            )
            expires_at = decision.expires_at or "Not set"

            approve_url = f"{Config.ARIA_BASE_URL}/decisions/{decision.decision_id}/approve"
            reject_url = f"{Config.ARIA_BASE_URL}/decisions/{decision.decision_id}/reject"

            # detect webhook type and format accordingly
            if "hooks.slack.com" in Config.NOTIFICATION_WEBHOOK_URL:
                payload = self._slack_payload(
                    decision, impact, emoji, approvers,
                    risk_reason, expires_at, approve_url, reject_url
                )
            elif "webhook.office.com" in Config.NOTIFICATION_WEBHOOK_URL:
                payload = self._teams_payload(
                    decision, impact, emoji, approvers,
                    risk_reason, expires_at, approve_url, reject_url
                )
            else:
                payload = self._generic_payload(
                    decision, impact, emoji, approvers,
                    risk_reason, expires_at, approve_url, reject_url
                )

            response = requests.post(
                Config.NOTIFICATION_WEBHOOK_URL,
                json=payload,
                timeout=5
            )
            response.raise_for_status()
            logger.info(f"Notification sent for decision {decision.decision_id}")

        except Exception as e:
            # notification failure must never block the pipeline
            logger.warning(f"Notification failed for {decision.decision_id}: {e}")
            self._log_notification(decision)

    def notify_expired(self, decision: Decision):
        """Log when a decision expires without approval."""
        logger.warning(
            f"[ARIA TTL] Decision expired without approval: "
            f"{decision.decision_id} | {decision.action_type} | "
            f"agent: {decision.agent_id}"
        )

    def _log_notification(self, decision: Decision):
        """Fallback — log to console when webhook not configured."""
        impact = decision.classification.impact.value if decision.classification else "unknown"
        approvers = (
            decision.classification.suggested_approvers
            if decision.classification else []
        )
        logger.info(
            f"\n"
            f"  ┌── ARIA: Approval Required {'─' * 30}\n"
            f"  │  Decision:   {decision.decision_id}\n"
            f"  │  Agent:      {decision.agent_id}\n"
            f"  │  Action:     {decision.action_type}\n"
            f"  │  Impact:     {impact.upper()}\n"
            f"  │  Approvers:  {', '.join(approvers) or 'Not specified'}\n"
            f"  │  Expires:    {decision.expires_at or 'Not set'}\n"
            f"  └{'─' * 50}"
        )

    def _slack_payload(
        self, decision, impact, emoji, approvers,
        risk_reason, expires_at, approve_url, reject_url
    ) -> dict:
        color = IMPACT_COLOR.get(impact, "#95A5A6")
        return {
            "attachments": [{
                "color": color,
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"{emoji} ARIA — Approval Required"
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*Decision ID*\n`{decision.decision_id[:8]}...`"},
                            {"type": "mrkdwn", "text": f"*Impact*\n{impact.upper()}"},
                            {"type": "mrkdwn", "text": f"*Agent*\n{decision.agent_id}"},
                            {"type": "mrkdwn", "text": f"*Action*\n{decision.action_type}"}
                        ]
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Risk Reason*\n{risk_reason}"
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*Approvers*\n{', '.join(approvers) or 'Not specified'}"},
                            {"type": "mrkdwn", "text": f"*Expires*\n{expires_at[11:16]} UTC" if expires_at != "Not set" else "*Expires*\nNot set"}
                        ]
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": (
                                f"*Description*\n{decision.description}"
                            )
                        }
                    }
                ]
            }]
        }

    def _teams_payload(
        self, decision, impact, emoji, approvers,
        risk_reason, expires_at, approve_url, reject_url
    ) -> dict:
        color = IMPACT_COLOR.get(impact, "#95A5A6").lstrip("#")
        return {
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "themeColor": color,
            "summary": f"ARIA: Approval Required — {decision.action_type}",
            "sections": [{
                "activityTitle": f"{emoji} ARIA — Approval Required",
                "activitySubtitle": f"Impact: **{impact.upper()}**",
                "facts": [
                    {"name": "Decision ID", "value": decision.decision_id[:8] + "..."},
                    {"name": "Agent", "value": decision.agent_id},
                    {"name": "Action", "value": decision.action_type},
                    {"name": "Description", "value": decision.description},
                    {"name": "Risk Reason", "value": risk_reason},
                    {"name": "Suggested Approvers", "value": ", ".join(approvers) or "Not specified"},
                    {"name": "Expires", "value": expires_at[11:16] + " UTC" if expires_at != "Not set" else "Not set"}
                ]
            }],
            "potentialAction": [
                {
                    "@type": "OpenUri",
                    "name": "View in ARIA",
                    "targets": [{"os": "default", "uri": f"{Config.ARIA_BASE_URL}/docs"}]
                }
            ]
        }

    def _generic_payload(
        self, decision, impact, emoji, approvers,
        risk_reason, expires_at, approve_url, reject_url
    ) -> dict:
        """Generic JSON payload for custom webhooks."""
        return {
            "event": "approval_required",
            "decision_id": decision.decision_id,
            "agent_id": decision.agent_id,
            "action_type": decision.action_type,
            "description": decision.description,
            "impact": impact,
            "risk_reason": risk_reason,
            "suggested_approvers": approvers,
            "expires_at": expires_at,
            "links": {
                "approve": approve_url,
                "reject": reject_url,
                "view": f"{Config.ARIA_BASE_URL}/decisions/{decision.decision_id}"
            }
        }