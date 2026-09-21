import json
from backend.config import ROOT
from backend.app import Database
from backend.engine import WorkflowService
from backend.skill_export import guidance

service = WorkflowService(Database(str(ROOT / "artifacts/skillforge.sqlite3")))
active = next(x for x in service.list() if x["state"] == "ACTIVE")
verified = service.verify(active["id"])
assert verified["report"]["passed"]
active = service.activate(active["id"])
folder = ROOT / "submission"
folder.mkdir(exist_ok=True)
(folder / "workflow-guidance.md").write_text(guidance(active), encoding="utf-8")
(ROOT / "artifacts/workflow-evidence.json").write_text(
    json.dumps(active, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(
    json.dumps(
        {
            "workflow": active["id"],
            "source_mode": active["artifact"]["source_mode"],
            "support": active["artifact"]["support_count"],
            "validation_count": active["report"]["count"],
            "trace_complete": all(
                r["trace_complete"] for r in active["report"]["cases"]
            ),
        }
    )
)
