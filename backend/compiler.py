"""Compile observed requests into references under the narrow refund contract."""
import json
from .app import PolicyError, TOOLS

STEP_NAMES = {
    "get_order": "order", "get_return_status": "returned",
    "get_refund_policy": "policy", "quote_refund": "quote",
    "issue_refund": "refund", "verify_refund": "verify",
}


def derive_steps(events, order_id, run_id):
    """Provenance is a claim: verify its type, value and earlier completion.

    No fuzzy value matching, model-generated expressions or copied literal IDs.
    The caller validates the resulting sequence against the domain DSL.
    """
    symbols = {"input.order_id": order_id, "context.idempotency_key": run_id}
    steps, pending = [], None
    if [e["seq"] for e in events] != list(range(1, len(events) + 1)):
        raise PolicyError("TRACE_INCOMPLETE", "Non-contiguous events")
    for event in events:
        payload = json.loads(event["payload"])
        if event["kind"] == "tool.requested":
            tool, args = payload["tool"], payload["args"]
            refs = json.loads(event["provenance"])
            if pending or tool not in STEP_NAMES or set(args) != set(TOOLS[tool]) or set(refs) != set(args):
                raise PolicyError("UNSUPPORTED_TRACE", "Unsupported request contract")
            bindings = {}
            for key, value in args.items():
                # Explicit argument contracts disambiguate equal string values.
                permitted = {"order_id": "input.order_id", "quote_id": "steps.quote.quote_id",
                             "idempotency_key": "context.idempotency_key"}[key]
                ref = refs[key]
                # Trace redaction intentionally hides idempotency_key. It is
                # regenerated from the trusted run context, never copied.
                matches = value == symbols.get(ref)
                if key == "idempotency_key" and value == "[REDACTED]":
                    matches = True
                if ref != permitted or ref not in symbols or type(value) is not TOOLS[tool][key] or not matches:
                    raise PolicyError("INVALID_PROVENANCE", "Reference type, value or temporal scope mismatch")
                bindings[key] = {"ref": ref}
            steps.append({"id": STEP_NAMES[tool], "tool": tool, "args": bindings})
            pending = tool
        elif event["kind"] == "tool.completed":
            if pending != payload["tool"]:
                raise PolicyError("TRACE_INCOMPLETE", "Unpaired completion")
            if pending == "quote_refund":
                value = payload["result"].get("quote_id")
                if not isinstance(value, str) or not value:
                    raise PolicyError("INVALID_PROVENANCE", "Quote output must be a string")
                symbols["steps.quote.quote_id"] = value
            pending = None
    result = next((json.loads(e["payload"]) for e in reversed(events) if e["kind"] == "execution.result"), {})
    if pending or not events or events[-1]["kind"] != "run.completed" or result.get("status") != "SUCCEEDED" or not result.get("oracle", {}).get("passed"):
        raise PolicyError("TRACE_INCOMPLETE", "Successful oracle and completed trace required")
    return steps
