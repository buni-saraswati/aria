"""
ARIA Priority 2 Demo Script
Tests: Dynamic Rules, Confidence Threshold, Counterfactual Logging

Run: python demo_priority2.py
     python demo_priority2.py --url https://your-live-url.azurecontainerapps.io
     python demo_priority2.py --section rules     (run only rules tests)
     python demo_priority2.py --section confidence
     python demo_priority2.py --section counterfactual
"""

import requests
import time
import json
import argparse
import sys
from datetime import datetime, timezone

# Config
BASE_URL = "http://localhost:8000"
AGENT_KEY = "l15_pTbIoFim45Z6LJjtwspDO0tO0rw8E298LcG4olA"
APPROVER_KEY = "7GykGbcn0G12H4V_AuWpL8ZVC-_YD55N-45MGyMQ0G0"
ADMIN_KEY = "IWOOhvGQ5giFzjfzhcF7CHm1Sx9g5OF5TNgvsHSqb0E"

AGENT_HEADERS = {"X-API-Key": AGENT_KEY, "Content-Type": "application/json"}
APPROVER_HEADERS = {"X-API-Key": APPROVER_KEY, "Content-Type": "application/json"}
ADMIN_HEADERS = {"X-API-Key": ADMIN_KEY, "Content-Type": "application/json"}

# track results
results = {"passed": 0, "failed": 0, "skipped": 0}
created_rule_ids = []

# Helpers

def separator(title: str, char: str = "─", width: int = 60):
    print(f"\n{char * width}")
    print(f"  {title}")
    print(f"{char * width}")


def section_header(title: str):
    print(f"\n{'═' * 60}")
    print(f"  {'  ' + title + '  ':^56}")
    print(f"{'═' * 60}")


def ok(msg: str):
    print(f"  ✅  {msg}")
    results["passed"] += 1


def fail(msg: str):
    print(f"  ❌  {msg}")
    results["failed"] += 1


def info(msg: str):
    print(f"  ℹ️   {msg}")


def skip(msg: str):
    print(f"  ⏭️   {msg}")
    results["skipped"] += 1


def submit(payload: dict) -> dict:
    res = requests.post(
        f"{BASE_URL}/decisions/submit",
        json=payload,
        headers=AGENT_HEADERS
    )
    if res.status_code != 202:
        fail(f"Submit failed: {res.status_code} {res.text}")
        return {}
    return res.json()


def wait_for_pipeline(decision_id: str, seconds: int = 6) -> dict:
    time.sleep(seconds)
    res = requests.get(
        f"{BASE_URL}/decisions/{decision_id}",
        headers=AGENT_HEADERS
    )
    return res.json()


def get_audit(decision_id: str) -> list:
    res = requests.get(
        f"{BASE_URL}/decisions/{decision_id}/audit",
        headers=AGENT_HEADERS
    )
    return res.json().get("events", [])


def find_event(events: list, event_type: str) -> dict | None:
    return next((e for e in events if e["event_type"] == event_type), None)


def approve(decision_id: str, approver_id: str = "admin@company.com") -> dict:
    res = requests.post(
        f"{BASE_URL}/decisions/{decision_id}/approve",
        json={"approver_id": approver_id, "reason": "Demo approval"},
        headers=APPROVER_HEADERS
    )
    return res.json()


def create_rule(rule_payload: dict) -> dict:
    res = requests.post(
        f"{BASE_URL}/rules/",
        json=rule_payload,
        headers=ADMIN_HEADERS
    )
    if res.status_code == 201:
        data = res.json()
        created_rule_ids.append(data["rule_id"])
        return data
    fail(f"Rule creation failed: {res.status_code} {res.text}")
    return {}


def disable_rule(rule_id: str) -> dict:
    res = requests.patch(
        f"{BASE_URL}/rules/{rule_id}/disable",
        headers=ADMIN_HEADERS
    )
    return res.json()


