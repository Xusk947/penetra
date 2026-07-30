"""Generic MCP client tool for agents.

Connects to a Model Context Protocol server over stdio and exposes its tools
so the agent can call them.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from langchain.tools import tool

logger = logging.getLogger(__name__)


def _run_async(coro: Any) -> Any:
    try:
        return asyncio.get_event_loop().run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


@tool
def mcp_client(
    server_command: str,
    server_args: str = "",
    action: str = "list_tools",
    tool_name: str | None = None,
    arguments: str = "{}",
) -> dict[str, Any]:
    """Connect to an MCP server over stdio and list or call tools.

    * ``server_command``: executable that runs the MCP server (e.g. ``python``).
    * ``server_args``: comma-separated arguments (e.g. ``mcp_server.py``).
    * ``action``: ``list_tools`` or ``call_tool``.
    * ``tool_name``: tool to call when action is ``call_tool``.
    * ``arguments``: JSON object with tool arguments.
    """
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
    except ImportError as exc:
        return {"error": f"MCP SDK not installed: {exc}"}

    args = [a.strip() for a in server_args.split(",") if a.strip()] if server_args else []
    params = StdioServerParameters(command=server_command, args=args, env=None)

    async def _execute() -> dict[str, Any]:
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                if action == "list_tools":
                    tools = await session.list_tools()
                    return {"tools": [t.name for t in tools.tools]}
                if action == "call_tool" and tool_name:
                    args_dict = json.loads(arguments or "{}")
                    result = await session.call_tool(tool_name, arguments=args_dict)
                    return {
                        "tool": tool_name,
                        "content": [c.text for c in result.content if hasattr(c, "text")],
                        "is_error": result.isError,
                    }
                return {"error": f"Unknown action: {action}"}

    try:
        return _run_async(_execute())
    except Exception as exc:
        logger.warning("MCP client failed for %s: %s", server_command, exc)
        return {"error": str(exc)}
