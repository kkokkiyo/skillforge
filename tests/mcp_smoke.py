import asyncio, json, sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    async with stdio_client(
        StdioServerParameters(command=sys.executable, args=["-m", "backend.mcp_server"])
    ) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            names = [t.name for t in (await session.list_tools()).tools]
            assert len(names) == 6
            quote = await session.call_tool("quote_refund", {"order_id": "order-001"})
            data = json.loads(quote.content[0].text)
            result = await session.call_tool(
                "issue_refund",
                {
                    "order_id": "order-001",
                    "quote_id": data["quote_id"],
                    "idempotency_key": "mcp-smoke",
                },
            )
            assert not result.is_error
            check = await session.call_tool("verify_refund", {"order_id": "order-001"})
            assert json.loads(check.content[0].text)["committed"]
            bad = await session.call_tool("get_order", {"order_id": "order-003"})
            assert bad.is_error
            record = {
                "tools": names,
                "refund_verified": True,
                "ownership_denied": True,
                "transport": "stdio",
            }
            Path("artifacts/mcp-evidence.json").write_text(json.dumps(record, indent=2))
            print(json.dumps(record))


asyncio.run(main())