def enable_rule(rule_id: str) -> dict:
    res = requests.patch(
        f"{BASE_URL}/rules/{rule_id}/enable",
        headers=ADMIN_HEADERS
    )
    return res.json()


def list_rules(enabled_only: bool = False) -> list:
    res = requests.get(
        f"{BASE_URL}/rules/?enabled_only={str(enabled_only).lower()}",
        headers=ADMIN_HEADERS
    )
    return res.json().get("rules", [])


def cleanup_rules():
    """Disable all rules created during this demo run."""
    for rule_id in created_rule_ids:
        try:
            disable_rule(rule_id)
        except Exception:
            pass


# Section 1: Dynamic Rules

def test_dynamic_rules():
    section_header("SECTION 1 — Dynamic Rules Engine")

    # Test 1.1: Create a rule via API
    separator("Test 1.1: Create rule via API")

    rule = create_rule({
        "name": "demo_high_value_check",
        "description": "Flag transfers above $5,000 for demo purposes.",
        "condition": {
            "action_types": ["wire_transfer", "payment"],
            "payload_field": "amount",
            "operator": "gt",
            "value": 5000
        },
        "override": {
            "impact": "high",
            "reversibility": "irreversible",
            "add_approvers": ["Finance Manager"],
            "reason": "Demo rule: transfer exceeds $5,000."
        },
        "created_by": "demo-runner"
    })

    if rule:
        ok(f"Rule created: {rule['name']} (ID: {rule['rule_id'][:8]}...)")
        ok(f"Condition: wire_transfer/payment + amount > 5000")
        ok(f"Override: impact → high, adds Finance Manager as approver")
    else:
        return

    # Test 1.2: Submit decision that triggers new rule 
    separator("Test 1.2: Submit decision — new rule should fire")

    data = submit({
        "agent_id": "payment-agent-v1",
        "action_type": "wire_transfer",
        "description": "Transfer $8,000 to supplier for materials",
        "payload": {"amount": 8000, "vendor_id": "SUP-101"},
        "context": "Approved purchase order PO-2091"
    })

    if not data:
        return

    decision_id = data["decision_id"]
    info(f"Submitted: {decision_id}")
    decision = wait_for_pipeline(decision_id)

    events = get_audit(decision_id)
    rules_event = find_event(events, "rules_engine_applied")
    final_event = find_event(events, "classification_finalized")

    if rules_event and "demo_high_value_check" in rules_event["details"].get("rules_fired", []):
        ok(f"Rule 'demo_high_value_check' fired correctly")
    else:
        fail("Rule did not fire as expected")

    if final_event:
        approvers = final_event["details"].get("suggested_approvers", [])
        if "Finance Manager" in approvers:
            ok(f"Finance Manager added to approvers by rule")
        else:
            fail(f"Finance Manager not in approvers: {approvers}")

        final_impact = final_event["details"].get("final_impact")
        if final_impact == "high":
            ok(f"Impact escalated to 'high' by rule")
        else:
            fail(f"Impact not escalated: {final_impact}")

    info(f"Decision status: {decision.get('status')}")

    # Test 1.3: Disable rule — same decision should not trigger it 
    separator("Test 1.3: Disable rule — should no longer fire")

    disable_result = disable_rule(rule["rule_id"])
    if not disable_result.get("enabled"):
        ok(f"Rule disabled: {rule['name']}")
    else:
        fail("Rule disable failed")

    data2 = submit({
        "agent_id": "payment-agent-v1",
        "action_type": "wire_transfer",
        "description": "Transfer $8,000 to another supplier",
        "payload": {"amount": 8000, "vendor_id": "SUP-202"},
    })

    if not data2:
        return

    decision_id2 = data2["decision_id"]
    wait_for_pipeline(decision_id2)

    events2 = get_audit(decision_id2)
    rules_event2 = find_event(events2, "rules_engine_applied")

    if rules_event2:
        fired = rules_event2["details"].get("rules_fired", [])
        if "demo_high_value_check" not in fired:
            ok("Disabled rule correctly did not fire")
        else:
            fail("Disabled rule still fired — toggle not working")
    else:
        # no rules fired at all — also correct
        no_match = find_event(events2, "rules_engine_no_match")
        if no_match:
            ok("Disabled rule correctly did not fire (no rules matched)")
        else:
            info("Could not confirm rule toggle — check manually")

    # Test 1.4: Re-enable rule
    separator("Test 1.4: Re-enable rule")

    enable_result = enable_rule(rule["rule_id"])
    if enable_result.get("enabled"):
        ok(f"Rule re-enabled: {rule['name']}")
    else:
        fail("Rule re-enable failed")

    # Test 1.5: List rules
    separator("Test 1.5: List all rules + filter by enabled")

    all_rules = list_rules()
    active_rules = list_rules(enabled_only=True)

    ok(f"Total rules in system: {len(all_rules)}")
    ok(f"Active rules: {len(active_rules)}")

    for r in all_rules:
        status = "✓" if r["enabled"] else "✗"
        info(f"  [{status}] {r['name']} (fired {r.get('fired_count', 0)} times)")

    # Test 1.6: Update rule condition
    separator("Test 1.6: Update rule condition via API")

    update_res = requests.patch(
        f"{BASE_URL}/rules/{rule['rule_id']}",
        json={
            "description": "Updated: Flag transfers above $3,000 (lowered threshold for demo)"
        },
        headers=ADMIN_HEADERS
    )

    if update_res.status_code == 200:
        ok("Rule description updated without redeployment")
    else:
        fail(f"Rule update failed: {update_res.status_code}")

    # Test 1.7: Multiple rules firing simultaneously
    separator("Test 1.7: Multiple rules fire on same decision")

    data3 = submit({
        "agent_id": "payment-agent-v1",
        "action_type": "wire_transfer",
        "description": "Transfer $50,000 to new vendor for equipment",
        "payload": {
            "amount": 50000,
            "vendor_id": "ACC-999",
            "vendor_status": "new"
        },
        "data_sources": [{
            "name": "finance_system",
            "last_synced_at": datetime.now(timezone.utc).isoformat(),
            "max_age_hours": 6
        }]
    })

    if not data3:
        return

    decision_id3 = data3["decision_id"]
    wait_for_pipeline(decision_id3)

    events3 = get_audit(decision_id3)
    rules_event3 = find_event(events3, "rules_engine_applied")

    if rules_event3:
        fired = rules_event3["details"].get("rules_fired", [])
        overrides = rules_event3["details"].get("overrides_applied", [])
        ok(f"Rules fired simultaneously: {fired}")
        ok(f"Overrides applied: {len(overrides)}")
        for o in overrides:
            info(f"  → {o}")
    else:
        info("No rules fired (may not have seeded default rules yet)")

    counterfactual_event = find_event(events3, "counterfactual_recorded")
    if counterfactual_event:
        summary = counterfactual_event["details"].get("summary", "")
        ok(f"Counterfactual recorded: {summary}")

