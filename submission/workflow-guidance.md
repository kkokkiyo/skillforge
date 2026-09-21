# SkillForge refund workflow guidance

Format: general human-readable Markdown. Not a verified NemoClaw/OpenClaw runtime skill.

## Identity
Workflow: workflow-b879b5296ada
Artifact SHA-256: c455c67eef757f6d15c378578c8439ad96c089783296111bf16a7eb612a9fd62
Policy: 1637656d8c47b29f690961004b2b54bf44204bd88ea61b47aa5d8d6dc6eb96e9
Source: live

## Applies to
A synthetic full refund for an owned order with a received return and no existing refund.
The server must validate the current policy, quote, amount and order version.
High-value refunds need a bound operator approval. This document grants no approval.

## Exclusions
No real payments, partial refunds, arbitrary code, remote shell, or authority from model text.
Policy/schema changes invalidate automatic use. Do not retry writes after an uncertain execution.

## Invocation
Use the local SkillForge console with route=auto, or POST /api/runs with a unique request_id and order_id.
Check the returned run_id via GET /api/runs/{run_id}; inspect SSE events before relying on the outcome.

## Steps
1. get_order: order_id <- input.order_id
2. get_return_status: order_id <- input.order_id
3. get_refund_policy: order_id <- input.order_id
4. quote_refund: order_id <- input.order_id
5. issue_refund: order_id <- input.order_id, quote_id <- steps.quote.quote_id, idempotency_key <- context.idempotency_key
6. verify_refund: order_id <- input.order_id

## Evidence
run-98bfe22b34f04555a8dd
run-33bfa2007a122c3ab51e
run-79c5279e59394ac1c5c6
run-01ae5228cb7ddeb073ce
run-93b83348de334a277999
