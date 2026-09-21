import copy
import http.client
import json
import os
import secrets
import threading
import unittest
from unittest.mock import patch

os.environ["SKILLFORGE_DB"] = ":memory:"
from backend.app import (
    Database,
    Gateway,
    Trace,
    Outcome,
    PolicyError,
    independent_oracle,
    load_case,
    split_manifest,
)
from backend.engine import WorkflowService, execute, validate_workflow, manual_workflow
from backend import server


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.db = Database()
        self.service = WorkflowService(self.db)

    def tearDown(self):
        self.db.conn.close()

    def test_full_discover_verify_activate_reuse_and_stale(self):
        self.service.discover()
        candidate = self.service.compile()
        self.assertGreaterEqual(len(candidate["artifact"]["source_trace_ids"]), 5)
        with self.assertRaises(PolicyError):
            self.service.activate(candidate["id"])
        verified = self.service.verify(candidate["id"])
        self.assertEqual(verified["state"], "VERIFIED")
        self.assertTrue(all(c["passed"] for c in verified["report"]["cases"]))
        self.service.activate(candidate["id"])
        result = self.service.run("order-001")
        self.assertEqual(result["status"], "SUCCEEDED")
        self.assertEqual(result["mode"], "workflow")
        with self.db.transaction():
            self.db.conn.execute("UPDATE policies SET active=0")
            self.db.conn.execute("INSERT INTO policies VALUES ('new',500000,1)")
        self.assertEqual(self.service.get(candidate["id"])["state"], "STALE")

    def test_artifact_tamper_and_unsafe_reference_rejected(self):
        artifact = manual_workflow(self.db)
        artifact["steps"][4]["args"]["quote_id"] = {"ref": "input.order_id"}
        with self.assertRaises(PolicyError):
            validate_workflow(artifact)
        self.service.discover()
        item = self.service.compile()
        self.service.verify(item["id"])
        self.service.activate(item["id"])
        artifact = item["artifact"]
        artifact["name"] = "tampered"
        with self.db.transaction():
            self.db.conn.execute(
                "UPDATE workflows SET artifact=? WHERE id=?",
                (json.dumps(artifact), item["id"]),
            )
        with self.assertRaises(PolicyError):
            self.service.run("order-001")

    def test_compiler_rejects_bad_provenance(self):
        self.service.discover()
        with self.db.transaction():
            self.db.conn.execute(
                "UPDATE events SET provenance='{}' WHERE kind='tool.requested'"
            )
        with self.assertRaises(PolicyError):
            self.service.compile()

    def test_all_fixtures_oracle_and_amount_negative(self):
        for group in ("discovery", "validation", "test"):
            for case in split_manifest()[group]:
                db = Database()
                load_case(db, case)
                result = execute(db, case["order_id"])
                self.assertEqual(result["status"], case["expected"])
                self.assertTrue(
                    independent_oracle(db, case["order_id"], case["expected"])[
                        "passed"
                    ],
                    case["id"],
                )
                if result["status"] == "SUCCEEDED":
                    db.conn.execute(
                        "UPDATE refunds SET amount_krw=1 WHERE order_id=?",
                        (case["order_id"],),
                    )
                    db.conn.commit()
                    self.assertFalse(
                        independent_oracle(db, case["order_id"], "SUCCEEDED")["passed"]
                    )
                db.conn.close()

    def test_approval_consumption_rolls_back_on_write_failure(self):
        a = self.db.create_approval("operator-1", "order-002", 600000)
        self.db.fail_refund_insert = True
        r = execute(
            self.db, "order-002", approval_id=a["approval_id"], operator_id="operator-1"
        )
        self.assertEqual(r["status"], "NEEDS_RECONCILIATION")
        self.assertIsNone(
            self.db.one(
                "SELECT consumed_at FROM approvals WHERE id=?", (a["approval_id"],)
            )[0]
        )
        self.assertEqual(self.db.one("SELECT COUNT(*) FROM refunds")[0], 0)

    def test_real_model_loop_with_fake_transport(self):
        class Client:
            model = "fake-transport"

            def __init__(self):
                self.index = 0

            def complete(inner, messages, tools, timeout):
                names = [
                    "get_order",
                    "get_return_status",
                    "get_refund_policy",
                    "quote_refund",
                    "issue_refund",
                    "verify_refund",
                ]
                name = names[inner.index]
                inner.index += 1
                args = {"order_id": "order-001"}
                if name == "issue_refund":
                    args["quote_id"] = json.loads(messages[-1]["content"])["quote_id"]
                return {
                    "choices": [
                        {
                            "message": {
                                "content": None,
                                "tool_calls": [
                                    {
                                        "id": str(inner.index),
                                        "type": "function",
                                        "function": {
                                            "name": name,
                                            "arguments": json.dumps(args),
                                        },
                                    }
                                ],
                            },
                            "finish_reason": "tool_calls",
                        }
                    ],
                    "usage": {"total_tokens": 10},
                }

        result = execute(self.db, "order-001", mode="live", model_client=Client())
        self.assertEqual(result["status"], "SUCCEEDED")
        self.assertEqual(result["metrics"]["model_calls"], 6)
        self.assertEqual(result["metrics"]["tokens"], 60)

    def test_model_cannot_grant_approval_authority(self):
        class Client:
            def complete(self, *args):
                return {
                    "choices": [
                        {
                            "message": {
                                "tool_calls": [
                                    {
                                        "id": "1",
                                        "function": {
                                            "name": "issue_refund",
                                            "arguments": json.dumps(
                                                {
                                                    "order_id": "order-002",
                                                    "quote_id": "fake",
                                                    "operator_id": "operator-1",
                                                }
                                            ),
                                        },
                                    }
                                ]
                            }
                        }
                    ]
                }

        r = execute(self.db, "order-002", mode="live", model_client=Client())
        self.assertEqual(r["status"], "DENIED")
        self.assertEqual(self.db.one("SELECT COUNT(*) FROM refunds")[0], 0)