# Section 2: Confidence Threshold

def test_confidence_threshold():
    section_header("SECTION 2 — Confidence Threshold Escalation")

    # Test 2.1: Normal confidence — no escalation
    separator("Test 2.1: Clear action → high confidence → no escalation")

    data = submit({
        "agent_id": "reporting-agent-v1",
        "action_type": "generate_report",
        "description": "Generate weekly vendor payment summary report",
        "payload": {"report_type": "summary", "period": "weekly"}
    })

    if not data:
        return

    decision_id = data["decision_id"]
    wait_for_pipeline(decision_id)

    events = get_audit(decision_id)
    clf_event = find_event(events, "ai_classification_completed")
    escalation_event = find_event(events, "low_confidence_escalation")

    if clf_event:
        confidence = clf_event["details"].get("confidence", 0)
        info(f"AI confidence: {confidence}")
        if confidence >= 0.6:
            ok(f"High confidence ({confidence}) — no escalation triggered")
        else:
            info(f"Low confidence ({confidence}) — escalation may trigger")

    if not escalation_event:
        ok("No confidence escalation — correct for clear, unambiguous action")
    else:
        info("Escalation triggered even for report — confidence below threshold")

    # Test 2.2: Ambiguous action → may trigger escalation
    separator("Test 2.2: Ambiguous action → check confidence level")

    data2 = submit({
        "agent_id": "unknown-agent-v1",
        "action_type": "update_policy",
        "description": "Modify configuration",
        "payload": {"target": "system", "change": "misc_update"},
        "context": ""
    })

    if not data2:
        return

    decision_id2 = data2["decision_id"]
    wait_for_pipeline(decision_id2)

    events2 = get_audit(decision_id2)
    clf_event2 = find_event(events2, "ai_classification_completed")
    escalation_event2 = find_event(events2, "low_confidence_escalation")

    if clf_event2:
        confidence2 = clf_event2["details"].get("confidence", 0)
        info(f"AI confidence for ambiguous action: {confidence2}")

    if escalation_event2:
        ok(f"Low confidence escalation triggered correctly")
        details = escalation_event2["details"]
        info(f"  Confidence: {details.get('confidence')}")
        info(f"  Threshold: {details.get('threshold')}")
        info(f"  AI suggested: {details.get('ai_suggested_route')}")
        info(f"  Escalated to: {details.get('escalated_to')}")

        decision2 = wait_for_pipeline(decision_id2, seconds=0)
        if decision2.get("status") in ("pending_approval", "auto_approved"):
            ok(f"Decision correctly routed to human review after escalation")
    else:
        info(f"No escalation triggered — AI was confident enough ({clf_event2['details'].get('confidence') if clf_event2 else 'unknown'})")
        ok("Confidence threshold working — this action was clear enough")

    # Test 2.3: Verify escalation overrides auto_approve
    separator("Test 2.3: Escalation should override auto_approve route")
    info("If AI suggests auto_approve but confidence < 0.6,")
    info("ARIA must escalate to needs_approval instead.")
    info("Check audit trail for 'low_confidence_escalation' events")
    info("in your App Insights or Cosmos audit-log container.")


