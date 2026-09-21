"""Typed FastAPI console with asynchronous jobs and reconnectable SSE traces."""

import asyncio
import hmac
import json
import os
import secrets
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from .config import ROOT, load_env
from .app import (
    Database,
    PolicyError,
    Trace,
    load_case,
    split_manifest,
    independent_oracle,
)
from .engine import WorkflowService, execute, digest
from .evaluation import benchmark
from .router import route_text

load_env()


class StrictBody(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class RunBody(StrictBody):
    order_id: str | None = Field(default=None, min_length=1, max_length=120)
    text: str | None = Field(default=None, min_length=1, max_length=2000)
    mode: Literal["mock", "live"] = "mock"
    route: Literal["auto", "react"] = "auto"
    approval_id: str | None = None
    request_id: str = Field(min_length=8, max_length=120)


class ApprovalBody(StrictBody):
    order_id: str = Field(min_length=1, max_length=120)
    amount_krw: int = Field(gt=0)


class CaseBody(StrictBody):
    kind: Literal["normal", "high", "unreceived"] = "normal"


class ActivateBody(StrictBody):
    expected_hash: str = Field(min_length=64, max_length=64)


def create_app(db: Database | None = None) -> FastAPI:
    if db is None:
        path = os.getenv("SKILLFORGE_DB", str(ROOT / "artifacts/skillforge.sqlite3"))
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        db = Database(path)
    service = WorkflowService(db)
    pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="refund")
    jobs: dict[str, dict] = {}
    lock = threading.RLock()
    app = FastAPI(title="SkillForge", version="0.3.0")
    app.state.db = db
    app.state.service = service
    with db.transaction():
        db.conn.execute(
            "CREATE TABLE IF NOT EXISTS api_requests(request_id TEXT PRIMARY KEY,payload_hash TEXT,run_id TEXT)"
        )
        db.conn.execute(
            "CREATE TABLE IF NOT EXISTS api_results(run_id TEXT PRIMARY KEY,result TEXT)"
        )

    def save_result(result: dict):
        rid = result["run_id"]
        if not db.one("SELECT 1 FROM runs WHERE id=?", (rid,)):
            trace = Trace(db, rid, result.get("mode", "mock"), "request-routing")
            trace.add("routing.result", result)
            trace.add("execution.result", result)
            trace.finish(result["status"], None)
        with db.transaction():
            db.conn.execute(
                "INSERT OR REPLACE INTO api_results VALUES (?,?)",
                (rid, json.dumps(result)),
            )
        with lock:
            jobs[rid] = result

    @app.exception_handler(PolicyError)
    async def policy_error(request: Request, error: PolicyError):
        return JSONResponse(
            status_code=409, content={"error": error.code, "message": error.message}
        )

    def operator(value: str | None) -> str:
        expected = os.getenv("SKILLFORGE_OPERATOR_SESSION", "")
        if not value or not expected or not hmac.compare_digest(value, expected):
            raise HTTPException(403, "OPERATOR_SESSION_REQUIRED")
        return "operator-1"

    def run_result(rid: str):
        saved = db.one("SELECT result FROM api_results WHERE run_id=?", (rid,))
        if saved:
            return json.loads(saved[0])
        for event in reversed(db.events(rid)):
            if event["kind"] == "execution.result":
                return json.loads(event["payload"])
        with lock:
            if rid in jobs:
                return dict(jobs[rid])
        row = db.one("SELECT * FROM runs WHERE id=?", (rid,))
        if row:
            return dict(row)
        raise HTTPException(404, "NOT_FOUND")

    # On startup, never replay an interrupted mutation automatically.
    with db.lock:
        interrupted = [
            dict(r)
            for r in db.conn.execute("SELECT * FROM runs WHERE status='RUNNING'")
        ]
        orphaned = [
            r[0]
            for r in db.conn.execute(
                "SELECT run_id FROM api_requests WHERE run_id NOT IN (SELECT id FROM runs)"
            )
        ]
    for row in interrupted:
        with db.transaction():
            db.conn.execute(
                "UPDATE runs SET status='NEEDS_RECONCILIATION' WHERE id=?", (row["id"],)
            )
            db.conn.execute(
                "INSERT OR REPLACE INTO reconciliation_holds VALUES (?,?,?,NULL)",
                (row["input_ref"], row["id"], "PROCESS_INTERRUPTED"),
            )
        save_result(
            {
                "run_id": row["id"],
                "status": "NEEDS_RECONCILIATION",
                "reason_code": "PROCESS_INTERRUPTED",
                "mode": row["mode"],
                "metrics": {
                    "model_calls": None,
                    "tool_calls": None,
                    "latency_ms": None,
                },
            }
        )
    for rid in orphaned:
        save_result(
            {
                "run_id": rid,
                "status": "FAILED",
                "reason_code": "INTERRUPTED_BEFORE_EXECUTION",
                "mode": "unknown",
                "metrics": {"model_calls": 0, "tool_calls": 0, "latency_ms": None},
            }
        )

    @app.post("/api/reconciliations/{oid}/resolve")
    def reconcile(oid: str, x_operator_session: str | None = Header(default=None)):
        op = operator(x_operator_session)
        with db.transaction():
            hold = db.one(
                "SELECT * FROM reconciliation_holds WHERE order_id=? AND resolved_by IS NULL",
                (oid,),
            )
            if not hold:
                raise HTTPException(404, "NO_PENDING_RECONCILIATION")
            if db.one(
                "SELECT 1 FROM runs WHERE input_ref=? AND status='RUNNING'", (oid,)
            ):
                raise HTTPException(409, "RUN_STILL_ACTIVE")
            oracle = independent_oracle(db, oid, "SUCCEEDED")
            if not oracle["safe"]:
                raise HTTPException(409, "UNSAFE_STATE_REQUIRES_MANUAL_REPAIR")
            db.conn.execute(
                "UPDATE reconciliation_holds SET resolved_by=? WHERE order_id=?",
                (op, oid),
            )
        return {
            "order_id": oid,
            "resolved_by": op,
            "state": oracle["actual"],
            "note": "Read-only state inspection; no refund write was retried.",
        }

    @app.get("/health")
    def health():
        nat = ROOT / "artifacts/nat-live-evidence.json"
        nat_ok = False
        if nat.is_file():
            try:
                nat_ok = json.loads(nat.read_text())["result"]["status"] == "SUCCEEDED"
            except (ValueError, KeyError):
                pass
        return {
            "status": "ok",
            "key_configured": bool(os.getenv("NVIDIA_API_KEY")),
            "live_verified": bool(
                db.one("SELECT 1 FROM runs WHERE mode='live' AND status='SUCCEEDED'")
            ),
            "operator_configured": bool(os.getenv("SKILLFORGE_OPERATOR_SESSION")),
            "nat_verified": nat_ok,
            "openshell_verified": False,
        }

    @app.post("/api/runs", status_code=202)
    def submit(body: RunBody, x_operator_session: str | None = Header(default=None)):
        op = operator(x_operator_session) if body.approval_id else None
        if not body.order_id and not body.text:
            raise HTTPException(422, "ORDER_OR_TEXT_REQUIRED")
        payload = digest(body.model_dump(exclude={"request_id"}))
        with lock:
            existing = db.one(
                "SELECT * FROM api_requests WHERE request_id=?", (body.request_id,)
            )
            if existing:
                if existing["payload_hash"] != payload:
                    raise HTTPException(409, "REQUEST_ID_CONFLICT")
                return {"run_id": existing["run_id"], "replayed": True}
            if sum(j["status"] in {"CREATED", "RUNNING"} for j in jobs.values()) >= 8:
                raise HTTPException(429, "QUEUE_FULL")
            rid = "run-" + secrets.token_hex(10)
            with db.transaction():
                db.conn.execute(
                    "INSERT INTO api_requests VALUES (?,?,?)",
                    (body.request_id, payload, rid),
                )
            jobs[rid] = {"run_id": rid, "status": "CREATED"}

        def work():
            started = time.monotonic()
            with lock:
                jobs[rid]["status"] = "RUNNING"
            try:
                oid = body.order_id
                routing = None
                if body.text:
                    routing = route_text(body.text, body.mode)
                    if routing["intent"] != "refund":
                        result = {
                            "run_id": rid,
                            "status": (
                                "NEEDS_INPUT"
                                if routing["intent"] == "clarify"
                                else "INFORMATION"
                            ),
                            "routing": routing,
                            "reason_code": routing["intent"].upper(),
                            "metrics": {
                                "model_calls": routing["model_calls"],
                                "tokens": routing["tokens"],
                                "tool_calls": 0,
                                "latency_ms": None,
                            },
                            "mode": body.mode,
                        }
                        save_result(result)
                        return
                    if oid and oid != routing["order_id"]:
                        raise PolicyError(
                            "ORDER_SCOPE_MISMATCH", "Text and selected order differ"
                        )
                    oid = routing["order_id"]
                remaining = 90 - (time.monotonic() - started)
                if remaining <= 0:
                    raise PolicyError(
                        "RUN_BUDGET_EXCEEDED", "Total request budget exhausted"
                    )
                kwargs = {
                    "mode": body.mode,
                    "approval_id": body.approval_id,
                    "operator_id": op,
                    "run_id": rid,
                    "prompt": body.text,
                    "budget_seconds": remaining,
                }
                result = (
                    service.run(oid, **kwargs)
                    if body.route == "auto"
                    else execute(db, oid, **kwargs)
                )
                if routing:
                    result["routing"] = routing
                    result["common_routing_cost"] = {
                        "model_calls": routing["model_calls"],
                        "tokens": routing["tokens"],
                    }
                save_result(result)
            except Exception as error:
                save_result(
                    {
                        "run_id": rid,
                        "status": "FAILED",
                        "reason_code": getattr(error, "code", type(error).__name__),
                        "mode": body.mode,
                        "metrics": {
                            "model_calls": getattr(error, "model_calls", None),
                            "tokens": None,
                            "tool_calls": None,
                            "latency_ms": round((time.monotonic() - started) * 1000, 3),
                        },
                    }
                )

        pool.submit(work)
        return {"run_id": rid, "status": "CREATED"}

    @app.get("/api/runs/{rid}")
    def get_run(rid: str):
        with lock:
            if rid in jobs:
                return dict(jobs[rid])
        return run_result(rid)

    @app.get("/api/runs/{rid}/events")
    async def get_events(
        rid: str,
        request: Request,
        after: int = 0,
        last_event_id: str | None = Header(default=None),
    ):
        if "text/event-stream" not in request.headers.get("accept", ""):
            return {"events": db.events(rid)}
        if last_event_id:
            try:
                after = max(after, int(last_event_id))
            except ValueError:
                raise HTTPException(422, "INVALID_EVENT_ID")

        async def stream():
            cursor = after
            for _ in range(480):
                if await request.is_disconnected():
                    return
                for event in db.events(rid):
                    if event["seq"] > cursor:
                        cursor = event["seq"]
                        yield f"id: {cursor}\nevent: trace\ndata: {json.dumps(event)}\n\n"
                with lock:
                    state = jobs.get(rid, {})
                if state.get("status") not in {"CREATED", "RUNNING", None}:
                    yield "event: done\ndata: " + json.dumps(state) + "\n\n"
                    return
                row = db.one("SELECT status FROM runs WHERE id=?", (rid,))
                if row and row[0] != "RUNNING":
                    yield "event: done\ndata: " + json.dumps(run_result(rid)) + "\n\n"
                    return
                yield ": heartbeat\n\n"
                await asyncio.sleep(0.25)

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.get("/api/workflows")
    def workflows():
        return service.list()

    @app.get("/api/workflows/{wid}/guidance")
    def export_guidance(wid: str):
        from .skill_export import guidance

        item = service.get(wid)
        if not item:
            raise HTTPException(404, "NOT_FOUND")
        try:
            text = guidance(item)
        except ValueError:
            raise HTTPException(409, "ACTIVE_WORKFLOW_REQUIRED")
        return Response(
            text,
            media_type="text/markdown",
            headers={
                "Content-Disposition": f'attachment; filename="{wid}-guidance.md"'
            },
        )

    @app.post("/api/demo/new-order", status_code=201)
    def new_order(
        body: CaseBody, x_operator_session: str | None = Header(default=None)
    ):
        operator(x_operator_session)
        oid = "demo-" + secrets.token_hex(5)
        load_case(
            db,
            {
                "order_id": oid,
                "amount_krw": 600000 if body.kind == "high" else 89000,
                "return_received": body.kind != "unreceived",
            },
        )
        return {"order_id": oid}

    @app.post("/api/approvals", status_code=201)
    def approval(
        body: ApprovalBody, x_operator_session: str | None = Header(default=None)
    ):
        return db.create_approval(
            operator(x_operator_session), body.order_id, body.amount_krw
        )

    @app.post("/api/demo/discover")
    def discover(x_operator_session: str | None = Header(default=None)):
        operator(x_operator_session)
        return service.discover()

    @app.post("/api/candidates", status_code=201)
    def compile_candidate(x_operator_session: str | None = Header(default=None)):
        operator(x_operator_session)
        return service.compile()

    @app.post("/api/workflows/{wid}/verify")
    def verify(wid: str, x_operator_session: str | None = Header(default=None)):
        operator(x_operator_session)
        return service.verify(wid)

    @app.post("/api/workflows/{wid}/activate")
    def activate(
        wid: str,
        body: ActivateBody,
        x_operator_session: str | None = Header(default=None),
    ):
        operator(x_operator_session)
        item = service.get(wid)
        if not item or item["artifact_hash"] != body.expected_hash:
            raise HTTPException(409, "HASH_MISMATCH")
        return service.activate(wid)

    @app.post("/api/workflows/{wid}/disable")
    def disable(wid: str, x_operator_session: str | None = Header(default=None)):
        operator(x_operator_session)
        if not service.get(wid):
            raise HTTPException(404, "NOT_FOUND")
        with db.transaction():
            db.conn.execute("UPDATE workflows SET state='DISABLED' WHERE id=?", (wid,))
        return service.get(wid)

    @app.post("/api/policy/bump")
    def bump(x_operator_session: str | None = Header(default=None)):
        operator(x_operator_session)
        ph = digest({"revision": secrets.token_hex(8), "limit": 500000})
        with db.transaction():
            db.conn.execute("UPDATE policies SET active=0")
            db.conn.execute("INSERT INTO policies VALUES (?,500000,1)", (ph,))
        return {"policy_hash": ph, "workflows": service.list()}

    @app.get("/api/evaluations")
    def evaluations():
        with db.lock:
            rows = db.conn.execute(
                "SELECT report FROM evaluations ORDER BY rowid DESC LIMIT 10"
            ).fetchall()
        return [
            {k: v for k, v in json.loads(r[0]).items() if k != "runs"} for r in rows
        ]

    @app.post("/api/evaluations")
    def evaluate(x_operator_session: str | None = Header(default=None)):
        operator(x_operator_session)
        return {k: v for k, v in benchmark(service).items() if k != "runs"}

    @app.get("/api/cases")
    def cases():
        return split_manifest()

    root = ROOT / "web" / "dist"
    app.mount(
        "/",
        StaticFiles(directory=str(root if root.exists() else ROOT / "web"), html=True),
        name="console",
    )
    return app


app = create_app()
