"""Deterministic HTTP full lifecycle, isolated DB and random session."""

import json, os, secrets, threading, urllib.request
from backend import webserver as server
from backend.app import Database

server.DB = Database()
session = secrets.token_urlsafe(32)
os.environ["SKILLFORGE_OPERATOR_SESSION"] = session
httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
thread = threading.Thread(target=httpd.serve_forever, daemon=True)
thread.start()


def post(path, body):
    request = urllib.request.Request(
        f"http://127.0.0.1:{httpd.server_port}" + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "X-Operator-Session": session},
    )
    with urllib.request.urlopen(request) as response:
        return json.load(response)


try:
    assert len(post("/api/demo/discover", {})["new_runs"]) == 30
    candidate = post("/api/candidates", {})
    wid = candidate["id"]
    assert post(f"/api/workflows/{wid}/verify", {})["report"]["passed"]
    assert post(f"/api/workflows/{wid}/activate", {})["state"] == "ACTIVE"
    order = post("/api/demo/new-order", {"kind": "high"})["order_id"]
    pending = post("/api/runs", {"order_id": order})
    assert pending["status"] == "AWAITING_APPROVAL"
    approval = post(
        "/api/approvals",
        {"order_id": order, "amount_krw": pending["quote"]["amount_krw"]},
    )
    assert (
        post("/api/runs", {"order_id": order, "approval_id": approval["approval_id"]})[
            "status"
        ]
        == "SUCCEEDED"
    )
    report = post("/api/evaluations", {})
    assert all(
        x["passed"] == 40 and x["unsafe"] == 0 for x in report["summary"].values()
    )
    assert post("/api/policy/bump", {})["workflows"][0]["state"] == "STALE"
    print(
        json.dumps(
            {
                "discovery": 30,
                "validation": 30,
                "evaluation": 120,
                "approval_resume": True,
                "policy_invalidation": True,
            }
        )
    )
finally:
    httpd.shutdown()
    httpd.server_close()
    thread.join()