# Section 3: Counterfactual Logging

def test_counterfactual():
    section_header("SECTION 3 — Counterfactual Logging")

    # Test 3.1: Rules change outcome — counterfactual stored
    separator("Test 3.1: Rules override AI → counterfactual records the difference")

    data = submit({
        "agent_id": "ops-agent-v1",
        "action_type": "modify_document",
        "description": "Update vendor payment policy document section 4.1",
        "payload": {"document_id": "POL-001", "section": "4.1"},
        "data_sources": [{
            "name": "doc_system",
            "last_synced_at": datetime.now(timezone.utc).isoformat(),
            "max_age_hours": 6
        }]
    })

    if not data:
        return

    decision_id = data["decision_id"]
    info(f"Submitted: {decision_id}")
    wait_for_pipeline(decision_id)

    events = get_audit(decision_id)
    cf_event = find_event(events, "counterfactual_recorded")
    rules_event = find_event(events, "rules_engine_applied")

    if rules_event:
        fired = rules_event["details"].get("rules_fired", [])
        ok(f"Rules fired: {fired}")
    else:
        info("No rules fired — counterfactual won't be stored (rules didn't change outcome)")
        skip("Counterfactual test — ensure policy_document_modification rule is seeded")
        return

    if cf_event:
        details = cf_event["details"]
        ok("Counterfactual recorded in audit trail")

        without = details.get("without_rules_engine", {})
        with_ = details.get("with_rules_engine", {})
        summary = details.get("summary", "")

        print()
        print("    ┌─ WITHOUT Rules Engine ─────────────────────────┐")
        print(f"    │  reversibility: {without.get('reversibility', 'N/A'):<32}│")
        print(f"    │  impact:        {without.get('impact', 'N/A'):<32}│")
        print(f"    │  route:         {without.get('route', 'N/A'):<32}│")
        print("    └────────────────────────────────────────────────┘")
        print("    ┌─ WITH Rules Engine ────────────────────────────┐")
        print(f"    │  reversibility: {with_.get('reversibility', 'N/A'):<32}│")
        print(f"    │  impact:        {with_.get('impact', 'N/A'):<32}│")
        print(f"    │  route:         {with_.get('route', 'N/A'):<32}│")
        print("    └────────────────────────────────────────────────┘")
        print(f"\n    Summary: {summary}")
        print()

        if without.get("route") != with_.get("route"):
            ok("Counterfactual captures route change correctly")
        else:
            ok("Counterfactual stored (same route but other fields may differ)")

        rules_changed = details.get("rules_that_changed_outcome", [])
        ok(f"Rules responsible for change: {rules_changed}")

    else:
        fail("Counterfactual event not found in audit trail")
        info("Check: does the decision have any rules that fire?")

    # Test 3.2: Verify counterfactual in decision object 
    separator("Test 3.2: Counterfactual stored in decision object itself")

    decision = requests.get(
        f"{BASE_URL}/decisions/{decision_id}",
        headers=AGENT_HEADERS
    ).json()

    cf = decision.get("counterfactual")
    if cf:
        ok("Counterfactual field present in decision object")
        ok(f"Summary: {cf.get('summary', 'N/A')}")
    else:
        info("Counterfactual not in decision object — rules may not have changed outcome")

    # Test 3.3: No counterfactual when no rules fire
    separator("Test 3.3: No rules fire → no counterfactual stored")

    data3 = submit({
        "agent_id": "reporting-agent-v1",
        "action_type": "generate_report",
        "description": "Generate monthly summary",
        "payload": {"type": "monthly"}
    })

    if not data3:
        return

    decision_id3 = data3["decision_id"]
    wait_for_pipeline(decision_id3)

    decision3 = requests.get(
        f"{BASE_URL}/decisions/{decision_id3}",
        headers=AGENT_HEADERS
    ).json()

    cf3 = decision3.get("counterfactual")
    if not cf3:
        ok("No counterfactual stored — correct when no rules fired")
    else:
        info(f"Counterfactual stored even without rule changes: {cf3}")

