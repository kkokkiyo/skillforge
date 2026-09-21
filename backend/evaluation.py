"""Paired, isolated executor comparison with trace-recomputable metrics."""

import json, math, os, platform, random, secrets, time
from collections import Counter
from datetime import datetime, timezone
from importlib.metadata import version, PackageNotFoundError
from pathlib import Path
from .app import (
    Database,
    independent_oracle,
    load_case,
    split_manifest,
    TOOL_SCHEMA_HASH,
)
from .engine import execute, manual_workflow, policy_hash, NVIDIAClient


def percentile(values, q):
    values = sorted(values)
    return values[max(0, math.ceil(len(values) * q) - 1)] if values else None


def summarize(rows):
    durations = [r["result"]["metrics"]["latency_ms"] for r in rows]
    normal = [r for r in rows if r["expected"] == "SUCCEEDED"]
    successful = [r["result"]["metrics"]["latency_ms"] for r in normal if r["passed"]]
    completed = [e for r in rows for e in r["events"] if e["kind"] == "model.completed"]
    usage = [json.loads(e["usage_json"]) for e in completed if e.get("usage_json")]
    unsafe_attempts = 0
    for row in rows:
        requested = None
        for event in row["events"]:
            if event["kind"] == "tool.requested":
                requested = json.loads(event["payload"])["tool"]
            if event["kind"] == "policy.decided" and requested == "issue_refund":
                unsafe_attempts += 1
    return {
        "n": len(rows),
        "passed": sum(r["passed"] for r in rows),
        "unsafe": sum(not r["oracle"]["safe"] for r in rows),
        "normal_n": len(normal),
        "normal_passed": sum(r["passed"] for r in normal),
        "unsafe_attempts_blocked": unsafe_attempts,
        "model_calls": sum(r["result"]["metrics"]["model_calls"] for r in rows),
        "tool_calls": sum(r["result"]["metrics"]["tool_calls"] for r in rows),
        "reported_tokens": (
            sum(
                u["total_tokens"]
                for u in usage
                if isinstance(u.get("total_tokens"), int)
            )
            if usage
            else None
        ),
        "usage_responses": len(usage),
        "model_responses": len(completed),
        "usage_missing_responses": len(completed) - len(usage),
        "p50_ms": percentile(durations, 0.5),
        "p95_ms": percentile(durations, 0.95),
        "normal_success_p50_ms": percentile(successful, 0.5),
        "normal_success_p95_ms": percentile(successful, 0.95),
        "failures_by_reason": dict(
            Counter(
                r["result"]["reason_code"] or r["result"]["status"]
                for r in rows
                if not r["passed"]
            )
        ),
        "routing_error_rate": None,
        "routing_note": "Executor comparison; common text routing excluded equally. Router has separate integration tests.",
        "approval_wait_ms": None,
        "approval_wait_note": "Pending is terminal in these fixtures; operator think time not simulated.",
    }


def benchmark(service, repeats=1, live=False):
    active = next((x for x in service.list() if x["state"] == "ACTIVE"), None)
    if not active:
        raise ValueError("Activate a verified workflow first")
    eid = "eval-" + secrets.token_hex(8)
    folder = Path(__file__).resolve().parents[1] / "artifacts" / "eval" / eid
    folder.mkdir(parents=True, exist_ok=True)
    manifest = {
        "id": eid,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "mode": "live" if live else "mock",
        "model": NVIDIAClient().model if live else None,
        "temperature": 1.0 if live else None,
        "top_p": 0.95 if live else None,
        "max_tokens": 2048 if live else None,
        "minimum_request_interval_seconds": float(
            os.getenv("NVIDIA_MIN_INTERVAL", "2.1")
        ),
        "concurrency": 1,
        "cache": False,
        "warmup": False,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "workflow_hash": active["artifact_hash"],
        "policy_hash": policy_hash(service.db),
        "tool_schema_hash": TOOL_SCHEMA_HASH,
        "split_hash": split_manifest()["split_hash"],
        "split": "test",
        "repetitions": repeats,
        "order_seed": 20260920,
        "dataset_note": "Synthetic repeated refund states; not a held-out natural-language generalization benchmark. Previous development evaluation exists.",
        "timeout_seconds": 90,
        "request_timeout_seconds": 30,
        "retry_limit": 1,
        "cases": split_manifest()["test"],
    }
    for package in ["nvidia-nat", "mcp", "fastapi"]:
        try:
            manifest[package] = version(package)
        except PackageNotFoundError:
            manifest[package] = None
    (folder / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    report = {
        **{k: v for k, v in manifest.items() if k != "cases"},
        "note": "Synthetic executor-only comparison. Mock results cannot establish LLM speedup. Failures retained; inspect provider error coverage before comparing latency.",
        "runs": [],
    }
    rng = random.Random(manifest["order_seed"])
    with (folder / "runs.jsonl").open("w", encoding="utf-8") as output:
        for rep in range(repeats):
            for case in manifest["cases"]:
                names = ["react", "manual", "compiled"]
                rng.shuffle(names)
                for name in names:
                    db = Database()
                    try:
                        with db.transaction():
                            db.conn.execute("UPDATE policies SET active=0")
                            limit = service.db.one(
                                "SELECT approval_limit_krw FROM policies WHERE active=1"
                            )[0]
                            db.conn.execute(
                                "INSERT OR REPLACE INTO policies VALUES (?,?,1)",
                                (policy_hash(service.db), limit),
                            )
                        load_case(db, case)
                        artifact = (
                            manual_workflow(db)
                            if name == "manual"
                            else active["artifact"] if name == "compiled" else None
                        )
                        result = execute(
                            db,
                            case["order_id"],
                            mode="live" if live else "mock",
                            artifact=artifact,
                        )
                        oracle = independent_oracle(
                            db, case["order_id"], case["expected"]
                        )
                        row = {
                            "case_id": case["id"],
                            "arm": name,
                            "rep": rep,
                            "expected": case["expected"],
                            "result": result,
                            "oracle": oracle,
                            "passed": result["status"] == case["expected"]
                            and oracle["passed"],
                            "events": db.events(result["run_id"]),
                        }
                        report["runs"].append(row)
                        output.write(json.dumps(row, ensure_ascii=False) + "\n")
                        output.flush()
                    finally:
                        db.conn.close()
    report["summary"] = {
        name: summarize([r for r in report["runs"] if r["arm"] == name])
        for name in ("react", "manual", "compiled")
    }
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    with service.db.transaction():
        service.db.conn.execute(
            "INSERT INTO evaluations VALUES (?,?)", (eid, json.dumps(report))
        )
    (folder / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (folder / "summary.json").write_text(
        json.dumps(report["summary"], indent=2), encoding="utf-8"
    )
    md = f"# SkillForge evaluation {eid}\n\nMode: **{report['mode']}**. {report['note']}\n\n| Arm | Cases | Pass | Unsafe commit | Model calls | p50 ms | p95 ms |\n|---|---:|---:|---:|---:|---:|---:|\n"
    for name, s in report["summary"].items():
        md += f"| {name} | {s['n']} | {s['passed']} | {s['unsafe']} | {s['model_calls']} | {s['p50_ms']} | {s['p95_ms']} |\n"
    md += (
        "\n## Failure and usage coverage\n\n```json\n"
        + json.dumps(report["summary"], indent=2)
        + "\n```\n\nEvery measurement is backed by runs.jsonl; manifest.json fixes settings and split.\n"
    )
    (folder / "report.md").write_text(md, encoding="utf-8")
    return report
