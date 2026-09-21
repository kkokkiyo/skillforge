"""Loopback-only operator console and explicit JSON API."""

import hmac
import json
import mimetypes
import os
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse
from .config import ROOT, load_env
from .app import Database, PolicyError, load_case, split_manifest
from .engine import WorkflowService, execute, policy_hash, digest
from .evaluation import benchmark

load_env()
dbpath = os.getenv("SKILLFORGE_DB", str(ROOT / "artifacts" / "skillforge.sqlite3"))
if dbpath != ":memory:":
    Path(dbpath).parent.mkdir(parents=True, exist_ok=True)
DB = Database(dbpath)


def operator_from_request(handler):
    expected = os.getenv("SKILLFORGE_OPERATOR_SESSION", "")
    supplied = handler.headers.get("X-Operator-Session", "")
    return (
        "operator-1"
        if expected and supplied and hmac.compare_digest(expected, supplied)
        else None
    )


class Handler(BaseHTTPRequestHandler):
    def send_json(self, code, value):
        raw = json.dumps(value, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def service(self):
        # server module alias can replace DB for isolated tests.
        return WorkflowService(DB)

    def do_GET(self):
        path = unquote(urlparse(self.path).path)
        service = self.service()
        if path == "/health":
            verified = DB.one(
                "SELECT 1 FROM runs WHERE mode='live' AND status='SUCCEEDED'"
            )
            return self.send_json(
                200,
                {
                    "status": "ok",
                    "mode": "mock",
                    "key_configured": bool(os.getenv("NVIDIA_API_KEY")),
                    "adapter_available": True,
                    "live_verified": bool(verified),
                    "operator_configured": bool(
                        os.getenv("SKILLFORGE_OPERATOR_SESSION")
                    ),
                    "nat_verified": False,
                    "openshell_verified": False,
                },
            )
        if path == "/api/cases":
            return self.send_json(200, split_manifest())
        if path == "/api/workflows":
            return self.send_json(200, service.list())
        if path == "/api/runs":
            with DB.lock:
                rows = [
                    dict(r)
                    for r in DB.conn.execute(
                        "SELECT * FROM runs ORDER BY rowid DESC LIMIT 80"
                    )
                ]
            return self.send_json(200, rows)
        if path.startswith("/api/runs/"):
            rid = path.split("/")[3]
            row = DB.one("SELECT * FROM runs WHERE id=?", (rid,))
            if not row:
                return self.send_json(404, {"error": "NOT_FOUND"})
            if path.endswith("/events"):
                return self.send_json(200, {"events": DB.events(rid)})
            return self.send_json(200, dict(row))
        if path == "/api/evaluations":
            with DB.lock:
                reports = [
                    json.loads(r[0])
                    for r in DB.conn.execute(
                        "SELECT report FROM evaluations ORDER BY rowid DESC LIMIT 5"
                    )
                ]
            return self.send_json(
                200, [{k: v for k, v in r.items() if k != "runs"} for r in reports]
            )
        root = (ROOT / "web").resolve()
        file = (root / (path.lstrip("/") or "index.html")).resolve()
        if root not in file.parents or not file.is_file():
            return self.send_json(404, {"error": "NOT_FOUND"})
        raw = file.read_bytes()
        self.send_response(200)
        self.send_header(
            "Content-Type",
            mimetypes.guess_type(str(file))[0] or "application/octet-stream",
        )
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 32768:
                return self.send_json(422, {"error": "INVALID_INPUT"})
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                return self.send_json(422, {"error": "INVALID_INPUT"})
            service, path = self.service(), self.path
            operator = operator_from_request(self)
            admin = path in {
                "/api/approvals",
                "/api/demo/discover",
                "/api/candidates",
                "/api/evaluations",
                "/api/demo/new-order",
                "/api/policy/bump",
            } or path.startswith("/api/workflows/")
            if admin and not operator:
                return self.send_json(403, {"error": "OPERATOR_SESSION_REQUIRED"})
            if path == "/api/approvals":
                if type(body.get("amount_krw")) is not int or not isinstance(
                    body.get("order_id"), str
                ):
                    return self.send_json(422, {"error": "INVALID_INPUT"})
                return self.send_json(
                    201,
                    DB.create_approval(operator, body["order_id"], body["amount_krw"]),
                )
            if path == "/api/demo/discover":
                return self.send_json(200, service.discover())
            if path == "/api/candidates":
                return self.send_json(201, service.compile())
            if path.startswith("/api/workflows/"):
                parts = path.split("/")
                if len(parts) != 5 or parts[4] not in {"verify", "activate"}:
                    return self.send_json(404, {"error": "NOT_FOUND"})
                return self.send_json(200, getattr(service, parts[4])(parts[3]))
            if path == "/api/demo/new-order":
                kind = body.get("kind", "normal")
                if kind not in {"normal", "high", "unreceived"}:
                    raise ValueError("Unknown scenario")
                oid = "demo-" + secrets.token_hex(5)
                load_case(
                    DB,
                    {
                        "order_id": oid,
                        "amount_krw": 600000 if kind == "high" else 89000,
                        "return_received": kind != "unreceived",
                    },
                )
                return self.send_json(201, {"order_id": oid})
            if path == "/api/policy/bump":
                new_hash = digest({"revision": secrets.token_hex(8), "limit": 500000})
                with DB.transaction():
                    DB.conn.execute("UPDATE policies SET active=0")
                    DB.conn.execute(
                        "INSERT INTO policies VALUES (?,500000,1)", (new_hash,)
                    )
                return self.send_json(
                    200, {"policy_hash": new_hash, "workflows": service.list()}
                )
            if path == "/api/evaluations":
                # Live benchmark must be an explicit CLI action with a known API budget.
                report = benchmark(service)
                return self.send_json(
                    200, {k: v for k, v in report.items() if k != "runs"}
                )
            if path == "/api/runs":
                oid = body.get("order_id")
                if not isinstance(oid, str) or not oid.strip() or len(oid) > 120:
                    return self.send_json(422, {"error": "INVALID_INPUT"})
                if body.get("approval_id") and not operator:
                    return self.send_json(403, {"error": "OPERATOR_SESSION_REQUIRED"})
                params = {
                    "mode": body.get("mode", "mock"),
                    "approval_id": body.get("approval_id"),
                    "operator_id": operator,
                }
                result = (
                    service.run(oid, **params)
                    if body.get("route", "auto") == "auto"
                    else execute(DB, oid, **params)
                )
                return self.send_json(202, result)
            return self.send_json(404, {"error": "NOT_FOUND"})
        except PolicyError as error:
            return self.send_json(409, {"error": error.code, "message": error.message})
        except (ValueError, KeyError, TypeError):
            return self.send_json(422, {"error": "INVALID_INPUT"})
        except Exception as error:
            return self.send_json(
                500, {"error": "INTERNAL_ERROR", "type": type(error).__name__}
            )

    def log_message(self, *_):
        pass


def main():
    print(
        "SkillForge: http://127.0.0.1:"
        + os.getenv("PORT", "8090")
        + " (loopback only)",
        flush=True,
    )
    ThreadingHTTPServer(
        ("127.0.0.1", int(os.getenv("PORT", "8090"))), Handler
    ).serve_forever()