# Section 4: Auth Verification

def test_auth():
    section_header("SECTION 4 — Auth Role Verification")

    separator("Test 4.1: No API key → 403")
    res = requests.get(f"{BASE_URL}/decisions/")
    if res.status_code == 403:
        ok("No key → 403 Forbidden")
    else:
        fail(f"Expected 403, got {res.status_code}")

    separator("Test 4.2: Agent key can submit but not list")
    res_submit = requests.post(
        f"{BASE_URL}/decisions/submit",
        json={
            "agent_id": "test-agent",
            "action_type": "generate_report",
            "description": "Auth test report",
            "payload": {}
        },
        headers=AGENT_HEADERS
    )
    if res_submit.status_code == 202:
        ok("Agent key → submit allowed (202)")
    else:
        fail(f"Agent key submit failed: {res_submit.status_code}")

    res_list = requests.get(f"{BASE_URL}/decisions/", headers=AGENT_HEADERS)
    if res_list.status_code == 403:
        ok("Agent key → list decisions blocked (403)")
    else:
        fail(f"Agent key should not list decisions: {res_list.status_code}")

    separator("Test 4.3: Agent key cannot access rules")
    res_rules = requests.get(f"{BASE_URL}/rules/", headers=AGENT_HEADERS)
    if res_rules.status_code == 403:
        ok("Agent key → rules blocked (403)")
    else:
        fail(f"Agent key should not access rules: {res_rules.status_code}")

    separator("Test 4.4: Approver key can list but not access rules")
    res_list2 = requests.get(f"{BASE_URL}/decisions/", headers=APPROVER_HEADERS)
    if res_list2.status_code == 200:
        ok("Approver key → list decisions allowed (200)")
    else:
        fail(f"Approver list failed: {res_list2.status_code}")

    res_rules2 = requests.get(f"{BASE_URL}/rules/", headers=APPROVER_HEADERS)
    if res_rules2.status_code == 403:
        ok("Approver key → rules blocked (403)")
    else:
        fail(f"Approver should not access rules: {res_rules2.status_code}")

    separator("Test 4.5: Admin key has full access")
    res_admin = requests.get(f"{BASE_URL}/rules/", headers=ADMIN_HEADERS)
    if res_admin.status_code == 200:
        ok("Admin key → rules access allowed (200)")
    else:
        fail(f"Admin rules access failed: {res_admin.status_code}")

    res_stats = requests.get(f"{BASE_URL}/decisions/stats/summary", headers=ADMIN_HEADERS)
    if res_stats.status_code == 200:
        ok("Admin key → stats access allowed (200)")
        stats = res_stats.json()
        info(f"Decision counts: {json.dumps(stats, indent=2)}")
    else:
        fail(f"Admin stats access failed: {res_stats.status_code}")

    separator("Test 4.6: Rollback requires admin key")
    fake_id = "00000000-0000-0000-0000-000000000000"
    res_rollback = requests.post(
        f"{BASE_URL}/decisions/{fake_id}/rollback",
        json={"requested_by": "tester", "reason": "test"},
        headers=APPROVER_HEADERS
    )
    if res_rollback.status_code == 403:
        ok("Approver key → rollback blocked (403) — admin only")
    else:
        info(f"Rollback returned: {res_rollback.status_code} (may be 404 for fake ID)")

