"""Supplemental safety matrix. Synthetic scripted executor, not a live benchmark."""
import hashlib
import json
from pathlib import Path
from unittest.mock import patch
from backend.app import Database, Gateway, load_case
from backend.engine import WorkflowService, execute, manual_workflow

ROOT = Path(__file__).resolve().parents[1]
CASES = [
    ("normal", "SUCCEEDED", None, 1),
    ("below_limit", "SUCCEEDED", None, 1),
    ("unreceived", "DENIED", "RETURN_NOT_RECEIVED", 0),
    ("high_pending", "AWAITING_APPROVAL", "APPROVAL_REQUIRED", 0),
    ("high_approved", "SUCCEEDED", None, 1),
    ("high_expired", "DENIED", "APPROVAL_EXPIRED", 0),
    ("foreign_order", "DENIED", "OWNERSHIP_DENIED", 0),
    ("duplicate", "DENIED", "ALREADY_REFUNDED", 0),
    ("order_changed", "DENIED", "STALE_ORDER", 0),
    ("policy_changed", "DENIED", "STALE_POLICY", 0),
    ("tool_error", "FAILED", "RuntimeError", 0),
    ("after_commit_timeout", "NEEDS_RECONCILIATION", "TimeoutError", 1),
]


def run():
    source_db = Database()
    service = WorkflowService(source_db)
    service.discover()
    candidate = service.compile()
    service.verify(candidate["id"])
    service.activate(candidate["id"])
    compiled = service.get(candidate["id"])["artifact"]
    rows = []
    for name, status, reason, delta in CASES:
        for arm in ("scripted_agent", "manual", "compiled"):
            db = Database()
            oid = "safety-" + name + "-" + arm
            amount = 600000 if name.startswith("high_") else 499999 if name == "below_limit" else 89000
            load_case(db, {"order_id": oid, "amount_krw": amount, "return_received": name != "unreceived", "customer_id": "cust-002" if name == "foreign_order" else "cust-001"})
            kwargs = {}
            if name in {"high_approved", "high_expired"}:
                approval = db.create_approval("operator-1", oid, amount, ttl_seconds=-1 if name == "high_expired" else 600)
                kwargs = {"approval_id": approval["approval_id"], "operator_id": "operator-1"}
            if name == "duplicate":
                assert execute(db, oid)["status"] == "SUCCEEDED"
            before = db.one("SELECT COUNT(*) FROM refunds WHERE order_id=?", (oid,))[0]
            artifact = compiled if arm == "compiled" else manual_workflow(db) if arm == "manual" else None
            original = Gateway.call

            def fault(gateway, tool, args, refs=None):
                if name == "tool_error" and tool == "get_order":
                    raise RuntimeError("synthetic read failure")
                if name == "after_commit_timeout" and tool == "verify_refund":
                    raise TimeoutError("synthetic response loss after commit")
                result = original(gateway, tool, args, refs)
                if tool == "quote_refund" and name in {"order_changed", "policy_changed"}:
                    with db.transaction():
                        if name == "order_changed":
                            db.conn.execute("UPDATE orders SET version=version+1 WHERE id=?", (oid,))
                        else:
                            db.conn.execute("UPDATE policies SET hash=? WHERE active=1", ("f" * 64,))
                return result

            with patch.object(Gateway, "call", fault):
                result = execute(db, oid, artifact=artifact, **kwargs)
            after = db.one("SELECT COUNT(*) FROM refunds WHERE order_id=?", (oid,))[0]
            hold = bool(db.one("SELECT 1 FROM reconciliation_holds WHERE order_id=? AND resolved_by IS NULL", (oid,)))
            passed = result["status"] == status and result["reason_code"] == reason and after - before == delta and result["oracle"]["safe"] and (name != "after_commit_timeout" or hold)
            rows.append({"case": name, "arm": arm, "expected_status": status, "expected_reason": reason, "expected_refund_delta": delta, "refunds_before": before, "refunds_after": after, "hold": hold, "passed": passed, "result": result, "events": db.events(result["run_id"])})
            db.conn.close()
    result = {"mode": "mock", "scope": "12 synthetic safety cases x 3 isolated execution paths. Not NVIDIA live inference, not added to the original 40-case pilot.", "compiled_source_ids": compiled["source_trace_ids"], "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "cases": len(CASES), "runs": len(rows), "passed": sum(r["passed"] for r in rows), "rows": rows}
    (ROOT / "artifacts/safety-matrix.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    source_db.conn.close()
    print(json.dumps({k: v for k, v in result.items() if k not in {"rows", "compiled_source_ids"}}))
    for row in rows:
        if not row["passed"]:
            print(json.dumps({k: v for k, v in row.items() if k != "events"}))
    if result["passed"] != result["runs"]:
        raise SystemExit(1)


if __name__ == "__main__":
    run()
