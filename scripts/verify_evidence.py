"""Recompute published evaluation aggregates; inspect NAT's concatenated JSON stream."""

import json
from pathlib import Path
from backend.config import ROOT
from backend.evaluation import summarize

folder = ROOT / "artifacts/eval/eval-dc5a773edccd641d"
report = json.loads((folder / "report.json").read_text())
rows = [json.loads(line) for line in (folder / "runs.jsonl").read_text().splitlines()]
assert len(rows) == 120
assert len({r["result"]["run_id"] for r in rows}) == 120
for name in ("react", "manual", "compiled"):
    selected = [r for r in rows if r["arm"] == name]
    assert len(selected) == 40
    assert summarize(selected) == report["summary"][name]
    assert {r["case_id"] for r in selected} == {
        c["id"] for c in json.loads((folder / "manifest.json").read_text())["cases"]
    }
    for row in selected:
        assert [e["seq"] for e in row["events"]] == list(
            range(1, len(row["events"]) + 1)
        )
spans = json.loads((ROOT / "artifacts/nat-span-evidence.json").read_text())
events = spans["events"]
from collections import Counter
counts = Counter(e["payload"]["event_type"] for e in events)
assert counts["FUNCTION_START"] == 7 and counts["FUNCTION_END"] == 7
starts = {e["payload"]["UUID"] for e in events if e["payload"]["event_type"] == "FUNCTION_START"}
ends = {e["payload"]["UUID"] for e in events if e["payload"]["event_type"] == "FUNCTION_END"}
assert starts == ends
result = {"aggregates_recomputed": True, "evaluation_id": report["id"], "paired_runs": len(rows), "nat_span_mode": spans["mode"], "nat_event_counts": dict(counts), "nat_spans_paired": True}
(ROOT / "artifacts/evidence-integrity.json").write_text(json.dumps(result, indent=2))
print(json.dumps(result))
