import json, os, unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app import Database, Trace, Gateway, PolicyError
from backend.engine import execute, WorkflowService, manual_workflow, validate_workflow
from backend.api import create_app


class RecoveryTests(unittest.TestCase):
    def test_post_write_hold_blocks_later_mutation(self):
        db = Database()
        r = execute(db, "order-001", fault_verify=True)
        self.assertEqual(r["status"], "NEEDS_RECONCILIATION")
        hold = db.one(
            "SELECT * FROM reconciliation_holds WHERE order_id=?", ("order-001",)
        )
        self.assertIsNone(hold["resolved_by"])
        quote = db.one("SELECT id FROM quotes LIMIT 1")[0]
        with self.assertRaises(PolicyError) as caught:
            Gateway(db, Trace(db, "held-retry", "mock", "order-001")).call(
                "issue_refund",
                {
                    "order_id": "order-001",
                    "quote_id": quote,
                    "idempotency_key": "new-write",
                },
            )
        self.assertEqual(caught.exception.code, "RECONCILIATION_REQUIRED")
        self.assertEqual(db.one("SELECT COUNT(*) FROM refunds")[0], 1)

    def test_restart_retains_hold_and_same_request_id(self):
        db = Database()
        app = create_app(db)
        Trace(db, "interrupted-id", "live", "order-001")
        with db.transaction():
            db.conn.execute(
                "INSERT INTO api_requests VALUES (?,?,?)",
                ("interrupted-request", "payload", "interrupted-id"),
            )
        restarted = create_app(db)
        with TestClient(restarted) as client:
            result = client.get("/api/runs/interrupted-id").json()
            self.assertEqual(result["status"], "NEEDS_RECONCILIATION")
            self.assertEqual(db.one("SELECT COUNT(*) FROM refunds")[0], 0)
            self.assertEqual(
                client.post("/api/reconciliations/order-001/resolve").status_code, 403
            )
            with patch.dict(
                os.environ, {"SKILLFORGE_OPERATOR_SESSION": "operator-test"}
            ):
                resolved = client.post(
                    "/api/reconciliations/order-001/resolve",
                    headers={"X-Operator-Session": "operator-test"},
                )
                self.assertEqual(resolved.status_code, 200, resolved.text)
            self.assertEqual(db.one("SELECT COUNT(*) FROM refunds")[0], 0)

    def test_orphaned_request_is_terminal_without_replay(self):
        db = Database()
        create_app(db)
        with db.transaction():
            db.conn.execute(
                "INSERT INTO api_requests VALUES (?,?,?)",
                ("orphan-request", "payload", "never-started"),
            )
        client = TestClient(create_app(db))
        self.assertEqual(
            client.get("/api/runs/never-started").json()["reason_code"],
            "INTERRUPTED_BEFORE_EXECUTION",
        )

    def test_artifact_unknown_root_and_report_binding(self):
        db = Database()
        artifact = manual_workflow(db)
        artifact["python_code"] = "print(1)"
        with self.assertRaises(PolicyError):
            validate_workflow(artifact)
        service = WorkflowService(db)
        service.discover()
        w = service.compile()
        w = service.verify(w["id"])
        self.assertTrue(all(r["trace_complete"] for r in w["report"]["cases"]))
        report = w["report"]
        report["artifact_hash"] = "0" * 64
        with db.transaction():
            db.conn.execute(
                "UPDATE workflows SET report=? WHERE id=?",
                (json.dumps(report), w["id"]),
            )
        with self.assertRaises(PolicyError) as caught:
            service.activate(w["id"])
        self.assertEqual(caught.exception.code, "REPORT_BINDING_INVALID")
