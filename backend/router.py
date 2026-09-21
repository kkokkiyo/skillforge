"""Bounded intent extraction. Model output cannot authorize an order or refund."""

import json
import re
import time
from .engine import NVIDIAClient
from .app import PolicyError

ORDER_PATTERN = re.compile(
    r"\b(?:synthetic-order-\d{3}|order-\d{3}|(?:demo|live)-[a-f0-9]{10,12})\b"
)


def route_text(text: str, mode: str = "mock", client=None) -> dict:
    ids = list(dict.fromkeys(ORDER_PATTERN.findall(text)))
    if len(ids) != 1:
        return {
            "intent": "clarify",
            "order_id": None,
            "reason": "주문 ID 하나를 명확히 입력해 주세요.",
            "model_calls": 0,
            "tokens": None,
        }
    if mode == "mock":
        intent = (
            "refund"
            if any(t in text.lower() for t in ("환불", "반품", "refund", "return"))
            else (
                "status"
                if any(t in text.lower() for t in ("상태", "조회", "status"))
                else "unsupported"
            )
        )
        return {
            "intent": intent,
            "order_id": ids[0],
            "model_calls": 0,
            "tokens": None,
            "source": "mock-rule",
        }
    client = client or NVIDIAClient()
    tools = [
        {
            "type": "function",
            "function": {
                "name": "classify_request",
                "description": "Classify the request; never perform business actions.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "intent": {
                            "type": "string",
                            "enum": ["refund", "status", "unsupported", "clarify"],
                        },
                        "order_id": {"type": "string"},
                    },
                    "required": ["intent", "order_id"],
                    "additionalProperties": False,
                },
            },
        }
    ]
    messages = [
        {
            "role": "system",
            "content": "Classify the user request using classify_request exactly once. Return the exact order ID from the user. Refund requests include Korean 환불/반품. No business tools are available.",
        },
        {"role": "user", "content": text},
    ]
    start = time.monotonic()
    attempts = 0
    for attempt in range(2):
        remaining = 30 - (time.monotonic() - start)
        if remaining <= 0:
            raise TimeoutError("INTENT_BUDGET_EXCEEDED")
        attempts += 1
        try:
            response = client.complete(messages, tools, remaining)
            break
        except PolicyError as error:
            error.model_calls = attempts
            if attempt or error.code not in {
                "NVIDIA_HTTP_429",
                "NVIDIA_HTTP_500",
                "NVIDIA_HTTP_503",
            }:
                raise
            delay = getattr(error, "retry_after", 0)
            if delay >= 30 - (time.monotonic() - start):
                raise
            if delay:
                time.sleep(delay)
    calls = response["choices"][0]["message"].get("tool_calls") or []
    if len(calls) != 1 or calls[0]["function"]["name"] != "classify_request":
        raise PolicyError("INVALID_INTENT", "A single structured intent is required")
    result = json.loads(calls[0]["function"]["arguments"])
    if (
        set(result) != {"intent", "order_id"}
        or result["intent"] not in {"refund", "status", "unsupported", "clarify"}
        or result["order_id"] != ids[0]
    ):
        raise PolicyError("INVALID_INTENT", "Intent or order binding failed")
    return {
        **result,
        "source": "live",
        "model_calls": attempts,
        "tokens": response.get("usage", {}).get("total_tokens"),
        "model": client.model,
    }
