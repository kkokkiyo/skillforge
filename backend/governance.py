"""Policy impact experiments on isolated synthetic databases; explicit promotion."""
import copy
import json
import secrets

from .app import Database, PolicyError, load_case, split_manifest, TOOL_SCHEMA_HASH
from .engine import digest, execute, policy_hash, validate_workflow


def expected_outcome(case, limit):
    """Independent scenario expectation, not derived from executor output."""
    if case.get("customer_id", "cust-001") != "cust-001" or not case.get("return_received", True):
        return "DENIED"
    return "AWAITING_APPROVAL" if case["amount_krw"] >= limit else "SUCCEEDED"


def boundary_cases(limit):
    return [
        {"id": name, "order_id": "policy-probe-" + name, "amount_krw": amount, **extra}
        for name, amount, extra in [
            ("below-limit", max(1, limit - 1), {}),
            ("at-limit", limit, {}), ("above-limit", limit + 1, {}),
            ("350k-refund", 350000, {}),
            ("return-missing", limit + 1, {"return_received": False}),
            ("foreign-order", 89000, {"customer_id": "cust-other"}),
        ]
    ]


def replay_case(case, policy, artifact):
    db = Database()
    try:
        with db.transaction():
            db.conn.execute("UPDATE policies SET active=0")
            db.conn.execute("INSERT OR REPLACE INTO policies VALUES (?,?,1)", (policy["hash"], policy["approval_limit_krw"]))
        load_case(db, case)
        expected = expected_outcome(case, policy["approval_limit_krw"])
        result = execute(db, case["order_id"], artifact=artifact)
        return {"case_id": case["id"], "amount_krw": case["amount_krw"],
                "expected": expected, "actual": result["status"], "reason": result["reason_code"],
                "passed": result["status"] == expected and result["oracle"]["safe"],
                "safe": result["oracle"]["safe"], "committed": result["oracle"]["committed"],
                "run_id": result["run_id"], "events": db.events(result["run_id"])}
    finally:
        db.conn.close()


class PolicyLab:
    def __init__(self, service):
        self.service, self.db = service, service.db
        with self.db.transaction():
            self.db.conn.execute("CREATE TABLE IF NOT EXISTS policy_reviews(id TEXT PRIMARY KEY,report TEXT,applied INTEGER DEFAULT 0)")

    def current(self):
        return dict(self.db.one("SELECT * FROM policies WHERE active=1"))

    def preview(self, wid, limit):
        if type(limit) is not int or not 2 <= limit <= 100000000:
            raise PolicyError("INVALID_INPUT", "Approval limit must be an integer in range")
        item = self.service.get(wid)
        if not item or item["state"] != "ACTIVE":
            raise PolicyError("ACTIVE_WORKFLOW_REQUIRED", "Activate a verified workflow first")
        if digest(item["artifact"]) != item["artifact_hash"]:
            raise PolicyError("HASH_MISMATCH", "Workflow changed")
        old = self.current()
        if limit == old["approval_limit_krw"]:
            raise PolicyError("NO_POLICY_CHANGE", "Choose a different approval limit")
        target = {"hash": digest({"limit": limit, "revision": secrets.token_hex(8)}), "approval_limit_krw": limit}
        adapted = {**item["artifact"], "policy_hash": target["hash"]}
        cases = split_manifest()["validation"] + boundary_cases(old["approval_limit_krw"])
        cases += [{**c, "id": "new-" + c["id"], "order_id": "new-" + c["order_id"]} for c in boundary_cases(limit)]
        rows = []
        for case in cases:
            before = replay_case(case, old, item["artifact"])
            after = replay_case(case, target, adapted)
            rows.append({"case_id": case["id"], "amount_krw": case["amount_krw"], "before": before, "after": after,
                         "changed": before["actual"] != after["actual"]})
        rid = "policy-review-" + secrets.token_hex(6)
        report = {"id": rid, "workflow_id": wid, "artifact_hash": item["artifact_hash"],
                  "base_policy": old, "target_policy": target, "cases": rows,
                  "passed": all(r[side]["passed"] for r in rows for side in ("before", "after")),
                  "changed_count": sum(r["changed"] for r in rows), "case_count": len(rows),
                  "unsafe_count": sum(not r[side]["safe"] for r in rows for side in ("before", "after")),
                  "false_block_count": sum(r[side]["expected"] == "SUCCEEDED" and r[side]["actual"] != "SUCCEEDED" for r in rows for side in ("before", "after")),
                  "scope": "isolated synthetic validation + boundary probes; no production writes",
                  "invalidation": "All workflows using the prior policy are invalidated; no selective safety claim.",
                  "applied": False}
        with self.db.transaction():
            if policy_hash(self.db) != old["hash"]:
                raise PolicyError("STALE_PREVIEW", "Policy changed during preview")
            self.db.conn.execute("INSERT INTO policy_reviews VALUES (?,?,0)", (rid, json.dumps(report)))
        return report

    def get(self, rid):
        row = self.db.one("SELECT * FROM policy_reviews WHERE id=?", (rid,))
        if not row:
            raise PolicyError("NOT_FOUND", "Policy review not found")
        return {**json.loads(row["report"]), "applied": bool(row["applied"])}

    def apply(self, rid):
        with self.db.transaction():
            report = self.get(rid)
            if report["applied"]:
                return report
            if not report["passed"] or policy_hash(self.db) != report["base_policy"]["hash"]:
                raise PolicyError("STALE_PREVIEW", "Successful preview for current policy required")
            target = report["target_policy"]
            self.db.conn.execute("UPDATE policies SET active=0")
            self.db.conn.execute("INSERT INTO policies VALUES (?,?,1)", (target["hash"], target["approval_limit_krw"]))
            self.db.conn.execute("UPDATE workflows SET state='STALE' WHERE state IN ('ACTIVE','VERIFIED','CANDIDATE')")
            self.db.conn.execute("UPDATE policy_reviews SET applied=1 WHERE id=?", (rid,))
        return self.get(rid)

    def rebase(self, wid):
        item = self.service.get(wid)
        if not item or item["state"] != "STALE" or not item["report"] or not item["report"]["passed"]:
            raise PolicyError("VERIFIED_PARENT_REQUIRED", "A previously verified stale workflow is required")
        if digest(item["artifact"]) != item["artifact_hash"] or item["report"]["artifact_hash"] != item["artifact_hash"]:
            raise PolicyError("HASH_MISMATCH", "Parent artifact/report mismatch")
        if item["artifact"]["tool_schema_hash"] != TOOL_SCHEMA_HASH:
            raise PolicyError("TOOL_SCHEMA_CHANGED", "Collect fresh traces after a tool contract change")
        artifact = copy.deepcopy(item["artifact"])
        artifact.update(policy_hash=policy_hash(self.db), parent_artifact_hash=item["artifact_hash"],
                        origin_policy_hash=artifact.get("origin_policy_hash", artifact["policy_hash"]))
        validate_workflow(artifact)
        wid = "workflow-" + secrets.token_hex(6)
        with self.db.transaction():
            if policy_hash(self.db) != artifact["policy_hash"]:
                raise PolicyError("STALE_POLICY", "Policy changed")
            existing = self.db.one("SELECT id FROM workflows WHERE artifact_hash=? AND state IN ('CANDIDATE','VERIFIED','ACTIVE')", (digest(artifact),))
            if existing:
                wid = existing["id"]
            else:
                self.db.conn.execute("INSERT INTO workflows VALUES (?,?,?,?,NULL)", (wid, "CANDIDATE", json.dumps(artifact), digest(artifact)))
        return self.service.get(wid)
