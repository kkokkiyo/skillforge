import json, os, time, unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app import Database
from backend.api import create_app
from backend.router import route_text


class APITests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(
            os.environ, {"SKILLFORGE_OPERATOR_SESSION": "isolated-test-session"}
        )
        self.env.start()
        self.db = Database()
        self.app = create_app(self.db)
        self.client = TestClient(self.app)
        self.headers = {"X-Operator-Session": "isolated-test-session"}

    def tearDown(self):
        self.client.close()
        self.env.stop()

    def finish(self, response):
        self.assertEqual(response.status_code, 202, response.text)
        rid = response.json()["run_id"]
        for _ in range(200):
            r = self.client.get("/api/runs/" + rid).json()
            if r["status"] not in {"CREATED", "RUNNING"}:
                return r
            time.sleep(0.01)
        self.fail("job did not terminate")

    def test_sse_reconnect_and_request_idempotence(self):
        body = {"order_id": "order-001", "request_id": "request-normal-1"}
        first = self.client.post("/api/runs", json=body)
        result = self.finish(first)
        self.assertEqual(result["status"], "SUCCEEDED")
        again = self.client.post("/api/runs", json=body)
        self.assertEqual(again.json()["run_id"], result["run_id"])
        self.assertEqual(
            self.client.post(
                "/api/runs", json={**body, "order_id": "order-002"}
            ).status_code,
            409,
        )
        stream = self.client.get(
            "/api/runs/" + result["run_id"] + "/events",
            headers={"Accept": "text/event-stream", "Last-Event-ID": "5"},
        )
        self.assertIn("event: done", stream.text)
        self.assertNotIn("id: 1\n", stream.text)
        self.assertEqual(self.db.one("SELECT COUNT(*) FROM refunds")[0], 1)

    def test_typed_inputs_and_auth_fail_closed(self):
        self.assertEqual(
            self.client.post(
                "/api/runs", json={"order_id": 4, "request_id": "abcdefgh"}
            ).status_code,
            422,
        )
        self.assertEqual(
            self.client.post(
                "/api/runs",
                json={
                    "order_id": "order-001",
                    "request_id": "abcdefgh",
                    "approved": True,
                },
            ).status_code,
            422,
        )
        self.assertEqual(
            self.client.post(
                "/api/approvals",
                json={"order_id": "order-002", "amount_krw": 600000},
                headers={"X-Operator-Id": "operator-1"},
            ).status_code,
            403,
        )

    def test_live_text_ambiguity_never_calls_model(self):
        with patch("backend.router.NVIDIAClient") as model:
            r = self.finish(
                self.client.post(
                    "/api/runs",
                    json={
                        "text": "order-001 또는 order-002 환불",
                        "mode": "live",
                        "request_id": "ambiguous-request",
                    },
                )
            )
            self.assertEqual(r["status"], "NEEDS_INPUT")
            model.assert_not_called()
        self.assertEqual(self.db.one("SELECT COUNT(*) FROM refunds")[0], 0)

    def test_text_cannot_override_selected_order(self):
        r = self.finish(
            self.client.post(
                "/api/runs",
                json={
                    "order_id": "order-002",
                    "text": "order-001 환불",
                    "request_id": "mismatch-request",
                },
            )
        )
        self.assertEqual(r["reason_code"], "ORDER_SCOPE_MISMATCH")
        self.assertEqual(self.db.one("SELECT COUNT(*) FROM refunds")[0], 0)

    def test_natural_language_mock_and_unknown_intent(self):
        self.assertEqual(route_text("order-001 상태 알려줘")["intent"], "status")
        self.assertEqual(route_text("order-001 배송지 바꿔줘")["intent"], "unsupported")
        r = self.finish(
            self.client.post(
                "/api/runs",
                json={
                    "text": "order-001 반품한 상품 환불해주세요",
                    "request_id": "natural-language",
                },
            )
        )
        self.assertEqual(r["status"], "SUCCEEDED")
        self.assertEqual(r["common_routing_cost"]["model_calls"], 0)

    def test_registry_expected_hash_gate(self):
        s = self.app.state.service
        s.discover()
        w = s.compile()
        s.verify(w["id"])
        url = "/api/workflows/" + w["id"] + "/activate"
        self.assertEqual(
            self.client.post(
                url, json={"expected_hash": "0" * 64}, headers=self.headers
            ).status_code,
            409,
        )
        self.assertEqual(
            self.client.post(
                url, json={"expected_hash": w["artifact_hash"]}, headers=self.headers
            ).status_code,
            200,
        )

    def test_approval_real_http_resume(self):
        pending = self.finish(
            self.client.post(
                "/api/runs",
                json={"order_id": "order-002", "request_id": "pending-request"},
            )
        )
        self.assertEqual(pending["status"], "AWAITING_APPROVAL")
        approval = self.client.post(
            "/api/approvals",
            json={"order_id": "order-002", "amount_krw": 600000},
            headers=self.headers,
        ).json()
        resumed = self.finish(
            self.client.post(
                "/api/runs",
                json={
                    "order_id": "order-002",
                    "request_id": "resumed-request",
                    "approval_id": approval["approval_id"],
                },
                headers=self.headers,
            )
        )
        self.assertEqual(resumed["status"], "SUCCEEDED")


if __name__ == "__main__":
    unittest.main()
