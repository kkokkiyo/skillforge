"""Export an active workflow as human guidance, not an executable runtime skill."""

from .engine import validate_workflow, digest


def guidance(workflow: dict) -> str:
    artifact = workflow["artifact"]
    validate_workflow(artifact)
    if workflow["state"] != "ACTIVE" or digest(artifact) != workflow["artifact_hash"]:
        raise ValueError("Only an unchanged ACTIVE workflow can be exported")
    lines = [
        "# SkillForge refund workflow guidance",
        "",
        "Format: general human-readable Markdown. Not a verified NemoClaw/OpenClaw runtime skill.",
        "",
        "## Identity",
        f"Workflow: {workflow['id']}",
        f"Artifact SHA-256: {workflow['artifact_hash']}",
        f"Policy: {artifact['policy_hash']}",
        f"Source: {artifact['source_mode']}",
        "",
        "## Applies to",
        "A synthetic full refund for an owned order with a received return and no existing refund.",
        "The server must validate the current policy, quote, amount and order version.",
        "High-value refunds need a bound operator approval. This document grants no approval.",
        "",
        "## Exclusions",
        "No real payments, partial refunds, arbitrary code, remote shell, or authority from model text.",
        "Policy/schema changes invalidate automatic use. Do not retry writes after an uncertain execution.",
        "",
        "## Invocation",
        "Use the local SkillForge console with route=auto, or POST /api/runs with a unique request_id and order_id.",
        "Check the returned run_id via GET /api/runs/{run_id}; inspect SSE events before relying on the outcome.",
        "",
        "## Steps",
    ]
    for index, step in enumerate(artifact["steps"], 1):
        lines.append(
            f"{index}. {step['tool']}: "
            + ", ".join(f"{k} <- {v['ref']}" for k, v in step["args"].items())
        )
    lines += ["", "## Evidence"] + artifact["source_trace_ids"]
    return "\n".join(lines) + "\n"
