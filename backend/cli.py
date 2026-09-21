"""Local CLI: python -m backend.cli check|demo|live|serve."""

import json
import os
import secrets
import sys
from pathlib import Path
from .config import ROOT, load_env


def main():
    load_env()
    action = sys.argv[1] if len(sys.argv) > 1 else "check"
    if action == "check":
        print(
            json.dumps(
                {
                    "key_configured": bool(os.getenv("NVIDIA_API_KEY")),
                    "operator_configured": bool(
                        os.getenv("SKILLFORGE_OPERATOR_SESSION")
                    ),
                }
            )
        )
        return
    if action == "serve":
        if not os.getenv("SKILLFORGE_OPERATOR_SESSION"):
            value = secrets.token_urlsafe(32)
            path = ROOT / ".env.local"
            with path.open("a", encoding="utf-8") as f:
                f.write("\nSKILLFORGE_OPERATOR_SESSION=" + value + "\n")
            path.chmod(0o600)
            os.environ["SKILLFORGE_OPERATOR_SESSION"] = value
            print(
                "Operator token saved in .env.local. Enter it in the local console; do not publish it."
            )
        import uvicorn

        uvicorn.run(
            "backend.api:app", host="127.0.0.1", port=int(os.getenv("PORT", "8090"))
        )
        return
    from .app import Database, load_case
    from .engine import execute, WorkflowService
    from .evaluation import benchmark

    folder = ROOT / "artifacts"
    folder.mkdir(exist_ok=True)
    if action == "live":
        db = Database(str(folder / "skillforge.sqlite3"))
        oid = "live-" + secrets.token_hex(6)
        load_case(db, {"order_id": oid, "amount_krw": 89000, "return_received": True})
        result = execute(db, oid, mode="live", budget_seconds=90)
        (folder / "live-evidence.json").write_text(
            json.dumps(
                {"result": result, "events": db.events(result["run_id"])},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(0 if result["status"] == "SUCCEEDED" else 1)
    if action == "demo":
        db = Database()
        service = WorkflowService(db)
        service.discover()
        candidate = service.compile()
        service.verify(candidate["id"])
        service.activate(candidate["id"])
        report = benchmark(service)
        print(json.dumps({"id": report["id"], "summary": report["summary"]}))
        return
    raise SystemExit("Usage: python -m backend.cli check|demo|live|serve")


if __name__ == "__main__":
    main()
