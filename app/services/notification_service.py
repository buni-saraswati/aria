import logging
import requests
from config import Config
from app.models.decision import Decision

logger = logging.getLogger(__name__)

IMPACT_EMOJI = {
    "low":      "🟢",
    "medium":   "🟡",
    "high":     "🟠",
    "critical": "🔴"
}

IMPACT_COLOR = {
    "low":      "#27AE60",
    "medium":   "#F39C12",
    "high":     "#E67E22",
    "critical": "#C0392B"
}


class NotificationService:

    def notify_pending_approval(self, decision: Decision):
        if not Config.NOTIFICATION_ENABLED:
            self._log_notification(decision)
            return

        if Config.GMAIL_USER and Config.GMAIL_APP_PASSWORD:
            self._send_email(decision)
        elif Config.SENDGRID_API_KEY:
            self._send_email(decision)
        elif Config.NOTIFICATION_WEBHOOK_URL:
            self._send_webhook(decision)
        else:
            self._log_notification(decision)

    def notify_expired(self, decision: Decision):
        logger.warning(
            f"[ARIA TTL] Decision expired: {decision.decision_id} "
            f"| {decision.action_type} | agent: {decision.agent_id}"
        )

    def _send_email(self, decision: Decision):
        """Send approval notification via Gmail SMTP."""
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        try:
            impact = decision.classification.impact.value \
                if decision.classification else "unknown"
            emoji = IMPACT_EMOJI.get(impact, "⚪")
            color = IMPACT_COLOR.get(impact, "#95A5A6")
            approvers = decision.classification.suggested_approvers \
                if decision.classification else []
            risk_reason = decision.classification.risk_reason \
                if decision.classification else "N/A"
            expires_at = decision.expires_at or "Not set"
            expires_display = expires_at[11:16] + " UTC" \
                if expires_at != "Not set" else "Not set"

            recipients = [
                e.strip()
                for e in Config.NOTIFICATION_APPROVER_EMAILS.split(",")
                if e.strip()
            ]

            if not recipients:
                logger.warning("No approver emails configured")
                self._log_notification(decision)
                return

            subject = (
                f"[ARIA] {emoji} Approval Required — "
                f"{decision.action_type} ({impact.upper()})"
            )

            html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        body {{ font-family: Arial, sans-serif; background: #f4f4f4; margin: 0; padding: 20px; }}
        .container {{ max-width: 600px; margin: 0 auto; background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .header {{ background: #1E3A5F; padding: 28px 32px; }}
        .header h1 {{ color: #fff; margin: 0; font-size: 22px; }}
        .header p {{ color: #A8D8EA; margin: 6px 0 0; font-size: 14px; }}
        .badge {{ display: inline-block; background: {color}; color: #fff; padding: 4px 14px; border-radius: 20px; font-size: 13px; font-weight: bold; margin-top: 10px; }}
        .body {{ padding: 28px 32px; }}
        .label {{ font-size: 11px; text-transform: uppercase; color: #888; margin-bottom: 4px; letter-spacing: 0.5px; }}
        .value {{ font-size: 15px; color: #1A1A1A; margin-bottom: 16px; }}
        .id-box {{ background: #f8f9fa; border: 1px solid #e0e0e0; border-radius: 4px; padding: 8px 12px; font-family: monospace; font-size: 13px; color: #2E86AB; margin-bottom: 16px; }}
        .reason-box {{ background: #FFF8E7; border-left: 4px solid {color}; padding: 12px 16px; margin-bottom: 16px; font-size: 14px; }}
        .grid {{ display: table; width: 100%; margin-bottom: 16px; }}
        .col {{ display: table-cell; width: 50%; vertical-align: top; padding-right: 16px; }}
        .divider {{ border: none; border-top: 1px solid #eee; margin: 20px 0; }}
        .actions {{ padding: 20px 32px 28px; background: #f8f9fa; }}
        .actions p {{ font-size: 13px; color: #666; margin: 0 0 14px; }}
        .footer {{ padding: 16px 32px; text-align: center; font-size: 12px; color: #aaa; border-top: 1px solid #eee; }}
    </style>
    </head>
    <body>
    <div class="container">
        <div class="header">
        <h1>{emoji} ARIA — Approval Required</h1>
        <p>An AI agent action requires your review before execution</p>
        <span class="badge">{impact.upper()} IMPACT</span>
        </div>
        <div class="body">
        <div class="label">Decision ID</div>
        <div class="id-box">{decision.decision_id}</div>

        <div class="grid">
            <div class="col">
            <div class="label">Agent</div>
            <div class="value">{decision.agent_id}</div>
            </div>
            <div class="col">
            <div class="label">Action Type</div>
            <div class="value">{decision.action_type}</div>
            </div>
        </div>

        <div class="label">Description</div>
        <div class="value">{decision.description}</div>

        <div class="label">Risk Reason</div>
        <div class="reason-box">{risk_reason}</div>

        <hr class="divider">

        <div class="grid">
            <div class="col">
            <div class="label">Suggested Approvers</div>
            <div class="value">{', '.join(approvers) or 'Not specified'}</div>
            </div>
            <div class="col">
            <div class="label">Expires At</div>
            <div class="value">{expires_display}</div>
            </div>
        </div>

        <div class="label">Payload</div>
        <div class="id-box">{decision.payload}</div>
        </div>

        <div class="actions">
        <p>Use ARIA Swagger UI to approve or reject this decision:</p>
        <p><strong>Swagger:</strong> {Config.ARIA_BASE_URL}/docs</p>
        <p><strong>Decision ID:</strong> {decision.decision_id}</p>
        </div>

        <div class="footer">
        ARIA — AI Reliability &amp; Integrity Architecture<br>
        This notification was sent because a decision requires human oversight.
        </div>
    </div>
    </body>
    </html>
    """

            # connect to Gmail SMTP
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(Config.GMAIL_USER, Config.GMAIL_APP_PASSWORD)

            for recipient in recipients:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = f"ARIA Notifications <{Config.GMAIL_USER}>"
                msg["To"] = recipient
                msg.attach(MIMEText(html_body, "html"))
                server.sendmail(Config.GMAIL_USER, recipient, msg.as_string())
                logger.info(f"Email sent to {recipient} for {decision.decision_id}")

            server.quit()

        except Exception as e:
            logger.warning(f"Gmail notification failed: {e}")
            self._log_notification(decision)

    def _send_webhook(self, decision: Decision):
        """Send to Slack/Teams/custom webhook."""
        try:
            impact = decision.classification.impact.value \
                if decision.classification else "unknown"
            emoji = IMPACT_EMOJI.get(impact, "⚪")
            approvers = decision.classification.suggested_approvers \
                if decision.classification else []
            risk_reason = decision.classification.risk_reason \
                if decision.classification else "N/A"
            expires_at = decision.expires_at or "Not set"

            payload = {
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
                    "approve": f"{Config.ARIA_BASE_URL}/decisions/{decision.decision_id}/approve",
                    "reject": f"{Config.ARIA_BASE_URL}/decisions/{decision.decision_id}/reject",
                    "view": f"{Config.ARIA_BASE_URL}/decisions/{decision.decision_id}"
                }
            }

            if "hooks.slack.com" in Config.NOTIFICATION_WEBHOOK_URL:
                payload = {
                    "text": f"{emoji} *ARIA — Approval Required*\n"
                            f"*Action:* {decision.action_type}\n"
                            f"*Impact:* {impact.upper()}\n"
                            f"*Reason:* {risk_reason}\n"
                            f"*Decision ID:* `{decision.decision_id[:8]}...`"
                }

            response = requests.post(
                Config.NOTIFICATION_WEBHOOK_URL,
                json=payload,
                timeout=5
            )
            response.raise_for_status()
            logger.info(f"Webhook notification sent for {decision.decision_id}")

        except Exception as e:
            logger.warning(f"Webhook notification failed: {e}")
            self._log_notification(decision)

    def _log_notification(self, decision: Decision):
        """Console fallback when no channel configured."""
        impact = decision.classification.impact.value \
            if decision.classification else "unknown"
        approvers = decision.classification.suggested_approvers \
            if decision.classification else []
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