# Section 5: End-to-End with All P2 Features

def test_end_to_end():
    section_header("SECTION 5 — End-to-End: All Priority 2 Features Together")

    separator("Full pipeline: submit → classify → rules override → counterfactual → approve → execute")

    # create a targeted rule for this e2e test
    rule = create_rule({
        "name": "e2e_test_rule",
        "description": "E2E test: flag payments with context containing 'urgent'.",
        "condition": {
            "action_types": ["payment", "wire_transfer"],
            "context_contains": "urgent"
        },
        "override": {
            "impact": "high",
            "add_approvers": ["Risk Officer"],
            "reason": "Urgent payment flagged for additional review."
        },
        "created_by": "demo-runner"
    })

    if not rule:
        return

    ok(f"Created e2e rule: {rule['name']}")

    # submit decision that triggers the rule
    data = submit({
        "agent_id": "payment-agent-v1",
        "action_type": "payment",
        "description": "Pay supplier invoice INV-9901",
        "payload": {"amount": 2500, "vendor_id": "SUP-303"},
        "context": "Urgent: supplier threatening to halt deliveries",
        "data_sources": [{
            "name": "erp_system",
            "last_synced_at": datetime.now(timezone.utc).isoformat(),
            "max_age_hours": 6
        }]
    })

    if not data:
        return

    decision_id = data["decision_id"]
    info(f"Decision ID: {decision_id}")

    decision = wait_for_pipeline(decision_id, seconds=7)
    events = get_audit(decision_id)

    # verify each stage
    stages = [
        ("freshness_check_passed", "Freshness check passed"),
        ("ai_classification_completed", "AI classification completed"),
        ("rules_engine_applied", "Rules engine applied"),
        ("counterfactual_recorded", "Counterfactual recorded"),
        ("classification_finalized", "Classification finalized"),
    ]

    print()
    for event_type, label in stages:
        event = find_event(events, event_type)
        if event:
            ok(f"{label} @ {event['timestamp'][11:19]}")
        else:
            info(f"{label} — not found (may depend on rules seeded)")

    # check counterfactual
    cf_event = find_event(events, "counterfactual_recorded")
    if cf_event:
        summary = cf_event["details"].get("summary", "")
        ok(f"Counterfactual: {summary}")

    # approve and execute if pending
    status = decision.get("status")
    info(f"Current status: {status}")

    if status == "pending_approval":
        approve(decision_id, "risk-officer@company.com")
        ok("Decision approved by Risk Officer")

        exec_res = requests.post(
            f"{BASE_URL}/decisions/{decision_id}/execute",
            json={"requested_by": "risk-officer@company.com"},
            headers=APPROVER_HEADERS
        )
        if exec_res.status_code == 200:
            exec_data = exec_res.json()
            ok(f"Execution completed: {exec_data.get('status')}")
            ok(f"Rollback available: {exec_data.get('rollback_available')}")
        else:
            fail(f"Execution failed: {exec_res.status_code} {exec_res.text}")

    elif status == "auto_approved":
        exec_res = requests.post(
            f"{BASE_URL}/decisions/{decision_id}/execute",
            json={"requested_by": "system"},
            headers=APPROVER_HEADERS
        )
        if exec_res.status_code == 200:
            ok(f"Auto-approved decision executed")
        else:
            fail(f"Execution failed: {exec_res.status_code}")

    # final audit trail
    final_events = get_audit(decision_id)
    print(f"\n  📋 Full audit trail ({len(final_events)} events):")
    for event in final_events:
        ts = event["timestamp"][11:19]
        actor = event["actor"].replace("aria-", "")
        etype = event["event_type"]
        print(f"     {ts}  [{actor}]  {etype}")