class HTTPTests(unittest.TestCase):
    def setUp(self):
        server.DB = Database()
        self.httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join()
        server.DB.conn.close()

    def post(self, path, body, session=None):
        connection = http.client.HTTPConnection(
            "127.0.0.1", self.httpd.server_port, timeout=5
        )
        headers = {"Content-Type": "application/json"}
        if session is not None:
            headers["X-Operator-Session"] = session
        connection.request("POST", path, json.dumps(body), headers)
        response = connection.getresponse()
        data = json.loads(response.read())
        connection.close()
        return response.status, data

    def test_operator_fail_closed_and_valid_approval(self):
        body = {"order_id": "order-002", "amount_krw": 600000}
        with patch.dict(os.environ, {"SKILLFORGE_OPERATOR_SESSION": ""}):
            for credential in (None, "", "local-demo-session"):
                self.assertEqual(self.post("/api/approvals", body, credential)[0], 403)
        secret = secrets.token_urlsafe(24)
        with patch.dict(os.environ, {"SKILLFORGE_OPERATOR_SESSION": secret}):
            self.assertEqual(self.post("/api/approvals", body, "wrong")[0], 403)
            status, a = self.post("/api/approvals", body, secret)
            self.assertEqual(status, 201)
            self.assertEqual(
                self.post(
                    "/api/runs",
                    {"order_id": "order-002", "approval_id": a["approval_id"]},
                )[0],
                403,
            )
            status, r = self.post(
                "/api/runs",
                {"order_id": "order-002", "approval_id": a["approval_id"]},
                secret,
            )
            self.assertEqual(r["status"], "SUCCEEDED")

    def test_bad_body_and_traversal(self):
        self.assertEqual(self.post("/api/runs", [])[0], 422)
        self.assertEqual(self.post("/api/runs", {"order_id": 2})[0], 422)
        c = http.client.HTTPConnection("127.0.0.1", self.httpd.server_port)
        c.request("GET", "/../README.md")
        r = c.getresponse()
        r.read()
        self.assertEqual(r.status, 404)
        c.close()


if __name__ == "__main__":
    unittest.main()
