import anyio
from mcp import Client

from pwn_mcp.server import mcp


def test_server_lists_tools():
    async def run():
        async with Client(mcp) as client:
            tools = await client.list_tools()
            return {t.name for t in tools.tools}

    names = anyio.run(run)
    assert "server_info" in names
