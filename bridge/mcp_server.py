#!/usr/bin/env python3
"""Biovector MCP Server — exposes workout tracking tools to LLM agents.

Run with:
    python -m bridge.mcp_server
    
Or register in your MCP client config:
    {
        "mcpServers": {
            "biovector": {
                "command": "python",
                "args": ["-m", "bridge.mcp_server"],
                "cwd": "/path/to/biovector"
            }
        }
    }
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, Resource

from bridge.tools import (
    add_set,
    get_workout_history,
    get_exercise_stats,
    get_1rm_progression,
    get_recent_sessions,
    get_session_detail,
    list_exercises,
    get_weekly_summary,
    get_strength_overview,
)

server = Server("biovector")

# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS = [
    Tool(
        name="add_set",
        description="Log a new exercise set (weight, reps, exercise name)",
        inputSchema={
            "type": "object",
            "properties": {
                "exercise_name": {"type": "string", "description": "Exercise name, short code, or ID"},
                "weight": {"type": "number", "description": "Weight in kg"},
                "reps": {"type": "integer", "description": "Number of reps"},
                "session_name": {"type": "string", "description": "Optional workout/session name", "default": ""},
                "notes": {"type": "string", "description": "Optional notes", "default": ""},
            },
            "required": ["exercise_name", "weight", "reps"],
        },
    ),
    Tool(
        name="get_workout_history",
        description="Retrieve workout history, optionally filtered by exercise",
        inputSchema={
            "type": "object",
            "properties": {
                "exercise_name": {"type": "string", "description": "Filter by exercise (empty for all)", "default": ""},
                "days": {"type": "integer", "description": "Lookback period in days", "default": 90},
                "limit": {"type": "integer", "description": "Max sets to return", "default": 20},
            },
        },
    ),
    Tool(
        name="get_exercise_stats",
        description="Get statistics and progression for a specific exercise",
        inputSchema={
            "type": "object",
            "properties": {
                "exercise_name": {"type": "string", "description": "Exercise name"},
                "days": {"type": "integer", "description": "Lookback period", "default": 90},
            },
            "required": ["exercise_name"],
        },
    ),
    Tool(
        name="get_1rm_progression",
        description="Track estimated 1RM progression over time for an exercise",
        inputSchema={
            "type": "object",
            "properties": {
                "exercise_name": {"type": "string", "description": "Exercise name"},
                "limit": {"type": "integer", "description": "Max data points", "default": 20},
            },
            "required": ["exercise_name"],
        },
    ),
    Tool(
        name="get_recent_sessions",
        description="Get the most recent workout sessions",
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Number of sessions", "default": 5},
            },
        },
    ),
    Tool(
        name="get_session_detail",
        description="Get detailed breakdown of a specific workout session",
        inputSchema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session ID"},
            },
            "required": ["session_id"],
        },
    ),
    Tool(
        name="list_exercises",
        description="List available exercises, optionally filtered by category or search term",
        inputSchema={
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "Equipment type filter", "default": ""},
                "search": {"type": "string", "description": "Search term", "default": ""},
            },
        },
    ),
    Tool(
        name="get_weekly_summary",
        description="Get weekly training volume summary",
        inputSchema={
            "type": "object",
            "properties": {
                "weeks": {"type": "integer", "description": "Weeks to summarize", "default": 8},
            },
        },
    ),
    Tool(
        name="get_strength_overview",
        description="Overview of current strength levels — best recent 1RM per exercise",
        inputSchema={
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Lookback period", "default": 90},
            },
        },
    ),
]

TOOL_HANDLERS = {
    "add_set": add_set,
    "get_workout_history": get_workout_history,
    "get_exercise_stats": get_exercise_stats,
    "get_1rm_progression": get_1rm_progression,
    "get_recent_sessions": get_recent_sessions,
    "get_session_detail": get_session_detail,
    "list_exercises": list_exercises,
    "get_weekly_summary": get_weekly_summary,
    "get_strength_overview": get_strength_overview,
}


@server.list_tools()
async def handle_list_tools():
    return TOOL_DEFINITIONS


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict):
    handler = TOOL_HANDLERS.get(name)
    if not handler:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]
    
    try:
        result = handler(**arguments)
        return [TextContent(type="text", text=result)]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {e}")]


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------

@server.list_resources()
async def handle_list_resources():
    return [
        Resource(
            uri="biovector://exercises",
            name="Exercise Definitions",
            description="All exercise definitions with biomechanical coefficients",
            mimeType="application/json",
        ),
        Resource(
            uri="biovector://sessions/recent",
            name="Recent Sessions",
            description="Last 10 workout sessions",
            mimeType="text/plain",
        ),
    ]


@server.read_resource()
async def handle_read_resource(uri: str):
    from biovector.core import Biovector, DATA_REF
    
    if uri == "biovector://exercises":
        data = json.loads((DATA_REF / "exercises.json").read_text())
        return json.dumps(data, indent=2)
    elif uri == "biovector://sessions/recent":
        return get_recent_sessions(10)
    else:
        return f"Unknown resource: {uri}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
