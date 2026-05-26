import os
import json
import uvicorn
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from mcp.server import Server
import mcp.types as types
from mcp.server.sse import SseServerTransport

from app.services.persistence.db import init_db
from app.services.persistence.reminder_persistence import (
    save_reminder,
    list_reminders as db_list_reminders,
    modify_reminder as db_modify_reminder,
    delete_reminder as db_delete_reminder,
)
from .tools import REMINDER_TOOLS

# Configure logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("reminder_server")

app = FastAPI(
    title="Travel Assistant - Reminder MCP Server",
    description="MCP tools server exclusive for reminders and itinerary management (CRUD)",
    version="0.1.0"
)

# Allow CORS for development or external connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure database initialization
init_db()

# Create official MCP server and SSE transport
mcp_server = Server("reminder-server")
sse_transport = SseServerTransport("/messages")


@mcp_server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    Lists available tools for reminder management.
    """
    return REMINDER_TOOLS


@mcp_server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """
    Executes reminder CRUD operations interacting with the database via persistence.py.
    """
    logger.info(f"Executing MCP tool (Reminders): '{name}' with arguments: {arguments}")
    
    try:
        if name == "record_reminder":
            title = str(arguments["title"])
            due_time = str(arguments["due_time"])
            note = str(arguments.get("note", ""))
            
            saved = save_reminder(title=title, due_time=due_time, note=note)
            result = {"message": "Reminder created successfully", "reminder": saved}
            
        elif name == "query_reminders":
            reminders = db_list_reminders()
            result = {
                "message": "List of reminders",
                "count": len(reminders),
                "reminders": reminders
            }
                
        elif name == "modify_reminder":
            reminder_id = int(arguments["id"])
            title = arguments.get("title")
            due_time = arguments.get("due_time")
            note = arguments.get("note")
            
            # Convert types if present
            if title is not None:
                title = str(title)
            if due_time is not None:
                due_time = str(due_time)
            if note is not None:
                note = str(note)
                
            res = db_modify_reminder(
                reminder_id=reminder_id,
                title=title,
                due_time=due_time,
                note=note
            )
            result = res
            
        elif name == "delete_reminder":
            reminder_id = int(arguments["id"])
            res = db_delete_reminder(reminder_id=reminder_id)
            result = res
            
        else:
            raise ValueError(f"Reminder tool '{name}' not supported")
            
        result_str = json.dumps(result, ensure_ascii=False)
        logger.info(f"Tool '{name}' executed successfully. Response: {result_str}")
        return [
            types.TextContent(
                type="text",
                text=result_str
            )
        ]
        
    except Exception as e:
        logger.exception(f"Error executing reminder tool '{name}'")
        return [
            types.TextContent(
                type="text",
                text=f"Error in execution of reminder tool '{name}': {str(e)}"
            )
        ]


from starlette.routing import Route

# Define ASGI class wrappers to prevent Starlette from wrapping them with request_response
class SSEASGIApp:
    async def __call__(self, scope, receive, send):
        logger.info("Received SSE connection request for the Reminders MCP server")
        async with sse_transport.connect_sse(scope, receive, send) as (read_stream, write_stream):
            await mcp_server.run(
                read_stream,
                write_stream,
                mcp_server.create_initialization_options()
            )

class MessageASGIApp:
    async def __call__(self, scope, receive, send):
        await sse_transport.handle_post_message(scope, receive, send)

# Register exact routes (both with and without trailing slash to prevent 307 redirects)
app.router.routes.append(Route("/sse", endpoint=SSEASGIApp(), methods=["GET"]))
app.router.routes.append(Route("/sse/", endpoint=SSEASGIApp(), methods=["GET"]))
app.router.routes.append(Route("/messages", endpoint=MessageASGIApp(), methods=["POST"]))
app.router.routes.append(Route("/messages/", endpoint=MessageASGIApp(), methods=["POST"]))


@app.get("/status")
async def status():
    """
    Returns the availability status of the reminder server with complete metadata.
    """
    return {
        "status": "online",
        "tool_count": len(REMINDER_TOOLS),
        "tools": [
            {
                "name": t.name,
                "description": t.description,
                "inputSchema": t.inputSchema
            }
            for t in REMINDER_TOOLS
        ]
    }


def run():
    reload = os.getenv("UVICORN_RELOAD", "false").lower() == "true"
    uvicorn.run("app.mcp.reminder.server:app", host="0.0.0.0", port=8003, reload=reload, reload_dirs=["app"] if reload else None)


if __name__ == "__main__":
    run()
