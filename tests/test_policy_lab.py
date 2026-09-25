import copy
import json
import os
import unittest
from unittest.mock import patch
os.environ["SKILLFORGE_DB"] = ":memory:"
from fastapi.testclient import TestClient
from backend.app import Database, PolicyError, load_case
from backend.engine import WorkflowService, execute, digest
from backend.governance import PolicyLab
from backend.api import create_app


class PolicyLabTests(unittest.TestCase):
    def setUp(self):
        self.db = Database()
        self.service = WorkflowService(self.db)
        self.lab = PolicyLab(self.service)
        self.service.discover()
        self.candidate = self.service.compile()
        self.service.verify(self.candidate["id"])
        self.service.activate(self.candidate["id"])

    def tearDown(self):
        self.db.conn.close()

    def test_end_to_end_policy_change_and_explicit_repromotion(self):
        before_counts = {t: self.db.one(f"SELECT COUNT(*) FROM {t}")[0] for t in ("orders", "refunds", "approvals", "runs")}
        review = self.lab.preview(self.candidate["id"], 300000)
        self.assertTrue(review["passed"])
        self.assertEqual(review["case_count"], 42)
        self.assertEqual(review["unsafe_count"], 0)
        row = next(r for r in review["cases"] if r["case_id"] == "350k-refund")
        self.assertEqual(row["before"]["actual"], "SUCCEEDED")
        self.assertEqual(row["after"]["actual"], "AWAITING_APPROVAL")
        self.assertEqual(before_counts, {t: self.db.one(f"SELECT COUNT(*) FROM {t}")[0] for t in before_counts})
        self.lab.apply(review["id"])
        self.assertEqual(self.service.get(self.candidate["id"])["state"], "STALE")
        load_case(self.db, {"order_id": "changed-order", "amount_krw": 350000})
        self.assertEqual(execute(self.db, "changed-order", artifact=self.candidate["artifact"])["reason_code"], "STALE_POLICY")
        new = self.lab.rebase(self.candidate["id"])
        self.assertEqual(self.lab.rebase(self.candidate["id"])["id"], new["id"])
        self.assertEqual(new["artifact"]["source_trace_ids"], self.candidate["artifact"]["source_trace_ids"])
        self.assertEqual(new["artifact"]["parent_artifact_hash"], self.candidate["artifact_hash"])
        with self.assertRaises(PolicyError):
            self.service.activate(new["id"])
        verified = self.service.verify(new["id"])
        self.assertTrue(verified["report"]["passed"])
        self.assertEqual(len(verified["report"]["boundary_checks"]), 6)
        self.service.activate(new["id"])
        r = self.service.run("changed-order")
        self.assertEqual((r["mode"], r["status"]), ("workflow", "AWAITING_APPROVAL"))
        approval = self.db.create_approval("operator-1", "changed-order", 350000)
        r = self.service.run("changed-order", approval_id=approval["approval_id"], operator_id="operator-1")
        self.assertEqual(r["status"], "SUCCEEDED")
        self.assertEqual(self.db.one("SELECT COUNT(*) FROM refunds")[0], 1)

    def test_stale_preview_cannot_overwrite_newer_policy(self):
        a = self.lab.preview(self.candidate["id"], 300000)
        b = self.lab.preview(self.candidate["id"], 400000)
        self.lab.apply(a["id"])
        with self.assertRaises(PolicyError) as ctx:
            self.lab.apply(b["id"])
        self.assertEqual(ctx.exception.code, "STALE_PREVIEW")
        self.assertTrue(self.lab.apply(a["id"])["applied"])
        self.assertEqual(self.lab.current()["approval_limit_krw"], 300000)

    def test_low_limit_revalidation_uses_current_expected_outcomes(self):
        review = self.lab.preview(self.candidate["id"], 50000)
        self.lab.apply(review["id"])
        candidate = self.lab.rebase(self.candidate["id"])
        verified = self.service.verify(candidate["id"])
        self.assertTrue(verified["report"]["passed"])
        self.assertTrue(any(c["expected"] == "AWAITING_APPROVAL" for c in verified["report"]["cases"]))

    def test_old_approval_does_not_authorize_new_policy(self):
        approval = self.db.create_approval("operator-1", "order-002", 600000)
        review = self.lab.preview(self.candidate["id"], 300000)
        self.lab.apply(review["id"])
        r = execute(self.db, "order-002", approval_id=approval["approval_id"], operator_id="operator-1")
        self.assertNotEqual(r["status"], "SUCCEEDED")
        self.assertEqual(self.db.one("SELECT COUNT(*) FROM refunds")[0], 0)

    def test_changed_trace_value_rejected_even_with_valid_provenance(self):
        with self.db.transaction():
            for row in self.db.conn.execute("SELECT run_id,seq,payload FROM events WHERE kind='tool.requested'").fetchall():
                payload = json.loads(row["payload"])
                if payload["tool"] == "issue_refund":
                    payload["args"]["quote_id"] = "forged-quote"
                    self.db.conn.execute("UPDATE events SET payload=? WHERE run_id=? AND seq=?", (json.dumps(payload), row["run_id"], row["seq"]))
        with self.assertRaises(PolicyError):
            self.service.compile()

    def test_compiler_does_not_use_manual_template(self):
        with patch("backend.engine.manual_workflow", side_effect=AssertionError("template used")):
            item = self.service.compile()
        self.assertEqual(item["artifact"]["steps"][4]["args"]["quote_id"], {"ref": "steps.quote.quote_id"})

    def test_missing_completion_rejected(self):
        with self.db.transaction():
            self.db.conn.execute("DELETE FROM events WHERE kind='tool.completed'")
        with self.assertRaises(PolicyError):
            self.service.compile()

    def test_operator_auth_and_strict_input(self):
        with patch.dict(os.environ, {"SKILLFORGE_OPERATOR_SESSION": "policy-test-only"}):
            with TestClient(create_app(self.db)) as client:
                body = {"workflow_id": self.candidate["id"], "approval_limit_krw": 300000}
                self.assertEqual(client.post("/api/policy/preview", json=body).status_code, 403)
                headers = {"X-Operator-Session": "policy-test-only"}
                for invalid in (True, "300000", 0, 1):
                    self.assertEqual(client.post("/api/policy/preview", json={**body, "approval_limit_krw": invalid}, headers=headers).status_code, 422)
                response = client.post("/api/policy/preview", json=body, headers=headers)
                self.assertEqual(response.status_code, 200)
                rid = response.json()["id"]
                self.assertEqual(client.post(f"/api/policy/reviews/{rid}/apply", json={}).status_code, 403)
                self.assertEqual(client.post(f"/api/policy/reviews/{rid}/apply", json={}, headers=headers).status_code, 200)
                self.assertEqual(client.post(f'/api/workflows/{self.candidate["id"]}/rebase', json={}, headers=headers).status_code, 200)
