"""Real MCP stdio transport; all tools share the policy gateway. Synthetic DB only."""

import secrets
from mcp.server.mcpserver import MCPServer
from .app import Database, Gateway, Trace

mcp = MCPServer("SkillForge synthetic refunds")
db = Database()
gateway = Gateway(db, Trace(db, "mcp-" + secrets.token_hex(8), "mcp", "stdio-session"))


@mcp.tool()
def get_order(order_id: str) -> dict:
    return gateway.call("get_order", {"order_id": order_id})


@mcp.tool()
def get_return_status(order_id: str) -> dict:
    return gateway.call("get_return_status", {"order_id": order_id})


@mcp.tool()
def get_refund_policy(order_id: str) -> dict:
    return gateway.call("get_refund_policy", {"order_id": order_id})


@mcp.tool()
def quote_refund(order_id: str) -> dict:
    return gateway.call("quote_refund", {"order_id": order_id})


@mcp.tool()
def issue_refund(order_id: str, quote_id: str, idempotency_key: str) -> dict:
    return gateway.call(
        "issue_refund",
        {
            "order_id": order_id,
            "quote_id": quote_id,
            "idempotency_key": idempotency_key,
        },
    )


@mcp.tool()
def verify_refund(order_id: str) -> dict:
    return gateway.call("verify_refund", {"order_id": order_id})


if __name__ == "__main__":
    mcp.run(transport="stdio")
