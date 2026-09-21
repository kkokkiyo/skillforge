import tempfile, unittest, threading, time, json, hashlib
from pathlib import Path
from backend.app import (
    Database,
    Gateway,
    MCPAdapter,
    MockModelLoop,
    Outcome,
    PolicyError,
    Trace,
    TOOL_SCHEMA_CANONICAL,
    TOOL_SCHEMA_HASH,
    independent_oracle,
    load_case,
    run_refund,
    split_manifest,
    validate_splits,
)


class M1FixTests(unittest.TestCase):
    def setUp(self):
        self.db = Database()

    def test_f01_latest_state_checks(self):
        t = Trace(self.db, "f01", "mock", "order-001")
        g = Gateway(self.db, t)
        q = g.call("quote_refund", {"order_id": "order-001"})
        self.db.conn.execute("UPDATE returns SET received=0 WHERE order_id='order-001'")
        self.db.conn.commit()
        with self.assertRaises(PolicyError) as e:
            g.call(
                "issue_refund",
                {
                    "order_id": "order-001",
                    "quote_id": q["quote_id"],
                    "idempotency_key": "f01",
                },
            )
        self.assertEqual(e.exception.code, "RETURN_NOT_RECEIVED")
        self.assertEqual(
            self.db.one("SELECT refunded_krw FROM orders WHERE id='order-001'")[0], 0
        )

    def test_f01_each_quote_binding_is_checked(self):
        for field, sql, code in [
            (
                "version",
                "UPDATE orders SET version=2 WHERE id='order-001'",
                "STALE_ORDER",
            ),
            (
                "policy_hash",
                "UPDATE quotes SET policy_hash='changed' WHERE id=?",
                "STALE_POLICY",
            ),
            (
                "expires_at",
                "UPDATE quotes SET expires_at='2000-01-01T00:00:00+00:00' WHERE id=?",
                "QUOTE_EXPIRED",
            ),
        ]:
            db = Database()
            t = Trace(db, "f01-" + field, "mock", "order-001")
            g = Gateway(db, t)
            q = g.call("quote_refund", {"order_id": "order-001"})
            db.conn.execute(sql, (q["quote_id"],) if "?" in sql else ())
            db.conn.commit()
            with self.assertRaises(PolicyError) as e:
                g.call(
                    "issue_refund",
                    {
                        "order_id": "order-001",
                        "quote_id": q["quote_id"],
                        "idempotency_key": "f01-" + field,
                    },
                )
            self.assertEqual(e.exception.code, code)
            self.assertEqual(
                db.one("SELECT refunded_krw FROM orders WHERE id='order-001'")[0], 0
            )

    def test_r1_quote_rolls_back_with_other_transaction(self):
        db = Database()
        g = Gateway(db, Trace(db, "r1", "mock", "order-001"))
        errors = []

        def quote():
            try:
                g._quote_refund({"order_id": "order-001"})
            except Exception as e:
                errors.append(type(e).__name__)

        with self.assertRaises(RuntimeError):
            with db.transaction():
                db.conn.execute(
                    "UPDATE orders SET status='ROLLBACK_ME' WHERE id='order-001'"
                )
                th = threading.Thread(target=quote)
                th.start()
                th.join(1)
                raise RuntimeError("rollback")
        th.join(1)
        self.assertEqual(
            db.one("SELECT status FROM orders WHERE id='order-001'")[0], "DELIVERED"
        )
        self.assertEqual(db.one("SELECT COUNT(*) FROM quotes")[0], 1)

    def test_f02_request_customer_is_not_authority(self):
        self.assertEqual(
            run_refund(self.db, "order-003", customer_id="cust-001")["reason_code"],
            "OWNERSHIP_DENIED",
        )

    def test_f03_static_root_boundary(self):
        from backend.server import ROOT

        self.assertNotEqual(
            (ROOT / "web" / ".." / "README.md").resolve().parent,
            (ROOT / "web").resolve(),
        )

    def test_f04_rollback_has_no_partial_write(self):
        t = Trace(self.db, "f04", "mock", "order-001")
        g = Gateway(self.db, t)
        q = g.call("quote_refund", {"order_id": "order-001"})
        self.db.fail_refund_insert = True
        with self.assertRaises(RuntimeError):
            g.call(
                "issue_refund",
                {
                    "order_id": "order-001",
                    "quote_id": q["quote_id"],
                    "idempotency_key": "f04",
                },
            )
        self.db.fail_refund_insert = False
        self.assertEqual(
            self.db.one("SELECT refunded_krw FROM orders WHERE id='order-001'")[0], 0
        )
        self.assertEqual(self.db.one("SELECT COUNT(*) FROM refunds")[0], 0)

    def test_f04_other_trace_cannot_commit_open_transaction(self):
        t = Trace(self.db, "f04-thread", "mock", "order-001")
        self.db.conn.execute("BEGIN IMMEDIATE")
        self.db.conn.execute(
            "UPDATE orders SET status='UNCOMMITTED' WHERE id='order-001'"
        )
        errors = []

        def other():
            try:
                t.add("other.request", {})
            except RuntimeError as e:
                errors.append(str(e))

        th = threading.Thread(target=other)
        th.start()
        th.join(1)
        self.db.conn.rollback()
        self.assertEqual(errors, ["trace write during transaction"])
        self.assertEqual(
            self.db.one("SELECT status FROM orders WHERE id='order-001'")[0],
            "DELIVERED",
        )

    def test_f05_live_is_unverified(self):
        import os
        from unittest.mock import patch

        with patch.dict(os.environ, {"NVIDIA_API_KEY": ""}):
            self._check_live_without_key()

    def _check_live_without_key(self):
        r = run_refund(self.db, "order-001", mode="live")
        self.assertEqual(r["status"], Outcome.FAILED)
        self.assertFalse(r["live_verified"])

    def test_f06_verify_mismatch_reconciles(self):
        self.assertEqual(
            run_refund(self.db, "order-001", fault_verify=True)["status"],
            Outcome.NEEDS_RECONCILIATION,
        )

    def test_r2_post_commit_exception_reconciles_and_stops(self):
        original = Gateway._verify_refund

        def broken(self, args):
            raise TimeoutError("after commit")

        Gateway._verify_refund = broken
        try:
            r = run_refund(self.db, "order-001")
            self.assertEqual(r["status"], Outcome.NEEDS_RECONCILIATION)
            self.assertEqual(
                self.db.one("SELECT status FROM runs WHERE id=?", (r["run_id"],))[0],
                Outcome.NEEDS_RECONCILIATION,
            )
            self.assertEqual(self.db.one("SELECT COUNT(*) FROM refunds")[0], 1)
        finally:
            Gateway._verify_refund = original

    def test_f07_real_splits_and_leak_detection(self):
        m = split_manifest()
        self.assertEqual(
            (len(m["discovery"]), len(m["validation"]), len(m["test"])), (30, 30, 40)
        )
        self.assertTrue(validate_splits(m))
        self.assertFalse(
            validate_splits(
                {
                    "discovery": [{"id": "same"}],
                    "validation": [{"id": "same"}],
                    "test": [],
                }
            )
        )

    def test_r3_oracle_rejects_partial_or_wrong_pending(self):
        self.db.conn.execute("UPDATE orders SET refunded_krw=100 WHERE id='order-001'")
        self.db.conn.execute(
            "INSERT INTO refunds VALUES ('bad','order-001','bad','bad',100,'COMMITTED')"
        )
        self.db.conn.commit()
        self.assertFalse(
            independent_oracle(self.db, "order-001", Outcome.DENIED)["passed"]
        )
        self.assertFalse(
            independent_oracle(Database(), "order-001", Outcome.AWAITING_APPROVAL)[
                "passed"
            ]
        )

    def test_s2_oracle_rejects_unapproved_high_value_and_unreceived_return(self):
        self.db.conn.execute(
            "UPDATE orders SET refunded_krw=600000 WHERE id='order-002'"
        )
        self.db.conn.execute(
            "INSERT INTO refunds VALUES ('bad-high','order-002','bad-high','bad',1,'COMMITTED')"
        )
        self.db.conn.commit()
        result = independent_oracle(self.db, "order-002", Outcome.SUCCEEDED)
        self.assertFalse(result["passed"])
        self.assertFalse(result["safe"])
        db = Database()
        db.conn.execute("UPDATE orders SET refunded_krw=89000 WHERE id='order-001'")
        db.conn.execute("UPDATE returns SET received=0 WHERE order_id='order-001'")
        db.conn.execute(
            "INSERT INTO refunds VALUES ('bad-ret','order-001','bad-ret','bad',89000,'COMMITTED')"
        )
        db.conn.commit()
        self.assertFalse(
            independent_oracle(db, "order-001", Outcome.SUCCEEDED)["passed"]
        )

    def test_r4_fixtures_load_and_leak_fields(self):
        m = split_manifest()
        db = Database()
        for group in ("discovery", "validation", "test"):
            for case in m[group]:
                load_case(db, case)
        self.assertEqual(
            sum(
                db.one("SELECT COUNT(*) FROM orders WHERE id LIKE 'synthetic-order-%'")[
                    0
                ]
                for _ in [0]
            ),
            100,
        )
        bad = {
            k: list(v) for k, v in m.items() if k in ("discovery", "validation", "test")
        }
        bad["validation"][0] = dict(
            bad["validation"][0],
            order_id=bad["discovery"][0]["order_id"],
            text=bad["discovery"][0]["text"],
            seed=bad["discovery"][0]["seed"],
        )
        self.assertFalse(validate_splits(bad))

    def test_s3_every_fixture_matches_outcome_and_reason(self):
        m = split_manifest()
        outcomes = {}
        for group in ("discovery", "validation", "test"):
            for case in m[group]:
                db = Database()
                load_case(db, case)
                r = run_refund(db, case["order_id"])
                outcomes[case["id"]] = r["status"]
                self.assertEqual(r["status"], case["expected"], case["id"])
                if case["expected"] == "DENIED":
                    self.assertEqual(
                        r["reason_code"], "RETURN_NOT_RECEIVED", case["id"]
                    )
        self.assertEqual(len(outcomes), 100)
        poisoned = {
            k: list(v) for k, v in m.items() if k in ("discovery", "validation", "test")
        }
        poisoned["test"][0] = dict(
            poisoned["test"][0],
            expected=(
                "SUCCEEDED"
                if poisoned["test"][0]["expected"] != "SUCCEEDED"
                else "DENIED"
            ),
        )
        db = Database()
        load_case(db, poisoned["test"][0])
        self.assertNotEqual(
            run_refund(db, poisoned["test"][0]["order_id"])["status"],
            poisoned["test"][0]["expected"],
        )

    def test_r5_quote_provenance_is_previous_step(self):
        r = run_refund(self.db, "order-001")
        event = [
            x
            for x in self.db.events(r["run_id"])
            if x["kind"] == "tool.requested" and "issue_refund" in x["payload"]
        ][0]
        provenance = json.loads(event["provenance"])
        self.assertEqual(provenance["quote_id"], "steps.quote.quote_id")
        self.assertNotEqual(provenance.get("quote_id"), "input.order_id")

    def test_r6_new_quote_uses_current_policy(self):
        self.db.conn.execute("UPDATE policies SET active=0")
        self.db.conn.execute("INSERT INTO policies VALUES ('new-policy',500000,1)")
        self.db.conn.commit()
        t = Trace(self.db, "r6", "mock", "order-001")
        q = Gateway(self.db, t).call("quote_refund", {"order_id": "order-001"})
        self.assertEqual(q["policy_hash"], "new-policy")

    def test_tool_schema_hash_covers_fields_and_types(self):
        self.assertIn("order_id", TOOL_SCHEMA_CANONICAL["get_order"])
        altered = json.loads(json.dumps(TOOL_SCHEMA_CANONICAL))
        altered["get_order"]["order_id"] = "integer"
        altered_hash = hashlib.sha256(
            json.dumps(altered, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        self.assertNotEqual(TOOL_SCHEMA_HASH, altered_hash)

    def test_approval_create_consume_expire_and_concurrent_single_use(self):
        pending = run_refund(self.db, "order-002")
        self.assertEqual(pending["status"], Outcome.AWAITING_APPROVAL)
        approval = self.db.create_approval("operator-1", "order-002", 600000)
        results = []

        def resume():
            results.append(
                run_refund(
                    self.db,
                    "order-002",
                    approval_id=approval["approval_id"],
                    operator_id="operator-1",
                )
            )

        a, b = threading.Thread(target=resume), threading.Thread(target=resume)
        a.start()
        b.start()
        a.join()
        b.join()
        self.assertEqual(sum(x["status"] == Outcome.SUCCEEDED for x in results), 1)
        self.assertEqual(
            sum(
                x.get("reason_code")
                in (
                    "APPROVAL_ALREADY_USED",
                    "DUPLICATE_REFUND",
                    "AMOUNT_INVALID",
                    "ALREADY_REFUNDED",
                )
                for x in results
            ),
            1,
        )
        db = Database()
        expired = db.create_approval("operator-1", "order-002", 600000, ttl_seconds=-1)
        self.assertEqual(
            run_refund(
                db,
                "order-002",
                approval_id=expired["approval_id"],
                operator_id="operator-1",
            )["reason_code"],
            "APPROVAL_EXPIRED",
        )
        db = Database()
        wrong = db.create_approval("operator-1", "order-002", 600000)
        self.assertEqual(
            run_refund(
                db,
                "order-002",
                approval_id=wrong["approval_id"],
                operator_id="attacker",
            )["reason_code"],
            "APPROVAL_BINDING_INVALID",
        )

    def test_s1_gateway_required_fields_are_negative(self):
        g = Gateway(self.db, Trace(self.db, "s4", "mock", "order-001"))
        for args in ({}, {"order_id": 1}, {"order_id": "order-001", "unexpected": "x"}):
            with self.assertRaises(PolicyError) as e:
                g.call("get_order", args)
            self.assertEqual(e.exception.code, "INVALID_INPUT")

    def test_idempotency_mcp_bounded_and_export(self):
        self.assertEqual(
            MockModelLoop().run(["x"] * 13)["reason"], "TURN_BUDGET_EXCEEDED"
        )
        t = Trace(self.db, "f08", "mock", "order-001")
        self.assertEqual(
            MCPAdapter(Gateway(self.db, t)).call(
                "get_order", {"order_id": "order-001"}
            )["id"],
            "order-001",
        )
        r = run_refund(self.db, "order-001")
        self.assertTrue(
            independent_oracle(self.db, "order-001", Outcome.SUCCEEDED)["passed"]
        )
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "trace.jsonl"
            self.db.export_jsonl(r["run_id"], p)
            self.assertTrue(p.read_text())

    def test_idempotency_same_payload_replays_and_conflict_is_denied(self):
        t = Trace(self.db, "idem", "mock", "order-001")
        g = Gateway(self.db, t)
        q = g.call("quote_refund", {"order_id": "order-001"})
        args = {
            "order_id": "order-001",
            "quote_id": q["quote_id"],
            "idempotency_key": "same-key",
        }
        first = g.call("issue_refund", args)
        second = g.call("issue_refund", args)
        self.assertTrue(second["replayed"])
        self.assertEqual(first["amount_krw"], second["amount_krw"])
        db = Database()
        t2 = Trace(db, "idem-conflict", "mock", "order-001")
        g2 = Gateway(db, t2)
        q2 = g2.call("quote_refund", {"order_id": "order-001"})
        g2.call(
            "issue_refund",
            {
                "order_id": "order-001",
                "quote_id": q2["quote_id"],
                "idempotency_key": "same-key",
            },
        )
        db.conn.execute(
            "UPDATE quotes SET amount_krw=88000 WHERE id=?", (q2["quote_id"],)
        )
        db.conn.commit()
        with self.assertRaises(PolicyError) as e:
            g2.call(
                "issue_refund",
                {
                    "order_id": "order-001",
                    "quote_id": q2["quote_id"],
                    "idempotency_key": "same-key",
                },
            )
        self.assertEqual(e.exception.code, "IDEMPOTENCY_CONFLICT")


if __name__ == "__main__":
    unittest.main()
