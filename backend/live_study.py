"""Explicit, bounded live evidence run: 5 discovery successes + 40 test cases."""

import json
from .config import ROOT, load_env
from .app import Database, load_case, split_manifest
from .engine import WorkflowService, execute
from .evaluation import benchmark

load_env()
db = Database(str(ROOT / "artifacts/skillforge.sqlite3"))
service = WorkflowService(db)
cases = [c for c in split_manifest()["discovery"] if c["expected"] == "SUCCEEDED"][:5]
for case in cases:
    if db.one("SELECT 1 FROM orders WHERE id=?", (case["order_id"],)):
        continue
    load_case(db, case)
    result = execute(db, case["order_id"], mode="live", budget_seconds=180)
    print(json.dumps({"stage": "discovery", "run": result}), flush=True)
    if result["status"] != "SUCCEEDED":
        raise SystemExit("Live discovery failed; evidence retained")
workflow = service.compile()
assert workflow["artifact"]["source_mode"] == "live"
service.verify(workflow["id"])
service.activate(workflow["id"])
print(json.dumps({"stage": "activated", "workflow_id": workflow["id"]}), flush=True)
report = benchmark(service, live=True)
print(
    json.dumps(
        {"stage": "evaluation", "id": report["id"], "summary": report["summary"]}
    ),
    flush=True,
)
