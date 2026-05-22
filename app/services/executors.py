import logging
import random
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class ExecutionResult:
    def __init__(self, success: bool, output: dict, pre_state: dict, rollback_possible: bool):
        self.success = success
        self.output = output
        self.pre_state = pre_state              # state before action ran
        self.rollback_possible = rollback_possible


def execute_wire_transfer(payload: dict) -> ExecutionResult:
    """
    Simulate a wire transfer.
    Pre-state: current account balance.
    Rollback: not possible (money sent).
    """
    amount = payload.get("amount", 0)
    vendor_id = payload.get("vendor_id", "unknown")

    pre_state = {
        "account_balance": 1_000_000,           # simulated
        "pending_transfers": [],
        "captured_at": datetime.now(timezone.utc).isoformat()
    }

    output = {
        "transaction_id": f"TXN-{random.randint(100000, 999999)}",
        "amount": amount,
        "vendor_id": vendor_id,
        "status": "transferred",
        "transferred_at": datetime.now(timezone.utc).isoformat(),
        "remaining_balance": pre_state["account_balance"] - amount
    }

    return ExecutionResult(
        success=True,
        output=output,
        pre_state=pre_state,
        rollback_possible=False             # wire transfers can't be reversed
    )


def execute_send_email(payload: dict) -> ExecutionResult:
    """
    Simulate sending an email.
    Pre-state: email draft content.
    Rollback: possible within 2 minutes (recall window).
    """
    recipient = payload.get("recipient", "unknown")
    subject = payload.get("subject", "No subject")

    pre_state = {
        "draft_content": payload.get("body", ""),
        "recipient": recipient,
        "captured_at": datetime.now(timezone.utc).isoformat()
    }

    output = {
        "message_id": f"MSG-{random.randint(100000, 999999)}",
        "recipient": recipient,
        "subject": subject,
        "status": "sent",
        "sent_at": datetime.now(timezone.utc).isoformat()
    }

    return ExecutionResult(
        success=True,
        output=output,
        pre_state=pre_state,
        rollback_possible=True              # can recall within window
    )


def execute_modify_document(payload: dict) -> ExecutionResult:
    """
    Simulate modifying a policy document.
    Pre-state: current document content/version.
    Rollback: restore previous version.
    """
    doc_id = payload.get("document_id", "unknown")
    section = payload.get("section", "unknown")

    pre_state = {
        "document_id": doc_id,
        "version": "v4.2",                  # simulated current version
        "section": section,
        "content": f"[Simulated current content of {doc_id} section {section}]",
        "last_modified": "2026-05-01T10:00:00Z",
        "captured_at": datetime.now(timezone.utc).isoformat()
    }

    output = {
        "document_id": doc_id,
        "section": section,
        "new_version": "v4.3",
        "status": "modified",
        "modified_at": datetime.now(timezone.utc).isoformat()
    }

    return ExecutionResult(
        success=True,
        output=output,
        pre_state=pre_state,
        rollback_possible=True              # can restore v4.2
    )


def execute_update_payment_status(payload: dict) -> ExecutionResult:
    """
    Simulate updating a payment record status.
    Pre-state: current payment record.
    Rollback: restore previous status.
    """
    payment_id = payload.get("payment_id", "unknown")
    new_status = payload.get("status", "unknown")

    pre_state = {
        "payment_id": payment_id,
        "current_status": "pending",        # simulated
        "captured_at": datetime.now(timezone.utc).isoformat()
    }

    output = {
        "payment_id": payment_id,
        "previous_status": pre_state["current_status"],
        "new_status": new_status,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }

    return ExecutionResult(
        success=True,
        output=output,
        pre_state=pre_state,
        rollback_possible=True
    )


def execute_generate_report(payload: dict) -> ExecutionResult:
    """
    Simulate generating a report.
    Pre-state: not meaningful (read-only action).
    Rollback: not needed.
    """
    pre_state = {}
    output = {
        "report_id": f"RPT-{random.randint(100000, 999999)}",
        "report_type": payload.get("report_type", "summary"),
        "period": payload.get("period", "weekly"),
        "status": "generated",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "download_url": f"/reports/RPT-{random.randint(100000, 999999)}.pdf"
    }

    return ExecutionResult(
        success=True,
        output=output,
        pre_state=pre_state,
        rollback_possible=False             # read-only, nothing to roll back
    )


# ─────────────────────────────────────────
# Executor registry
# Maps action_type → executor function
# Add new action types here only
# ─────────────────────────────────────────

EXECUTORS = {
    "wire_transfer":          execute_wire_transfer,
    "bank_transfer":          execute_wire_transfer,
    "payment":                execute_wire_transfer,
    "send_email":             execute_send_email,
    "send_reminder_email":    execute_send_email,
    "modify_document":        execute_modify_document,
    "update_policy":          execute_modify_document,
    "update_payment_status":  execute_update_payment_status,
    "generate_report":        execute_generate_report,
    "refund":               execute_wire_transfer,
    "update_payment_terms": execute_update_payment_status,
    "send_notification":    execute_send_email,
    "broadcast_message":    execute_send_email,
    "create_document":      execute_modify_document,
    "archive_document":     execute_modify_document,
    "export_data":          execute_generate_report,
    "run_audit":            execute_generate_report,
    "update_record":        execute_update_payment_status,
    "create_record":        execute_update_payment_status,
    "archive_record":       execute_update_payment_status,
    "deploy_config":        execute_modify_document,
    "update_credentials":   execute_modify_document,
    "revoke_access":        execute_modify_document,
    "grant_access":         execute_modify_document,
}


def get_executor(action_type: str):
    """Return executor for action_type. Raises if not found."""
    executor = EXECUTORS.get(action_type)
    if not executor:
        raise ValueError(
            f"No executor registered for action_type '{action_type}'. "
            f"Known types: {list(EXECUTORS.keys())}"
        )
    return executor