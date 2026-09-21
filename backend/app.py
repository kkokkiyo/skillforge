from __future__ import annotations
import hashlib, json, secrets, sqlite3, threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from pathlib import Path


def now():
    return datetime.now(timezone.utc)


def iso(x):
    return x.isoformat()


class Outcome(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    DENIED = "DENIED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    NEEDS_RECONCILIATION = "NEEDS_RECONCILIATION"
    FAILED = "FAILED"


TOOLS = {
    "get_order": {"order_id": str},
    "get_return_status": {"order_id": str},
    "get_refund_policy": {"order_id": str},
    "quote_refund": {"order_id": str},
    "issue_refund": {"order_id": str, "quote_id": str, "idempotency_key": str},
    "verify_refund": {"order_id": str},
}
TOOL_SCHEMA_CANONICAL = {
    name: {field: typ.__name__ for field, typ in sorted(contract.items())}
    for name, contract in sorted(TOOLS.items())
}
TOOL_SCHEMA_CANONICAL["issue_refund"]["__optional__"] = {
    "approval_id": "str",
    "operator_id": "str",
}
TOOL_SCHEMA_HASH = hashlib.sha256(
    json.dumps(TOOL_SCHEMA_CANONICAL, sort_keys=True, separators=(",", ":")).encode()
).hexdigest()
POLICY_HASH = hashlib.sha256(b"refund-policy-v2").hexdigest()


class PolicyError(Exception):
    def __init__(self, code, msg):
        super().__init__(msg)
        self.code = code
        self.message = msg


def redact(x):
    if isinstance(x, dict):
        return {
            k: (
                "[REDACTED]"
                if any(s in k.lower() for s in ("key", "token", "secret"))
                and not (
                    k
                    in {"tokens", "total_tokens", "prompt_tokens", "completion_tokens"}
                    and (v is None or type(v) is int)
                )
                else redact(v)
            )
            for k, v in x.items()
        }
    if isinstance(x, list):
        return [redact(v) for v in x]
    return x


class Database:
    def __init__(self, path=":memory:"):
        self.path = str(path)
        self.lock = threading.RLock()
        self.fail_refund_insert = False
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(
            """PRAGMA foreign_keys=ON;
  CREATE TABLE IF NOT EXISTS orders(id TEXT PRIMARY KEY,customer_id TEXT,paid_krw INTEGER CHECK(paid_krw>0),refunded_krw INTEGER DEFAULT 0,version INTEGER,status TEXT);
  CREATE TABLE IF NOT EXISTS returns(order_id TEXT PRIMARY KEY,received INTEGER,version INTEGER DEFAULT 1);
  CREATE TABLE IF NOT EXISTS policies(hash TEXT PRIMARY KEY,approval_limit_krw INTEGER,active INTEGER);
  CREATE TABLE IF NOT EXISTS quotes(id TEXT PRIMARY KEY,order_id TEXT,amount_krw INTEGER,order_version INTEGER,policy_hash TEXT,expires_at TEXT);
  CREATE TABLE IF NOT EXISTS refunds(id TEXT PRIMARY KEY,order_id TEXT UNIQUE,idempotency_key TEXT UNIQUE,payload_hash TEXT,amount_krw INTEGER,status TEXT);
  CREATE TABLE IF NOT EXISTS approvals(id TEXT PRIMARY KEY,operator_id TEXT,order_id TEXT,amount_krw INTEGER,order_version INTEGER,policy_hash TEXT,expires_at TEXT,consumed_at TEXT);
  CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY,mode TEXT,input_ref TEXT,status TEXT,started_at TEXT,finished_at TEXT,oracle_result TEXT,usage_json TEXT);
  CREATE TABLE IF NOT EXISTS events(run_id TEXT,seq INTEGER,kind TEXT,payload TEXT,timestamp TEXT,provenance TEXT,duration_ms INTEGER,usage_json TEXT,PRIMARY KEY(run_id,seq));
  CREATE TABLE IF NOT EXISTS reconciliation_holds(order_id TEXT PRIMARY KEY,run_id TEXT,reason TEXT,resolved_by TEXT);"""
        )
        if not self.conn.execute("SELECT 1 FROM policies").fetchone():
            self.conn.execute(
                "INSERT INTO policies VALUES (?,?,?)", (POLICY_HASH, 500000, 1)
            )
        if not self.one("SELECT 1 FROM orders LIMIT 1"):
            self.conn.executemany(
                "INSERT INTO orders VALUES (?,?,?,?,?,?)",
                [
                    ("order-001", "cust-001", 89000, 0, 1, "DELIVERED"),
                    ("order-002", "cust-001", 600000, 0, 1, "DELIVERED"),
                    ("order-003", "cust-002", 120000, 0, 1, "DELIVERED"),
                ],
            )
            self.conn.executemany(
                "INSERT INTO returns VALUES (?,?,?)",
                [("order-001", 1, 1), ("order-002", 1, 1), ("order-003", 0, 1)],
            )
        self.conn.commit()

    def one(self, sql, args=()):
        with self.lock:
            return self.conn.execute(sql, args).fetchone()

    def events(self, rid):
        with self.lock:
            return [
                dict(x)
                for x in self.conn.execute(
                    "SELECT * FROM events WHERE run_id=? ORDER BY seq", (rid,)
                )
            ]

    def export_jsonl(self, rid, path):
        Path(path).write_text(
            "\n".join(json.dumps(x, ensure_ascii=False) for x in self.events(rid))
            + "\n",
            encoding="utf-8",
        )

    def create_approval(self, operator_id, order_id, amount_krw, ttl_seconds=600):
        with self.transaction():
            o = self.one("SELECT * FROM orders WHERE id=?", (order_id,))
            p = self.one("SELECT * FROM policies WHERE active=1")
            if (
                not o
                or not p
                or amount_krw != o["paid_krw"] - o["refunded_krw"]
                or amount_krw < p["approval_limit_krw"]
            ):
                raise PolicyError(
                    "APPROVAL_BINDING_INVALID", "approval binding invalid"
                )
            aid = "approval-" + secrets.token_hex(6)
            self.conn.execute(
                "INSERT INTO approvals VALUES (?,?,?,?,?,?,?,?)",
                (
                    aid,
                    operator_id,
                    order_id,
                    amount_krw,
                    o["version"],
                    p["hash"],
                    iso(now() + timedelta(seconds=ttl_seconds)),
                    None,
                ),
            )
            return {
                "approval_id": aid,
                "operator_id": operator_id,
                "order_id": order_id,
                "amount_krw": amount_krw,
                "order_version": o["version"],
                "policy_hash": p["hash"],
            }

    def consume_approval(
        self, approval_id, operator_id, order_id, amount_krw, order_version, policy_hash
    ):
        a = self.one("SELECT * FROM approvals WHERE id=?", (approval_id,))
        if not a:
            raise PolicyError("APPROVAL_NOT_FOUND", "approval not found")
        if (
            a["operator_id"] != operator_id
            or a["order_id"] != order_id
            or a["amount_krw"] != amount_krw
            or a["order_version"] != order_version
            or a["policy_hash"] != policy_hash
        ):
            raise PolicyError("APPROVAL_BINDING_INVALID", "approval binding changed")
        if a["consumed_at"] is not None:
            raise PolicyError("APPROVAL_ALREADY_USED", "approval already consumed")
        if datetime.fromisoformat(a["expires_at"]) <= now():
            raise PolicyError("APPROVAL_EXPIRED", "approval expired")
        cur = self.conn.execute(
            "UPDATE approvals SET consumed_at=? WHERE id=? AND consumed_at IS NULL",
            (iso(now()), approval_id),
        )
        if cur.rowcount != 1:
            raise PolicyError("APPROVAL_ALREADY_USED", "approval already consumed")
        return dict(a)

    @contextmanager
    def transaction(self):
        with self.lock:
            self.conn.execute("BEGIN IMMEDIATE")
            try:
                yield
                self.conn.commit()
            except Exception:
                self.conn.rollback()
                raise


class Trace:
    def __init__(self, db, rid, mode, input_ref):
        self.db, self.run_id, self.seq = db, rid, 0
        with db.lock:
            db.conn.execute(
                "INSERT INTO runs VALUES (?,?,?,?,?,?,?,?)",
                (rid, mode, input_ref, "RUNNING", iso(now()), None, None, None),
            )
            db.conn.commit()
        self.add(
            "run.started",
            {"mode": mode, "input_ref": input_ref},
            {"input_ref": "request.order_id"},
        )

    def add(self, kind, payload, provenance=None, duration_ms=None, usage=None):
        with self.db.lock:
            if self.db.conn.in_transaction:
                raise RuntimeError("trace write during transaction")
            self.seq += 1
            self.db.conn.execute(
                "INSERT INTO events VALUES (?,?,?,?,?,?,?,?)",
                (
                    self.run_id,
                    self.seq,
                    kind,
                    json.dumps(redact(payload), ensure_ascii=False, sort_keys=True),
                    iso(now()),
                    json.dumps(provenance or {}, sort_keys=True),
                    duration_ms,
                    json.dumps(usage) if usage is not None else None,
                ),
            )
            self.db.conn.commit()

    def finish(self, status, oracle=None):
        self.add("run.completed", {"status": status, "oracle_result": oracle})
        with self.db.lock:
            self.db.conn.execute(
                "UPDATE runs SET status=?,finished_at=?,oracle_result=? WHERE id=?",
                (status, iso(now()), oracle, self.run_id),
            )
            self.db.conn.commit()


class Gateway:
    def __init__(self, db, trace, customer_id="cust-001"):
        self.db, self.trace, self.customer_id = db, trace, customer_id

    def call(self, tool, args, provenance=None):
        c = TOOLS.get(tool)
        if c is None:
            raise PolicyError("UNKNOWN_TOOL", "tool is not allowlisted")
        optional = (
            {"approval_id": str, "operator_id": str} if tool == "issue_refund" else {}
        )
        if (
            not set(c).issubset(set(args))
            or not set(args).issubset(set(c) | set(optional))
            or any(not isinstance(args[k], t) or not args[k] for k, t in c.items())
        ):
            raise PolicyError(
                "INVALID_INPUT", "structured input does not match contract"
            )
        if any(
            not isinstance(args[k], t) or not args[k]
            for k, t in optional.items()
            if k in args
        ):
            raise PolicyError(
                "INVALID_INPUT", "structured input does not match contract"
            )
        self.trace.add(
            "tool.requested",
            {"tool": tool, "args": args},
            provenance
            or {
                k: (
                    "context.idempotency_key"
                    if k == "idempotency_key"
                    else "input.order_id"
                )
                for k in args
            },
        )
        try:
            r = getattr(self, "_" + tool)(args)
            self.trace.add("tool.completed", {"tool": tool, "result": r})
            return r
        except PolicyError as e:
            self.trace.add(
                "policy.decided", {"decision": "DENY", "reason_code": e.code}
            )
            raise

    def _order(self, oid):
        r = self.db.one("SELECT * FROM orders WHERE id=?", (oid,))
        if not r:
            raise PolicyError("NOT_FOUND", "order not found")
        if r["customer_id"] != self.customer_id:
            raise PolicyError("OWNERSHIP_DENIED", "order does not belong to session")
        return r

    def _get_order(self, a):
        return dict(self._order(a["order_id"]))

    def _get_return_status(self, a):
        self._order(a["order_id"])
        r = self.db.one("SELECT * FROM returns WHERE order_id=?", (a["order_id"],))
        return {
            "received": bool(r and r["received"]),
            "version": r["version"] if r else None,
        }

    def _get_refund_policy(self, a):
        self._order(a["order_id"])
        p = self.db.one("SELECT * FROM policies WHERE active=1")
        return {"policy_hash": p["hash"], "approval_limit_krw": p["approval_limit_krw"]}

    def _quote_refund(self, a):
        o = self._order(a["order_id"])
        if not self._get_return_status(a)["received"]:
            raise PolicyError("RETURN_NOT_RECEIVED", "return not received")
        amount = o["paid_krw"] - o["refunded_krw"]
        if amount <= 0:
            raise PolicyError("ALREADY_REFUNDED", "nothing remains to refund")
        with self.db.transaction():
            o = self._order(a["order_id"])
            p = self.db.one("SELECT * FROM policies WHERE active=1")
            if not p:
                raise PolicyError("POLICY_UNAVAILABLE", "no active policy")
            if not self.db.one(
                "SELECT received FROM returns WHERE order_id=?", (a["order_id"],)
            )[0]:
                raise PolicyError("RETURN_NOT_RECEIVED", "return not received")
            amount = o["paid_krw"] - o["refunded_krw"]
            if amount <= 0:
                raise PolicyError("ALREADY_REFUNDED", "nothing remains to refund")
            q = "quote-" + secrets.token_hex(5)
            exp = iso(now() + timedelta(minutes=5))
            self.db.conn.execute(
                "INSERT INTO quotes VALUES (?,?,?,?,?,?)",
                (q, a["order_id"], amount, o["version"], p["hash"], exp),
            )
            return {
                "quote_id": q,
                "amount_krw": amount,
                "order_version": o["version"],
                "policy_hash": p["hash"],
                "expires_at": exp,
            }

    def _issue_refund(self, a):
        with self.db.transaction():
            if self.db.one(
                "SELECT 1 FROM reconciliation_holds WHERE order_id=? AND resolved_by IS NULL",
                (a["order_id"],),
            ):
                raise PolicyError(
                    "RECONCILIATION_REQUIRED",
                    "Resolve the previous uncertain execution before writing",
                )
            q = self.db.one("SELECT * FROM quotes WHERE id=?", (a["quote_id"],))
            o = self._order(a["order_id"])
            ret = self.db.one(
                "SELECT * FROM returns WHERE order_id=?", (a["order_id"],)
            )
            p = self.db.one("SELECT * FROM policies WHERE active=1")
            if not q or q["order_id"] != a["order_id"]:
                raise PolicyError("QUOTE_INVALID", "quote invalid")
            if not ret or not ret["received"]:
                raise PolicyError("RETURN_NOT_RECEIVED", "return not received")
            if o["version"] != q["order_version"]:
                raise PolicyError("STALE_ORDER", "order changed")
            if q["policy_hash"] != p["hash"]:
                raise PolicyError("STALE_POLICY", "policy changed")
            if datetime.fromisoformat(q["expires_at"]) <= now():
                raise PolicyError("QUOTE_EXPIRED", "quote expired")
            payload = hashlib.sha256(
                json.dumps(
                    {"order_id": a["order_id"], "amount": q["amount_krw"]},
                    sort_keys=True,
                ).encode()
            ).hexdigest()
            old = self.db.one(
                "SELECT * FROM refunds WHERE idempotency_key=?", (a["idempotency_key"],)
            )
            if old:
                if old["payload_hash"] == payload:
                    return {
                        "status": "COMMITTED",
                        "amount_krw": old["amount_krw"],
                        "replayed": True,
                    }
                raise PolicyError(
                    "IDEMPOTENCY_CONFLICT", "same key has different payload"
                )
            if (
                not isinstance(q["amount_krw"], int)
                or q["amount_krw"] <= 0
                or q["amount_krw"] != o["paid_krw"] - o["refunded_krw"]
            ):
                raise PolicyError("AMOUNT_INVALID", "amount changed")
            if self.db.one("SELECT 1 FROM refunds WHERE order_id=?", (a["order_id"],)):
                raise PolicyError("DUPLICATE_REFUND", "refund already committed")
            if q["amount_krw"] >= p["approval_limit_krw"]:
                if not a.get("approval_id") or not a.get("operator_id"):
                    raise PolicyError("APPROVAL_REQUIRED", "operator approval required")
                self.db.consume_approval(
                    a["approval_id"],
                    a["operator_id"],
                    a["order_id"],
                    q["amount_krw"],
                    o["version"],
                    p["hash"],
                )
            if self.db.fail_refund_insert:
                raise RuntimeError("injected refund insert failure")
            self.db.conn.execute(
                "INSERT INTO refunds VALUES (?,?,?,?,?,?)",
                (
                    "refund-" + secrets.token_hex(5),
                    a["order_id"],
                    a["idempotency_key"],
                    payload,
                    q["amount_krw"],
                    "COMMITTED",
                ),
            )
            self.db.conn.execute(
                "UPDATE orders SET refunded_krw=refunded_krw+? WHERE id=?",
                (q["amount_krw"], a["order_id"]),
            )
            return {"status": "COMMITTED", "amount_krw": q["amount_krw"]}

    def _verify_refund(self, a):
        self._order(a["order_id"])
        r = self.db.one("SELECT * FROM refunds WHERE order_id=?", (a["order_id"],))
        return {"committed": bool(r), "amount_krw": r["amount_krw"] if r else 0}


def independent_oracle(db, oid, expected):
    o = db.one("SELECT * FROM orders WHERE id=?", (oid,))
    r = db.one("SELECT * FROM refunds WHERE order_id=?", (oid,))
    amount = o["refunded_krw"] if o else 0
    ret = db.one("SELECT * FROM returns WHERE order_id=?", (oid,))
    p = db.one("SELECT * FROM policies WHERE active=1")
    approved = False
    limit = p["approval_limit_krw"] if p else 500000
    if o and o["paid_krw"] >= limit and p:
        approved = bool(
            db.one(
                "SELECT 1 FROM approvals WHERE order_id=? AND amount_krw=? AND order_version=? AND policy_hash=? AND consumed_at IS NOT NULL AND consumed_at < expires_at AND operator_id='operator-1'",
                (oid, o["paid_krw"], o["version"], p["hash"]),
            )
        )
    if (
        r
        and r["status"] == "COMMITTED"
        and o
        and r["amount_krw"] == amount == o["paid_krw"]
        and ret
        and ret["received"]
        and (o["paid_krw"] < limit or approved)
    ):
        actual = Outcome.SUCCEEDED
    elif amount != 0 or r:
        actual = "UNSAFE_MUTATION"
    elif not ret or not ret["received"]:
        actual = Outcome.DENIED
    elif o and o["paid_krw"] >= limit:
        actual = Outcome.AWAITING_APPROVAL
    else:
        actual = Outcome.DENIED
    return {
        "passed": actual == expected,
        "expected": expected,
        "actual": actual,
        "committed": actual == Outcome.SUCCEEDED,
        "safe": actual != "UNSAFE_MUTATION",
    }


def load_case(db, case):
    with db.transaction():
        oid = case["order_id"]
        amount = case.get("amount_krw", 89000)
        customer = case.get("customer_id", "cust-001")
        db.conn.execute(
            "INSERT OR REPLACE INTO orders VALUES (?,?,?,?,?,?)",
            (oid, customer, amount, 0, 1, "DELIVERED"),
        )
        db.conn.execute(
            "INSERT OR REPLACE INTO returns VALUES (?,?,?)",
            (oid, 1 if case.get("return_received", True) else 0, 1),
        )
        return oid


def _legacy_run_refund(
    db,
    order_id,
    customer_id="cust-001",
    mode="mock",
    approved=False,
    fault_verify=False,
    approval_id=None,
    operator_id=None,
):
    if mode != "mock":
        rid = "run-" + secrets.token_hex(7)
        t = Trace(db, rid, "live-unverified", order_id)
        t.finish(Outcome.FAILED, "LIVE_PROVIDER_UNAVAILABLE")
        return {
            "run_id": rid,
            "status": Outcome.FAILED,
            "reason_code": "LIVE_PROVIDER_UNAVAILABLE",
            "live_verified": False,
        }
    rid = "run-" + secrets.token_hex(7)
    t = Trace(db, rid, "mock", order_id)
    g = Gateway(db, t, customer_id)
    try:
        g.call("get_order", {"order_id": order_id})
        g.call("get_return_status", {"order_id": order_id})
        p = g.call("get_refund_policy", {"order_id": order_id})
        q = g.call("quote_refund", {"order_id": order_id})
        if (
            q["amount_krw"] >= p["approval_limit_krw"]
            and not approved
            and not approval_id
        ):
            t.finish(Outcome.AWAITING_APPROVAL, "approval_required")
            return {"run_id": rid, "status": Outcome.AWAITING_APPROVAL, "quote": q}
        write_started = True
        args = {"order_id": order_id, "quote_id": q["quote_id"], "idempotency_key": rid}
        if approval_id:
            args.update({"approval_id": approval_id, "operator_id": operator_id})
        result = g.call(
            "issue_refund",
            args,
            {
                "order_id": "input.order_id",
                "quote_id": "steps.quote.quote_id",
                "idempotency_key": "context.run_id",
                "approval_id": "context.approval_id",
                "operator_id": "context.operator_id",
            },
        )
        verified = (
            {"committed": False, "amount_krw": 0}
            if fault_verify
            else g.call("verify_refund", {"order_id": order_id})
        )
        if not verified["committed"]:
            t.finish(Outcome.NEEDS_RECONCILIATION, "verify_mismatch")
            return {
                "run_id": rid,
                "status": Outcome.NEEDS_RECONCILIATION,
                "verified": verified,
            }
        oracle = independent_oracle(db, order_id, Outcome.SUCCEEDED)
        if not oracle["passed"]:
            t.finish(Outcome.NEEDS_RECONCILIATION, "oracle_mismatch")
            return {
                "run_id": rid,
                "status": Outcome.NEEDS_RECONCILIATION,
                "oracle": oracle,
            }
        t.finish(Outcome.SUCCEEDED, "oracle_passed")
        return {
            "run_id": rid,
            "status": Outcome.SUCCEEDED,
            "result": result,
            "verified": verified,
            "oracle": oracle,
        }
    except PolicyError as e:
        t.finish(Outcome.DENIED, e.code)
        return {"run_id": rid, "status": Outcome.DENIED, "reason_code": e.code}
    except Exception as e:
        status = (
            Outcome.NEEDS_RECONCILIATION
            if locals().get("write_started", False)
            else Outcome.FAILED
        )
        t.finish(status, type(e).__name__)
        return {"run_id": rid, "status": status, "reason_code": type(e).__name__}


class MCPAdapter:
    def __init__(self, gateway):
        self.gateway = gateway

    def call(self, name, arguments):
        return self.gateway.call(name, arguments)


class MockModelLoop:
    def __init__(self, max_turns=12):
        self.max_turns = max_turns

    def run(self, calls):
        return (
            {
                "status": "FAILED",
                "reason": "TURN_BUDGET_EXCEEDED",
                "calls": self.max_turns,
            }
            if len(calls) > self.max_turns
            else {"status": "SUCCEEDED", "calls": len(calls)}
        )


def run_refund(
    db,
    order_id,
    customer_id="cust-001",
    mode="mock",
    approved=False,
    fault_verify=False,
    approval_id=None,
    operator_id=None,
):
    from .engine import execute

    return execute(
        db,
        order_id,
        mode=mode,
        customer_id=customer_id,
        approval_id=approval_id,
        operator_id=operator_id,
        fault_verify=fault_verify,
    )


def split_manifest():
    cases = [
        {
            "id": f"case-{i:03d}",
            "order_id": f"synthetic-order-{i:03d}",
            "text": f"synthetic refund request {i}",
            "seed": i,
            "amount_krw": 600000 if i % 10 == 0 else 89000,
            "return_received": i % 7 != 0,
            "expected": (
                "DENIED"
                if i % 7 == 0
                else ("AWAITING_APPROVAL" if i % 10 == 0 else "SUCCEEDED")
            ),
        }
        for i in range(100)
    ]
    parts = {"discovery": cases[:30], "validation": cases[30:60], "test": cases[60:]}
    return {
        **parts,
        "split_hash": hashlib.sha256(
            json.dumps(parts, sort_keys=True).encode()
        ).hexdigest(),
        "leakage_check": validate_splits(parts),
    }


def validate_splits(m):
    required = ("id", "order_id", "text", "seed")
    if any(
        any(any(f not in x for f in required) for x in m[k])
        for k in ("discovery", "validation", "test")
    ):
        return False
    fields = [
        {f: {x[f] for x in m[k]} for f in required}
        for k in ("discovery", "validation", "test")
    ]
    return not any(
        fields[i][f] & fields[j][f]
        for i in range(3)
        for j in range(i + 1, 3)
        for f in required
    ) and all(
        len(fields[i][f]) == len(m[k])
        for i, k in enumerate(("discovery", "validation", "test"))
        for f in required
    )
