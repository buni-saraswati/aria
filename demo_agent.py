"""
ARIA Demo Agent
"""

import requests
import time

BASE_URL = "http://localhost:8000"


def submit(payload: dict) -> str:
    res = requests.post(f"{BASE_URL}/decisions/submit", json=payload)
    data = res.json()
    decision_id = data["decision_id"]
    print(f"  Submitted: {decision_id} ({payload['action_type']})")
    return decision_id


def approve(decision_id: str, approver: str):
    requests.post(
        f"{BASE_URL}/decisions/{decision_id}/approve",
        json={"approver_id": approver, "reason": "Reviewed and approved."}
    )
    print(f"  Approved:  {decision_id} by {approver}")


def execute(decision_id: str):
    res = requests.post(
        f"{BASE_URL}/decisions/{decision_id}/execute",
        json={"requested_by": "demo-runner"}
    )
    data = res.json()
    print(f"  Executed:  {decision_id} → {data.get('status')} "
          f"(rollback: {data.get('rollback_available')})")
    return data


def wait_for_classification(decision_id: str, seconds: int = 6):
    time.sleep(seconds)
    res = requests.get(f"{BASE_URL}/decisions/{decision_id}")
    status = res.json().get("status")
    print(f"  Status:    {decision_id} → {status}")
    return status


def separator(title: str):
    print(f"\n{'─' * 50}")
    print(f"  {title}")
    print('─' * 50)


if __name__ == "__main__":
    print("\n ARIA Demo Agent Starting...\n")

    # Scenario 1: Auto-approved (low risk)
    separator("Scenario 1: Generate Report → auto_approve")
    d1 = submit({
        "agent_id": "reporting-agent-v1",
        "action_type": "generate_report",
        "description": "Generate weekly vendor payment summary report",
        "payload": {"report_type": "summary", "period": "weekly"}
    })
    status = wait_for_classification(d1)
    if status == "auto_approved":
        execute(d1)

    # Scenario 2: Needs approval → approved 
    separator("Scenario 2: Update Payment Status → approve → execute → rollback")
    d2 = submit({
        "agent_id": "payment-agent-v1",
        "action_type": "update_payment_status",
        "description": "Update payment status to received for invoice INV-2091",
        "payload": {"payment_id": "PAY-2091", "status": "received"}
    })
    wait_for_classification(d2)
    approve(d2, "finance-manager@company.com")
    result = execute(d2)
    if result.get("rollback_available"):
        requests.post(
            f"{BASE_URL}/decisions/{d2}/rollback",
            json={"requested_by": "finance-manager@company.com",
                  "reason": "Wrong invoice ID — rolling back."}
        )
        print(f"  Rolled back: {d2}")

    # Scenario 3: Policy doc → rules fire
    separator("Scenario 3: Modify Policy Document → rules override → approve → execute")
    d3 = submit({
        "agent_id": "ops-agent-v1",
        "action_type": "modify_document",
        "description": "Update vendor payment policy document section 4.1",
        "payload": {"document_id": "POL-001", "section": "4.1"}
    })
    wait_for_classification(d3)
    approve(d3, "compliance-officer@company.com")
    execute(d3)

    # Scenario 4: Hard block (data deletion)
    separator("Scenario 4: Delete Record → hard_block (no approval possible)")
    d4 = submit({
        "agent_id": "cleanup-agent-v1",
        "action_type": "delete_record",
        "description": "Delete duplicate transaction records from Q1 2026",
        "payload": {"table": "transactions", "filter": "quarter=Q1_2026"}
    })
    wait_for_classification(d4)

    # Scenario 5: Stale data → rejected at freshness
    separator("Scenario 5: Wire Transfer → stale data → rejected before AI runs")
    d5 = submit({
        "agent_id": "payment-agent-v1",
        "action_type": "wire_transfer",
        "description": "Transfer $15,000 to Vendor ABC",
        "payload": {"amount": 15000, "vendor_id": "ACC-500"},
        "data_sources": [
            {
                "name": "finance_system",
                "last_synced_at": "2026-04-01T10:00:00Z",
                "max_age_hours": 6
            }
        ]
    })
    wait_for_classification(d5)

    # Scenario 6: Large transfer → hard block
    separator("Scenario 6: $500K Wire Transfer → rules escalate → hard_block")
    d6 = submit({
        "agent_id": "payment-agent-v1",
        "action_type": "wire_transfer",
        "description": "Transfer $500,000 to new vendor for equipment purchase",
        "payload": {
            "amount": 500000,
            "vendor_id": "ACC-999",
            "vendor_status": "new"
        },
        "data_sources": [
            {
                "name": "finance_system",
                "last_synced_at": "2026-05-16T10:00:00Z",
                "max_age_hours": 6
            }
        ]
    })
    wait_for_classification(d6)

    # Scenario 7: Needs approval → rejected
    separator("Scenario 7: Send Email → approve → rejected by approver")
    d7 = submit({
        "agent_id": "comms-agent-v1",
        "action_type": "send_email",
        "description": "Send payment reminder to Vendor X",
        "payload": {
            "recipient": "vendor-x@example.com",
            "subject": "Payment Reminder - Invoice #3301",
            "body": "Dear Vendor X, this is a reminder..."
        }
    })
    wait_for_classification(d7)
    requests.post(
        f"{BASE_URL}/decisions/{d7}/reject",
        json={
            "approver_id": "manager@company.com",
            "reason": "Wrong vendor selected. Do not send."
        }
    )
    print(f"  Rejected: {d7}")

    print(f"\n{'─' * 50}")
    print("  Demo complete. Check /docs to explore results.")
    print(f"{'─' * 50}\n")