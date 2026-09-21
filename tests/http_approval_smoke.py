import json, threading, urllib.request, urllib.error, sys, os, secrets

from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend import server

server.DB = server.Database()
session = secrets.token_urlsafe(32)
os.environ["SKILLFORGE_OPERATOR_SESSION"] = session
httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
thread = threading.Thread(target=httpd.serve_forever, daemon=True)
thread.start()
base = f"http://127.0.0.1:{httpd.server_port}"


def post(path, body, headers=None):
    req = urllib.request.Request(
        base + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    with urllib.request.urlopen(req) as r:
        return r.status, json.load(r)


try:
    try:
        post(
            "/api/approvals",
            {"order_id": "order-002", "amount_krw": 600000},
            {"X-Operator-Id": "operator-1"},
        )
        raise AssertionError("untrusted operator header was accepted")
    except urllib.error.HTTPError as error:
        assert error.code == 403
    status, approval = post(
        "/api/approvals",
        {"order_id": "order-002", "amount_krw": 600000},
        {"X-Operator-Session": session},
    )
    assert status == 201 and approval["approval_id"]
    status, result = post(
        "/api/runs",
        {"order_id": "order-002", "approval_id": approval["approval_id"]},
        {"X-Operator-Session": session},
    )
    assert status == 202 and result["status"] == "SUCCEEDED", result
    print(
        json.dumps(
            {
                "approval_status": status,
                "approval_id_present": True,
                "run_status": result["status"],
                "run_id": result["run_id"],
            }
        )
    )
finally:
    httpd.shutdown()
    httpd.server_close()
    thread.join()