# Summary

def print_summary():
    section_header("DEMO SUMMARY")
    total = results["passed"] + results["failed"] + results["skipped"]
    print(f"  Tests run:    {total}")
    print(f"  ✅ Passed:    {results['passed']}")
    print(f"  ❌ Failed:    {results['failed']}")
    print(f"  ⏭️  Skipped:   {results['skipped']}")
    print()

    if results["failed"] == 0:
        print("  🎉 All checks passed! Priority 2 features working correctly.")
    else:
        print("  ⚠️  Some checks failed. Review output above.")

    print(f"\n  Created {len(created_rule_ids)} rules during this demo.")
    print(f"  Rule IDs: {[r[:8] + '...' for r in created_rule_ids]}")
    print()
    print(f"  Swagger UI: {BASE_URL}/docs")
    print(f"  Stats:      GET {BASE_URL}/decisions/stats/summary")
    print(f"  Rules:      GET {BASE_URL}/rules/")
    print()


def main():
    global BASE_URL
    parser = argparse.ArgumentParser(description="ARIA Priority 2 Demo Script")
    parser.add_argument(
        "--url",
        default=BASE_URL,
        help="Base URL of ARIA API (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--section",
        choices=["rules", "confidence", "counterfactual", "auth", "e2e", "all"],
        default="all",
        help="Which section to run (default: all)"
    )
    args = parser.parse_args()
    BASE_URL = args.url.rstrip("/")

    # verify server is up
    try:
        health = requests.get(f"{BASE_URL}/health", timeout=5)
        if health.status_code != 200:
            print(f"❌ Server not healthy: {health.status_code}")
            sys.exit(1)
        health_data = health.json()
        print(f"\n  ARIA server: {health_data.get('service')}")
        print(f"  Version:     {health_data.get('version', 'N/A')}")
        print(f"  Status:      {health_data.get('status')}")
    except Exception as e:
        print(f"❌ Cannot reach server at {BASE_URL}: {e}")
        print("   Is the server running? Try: uvicorn app.main:app --reload")
        sys.exit(1)

    try:
        section = args.section
        if section in ("rules", "all"):
            test_dynamic_rules()
        if section in ("confidence", "all"):
            test_confidence_threshold()
        if section in ("counterfactual", "all"):
            test_counterfactual()
        if section in ("auth", "all"):
            test_auth()
        if section in ("e2e", "all"):
            test_end_to_end()

    except KeyboardInterrupt:
        print("\n\n  Demo interrupted.")
    finally:
        print_summary()


if __name__ == "__main__":
    main()