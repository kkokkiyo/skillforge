"""Reproducible policy-change proof. No writes to the operating database."""
import argparse
import json
import sqlite3
from pathlib import Path
from backend.app import Database, load_case, split_manifest
from backend.config import ROOT, load_env
from backend.engine import WorkflowService, execute
from backend.governance import PolicyLab


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--saved-live", action="store_true", help="Compile saved local live discovery traces, not new inference")
    parser.add_argument("--live", action="store_true", help="Make two new NVIDIA runs on isolated orders")
    parser.add_argument("--collect-live", action="store_true", help="Collect five fresh successful discovery traces with NVIDIA")
    parser.add_argument("--output", default="artifacts/policy-change-demo-latest.json", help="Output path; defaults to an untracked file to preserve published evidence")
    args = parser.parse_args()
    load_env()
    db = Database()
    service = WorkflowService(db)
    if args.collect_live:
        successes = 0
        for case in [c for c in split_manifest()["discovery"] if c["expected"] == "SUCCEEDED"][:8]:
            isolated = Database()
            try:
                load_case(isolated, case)
                result = execute(isolated, case["order_id"], mode="live")
                rid = result["run_id"]
                with db.transaction():
                    db.conn.execute("INSERT INTO runs VALUES (?,?,?,?,?,?,?,?)", tuple(isolated.one("SELECT * FROM runs WHERE id=?", (rid,))))
                    db.conn.executemany("INSERT INTO events VALUES (?,?,?,?,?,?,?,?)", [tuple(e.values()) for e in isolated.events(rid)])
                successes += result["status"] == "SUCCEEDED"
                print(json.dumps({"discovery_run": rid, "status": result["status"], "successful_sources": successes}), flush=True)
                if successes >= 5:
                    break
            finally:
                isolated.conn.close()
    elif args.saved_live:
        evidence = json.loads((ROOT / "artifacts/workflow-evidence.json").read_text())
        source = sqlite3.connect(f"file:{ROOT / 'artifacts/skillforge.sqlite3'}?mode=ro", uri=True)
        try:
            with db.transaction():
                policy = source.execute("SELECT * FROM policies WHERE hash=?", (evidence["artifact"]["policy_hash"],)).fetchone()
                if not policy:
                    raise RuntimeError("Saved source policy is missing locally")
                db.conn.execute("UPDATE policies SET active=0")
                db.conn.execute("INSERT OR REPLACE INTO policies VALUES (?,?,1)", policy[:2])
                for rid in evidence["artifact"]["source_trace_ids"]:
                    row = source.execute("SELECT * FROM runs WHERE id=?", (rid,)).fetchone()
                    if not row:
                        raise RuntimeError("Saved live source is missing locally")
                    db.conn.execute("INSERT INTO runs VALUES (?,?,?,?,?,?,?,?)", row)
                    db.conn.executemany("INSERT INTO events VALUES (?,?,?,?,?,?,?,?)", source.execute("SELECT * FROM events WHERE run_id=? ORDER BY seq", (rid,)).fetchall())
        finally:
            source.close()
        from backend.compiler import derive_steps
        for rid in evidence["artifact"]["source_trace_ids"]:
            row = db.one("SELECT * FROM runs WHERE id=?", (rid,))
            derive_steps(db.events(rid), row["input_ref"], rid)
    else:
        service.discover()
    original = service.compile()
    service.verify(original["id"])
    original = service.activate(original["id"])
    lab = PolicyLab(service)
    review = lab.preview(original["id"], 300000)
    live_runs = []
    if args.live:
        load_case(db, {"order_id": "policy-live-before", "amount_krw": 350000})
        before = execute(db, "policy-live-before", mode="live")
        live_runs.append({"label": "before-policy-change", "result": before, "events": db.events(before["run_id"])})
    lab.apply(review["id"])
    migrated = lab.rebase(original["id"])
    service.verify(migrated["id"])
    migrated = service.activate(migrated["id"])
    if args.live:
        load_case(db, {"order_id": "policy-live-after", "amount_krw": 350000})
        after = execute(db, "policy-live-after", mode="live")
        live_runs.append({"label": "after-policy-change", "result": after, "events": db.events(after["run_id"])})
    load_case(db, {"order_id": "policy-reuse", "amount_krw": 350000})
    pending = service.run("policy-reuse")
    approval = db.create_approval("operator-1", "policy-reuse", 350000)
    completed = service.run("policy-reuse", approval_id=approval["approval_id"], operator_id="operator-1")
    report = {"source": "new NVIDIA live discovery" if args.collect_live else "saved live traces" if args.saved_live else "scripted mock discovery",
              "original": original, "comparison": review, "migrated": migrated,
              "live_runs": live_runs, "pending": pending, "approved": completed,
              "source_events": {rid: db.events(rid) for rid in original["artifact"]["source_trace_ids"]},
              "discovery_runs": [{**dict(row), "events": db.events(row["id"])} for row in db.conn.execute("SELECT * FROM runs WHERE mode='live' AND input_ref LIKE 'synthetic-order-%'").fetchall()],
              "limitations": "42 paired synthetic replay cases; saved source traces are not new inference. New NVIDIA runs, when requested, are reported separately. No real payment."}
    passed = review["passed"] and migrated["report"]["passed"] and pending["status"] == "AWAITING_APPROVAL" and completed["status"] == "SUCCEEDED"
    if args.live:
        passed = passed and [x["result"]["status"] for x in live_runs] == ["SUCCEEDED", "AWAITING_APPROVAL"]
    report["passed"] = passed
    path = ROOT / args.output
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"passed": passed, "source": report["source"], "paired_cases": review["case_count"], "changed": review["changed_count"], "live_results": [r["result"]["status"] for r in live_runs], "evidence": str(path)}))
    db.conn.close()
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
