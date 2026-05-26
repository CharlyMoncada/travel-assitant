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
from app.services.persistence.expense_persistence import (
    save_expense,
    get_expense_summary,
    modify_expense as db_modify_expense,
    delete_expense as db_delete_expense,
)
from .tools import EXPENSE_TOOLS

# Configure logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("finance_server")

app = FastAPI(
    title="Travel Assistant - Finance MCP Server",
    description="MCP tools server for financial management (expenses, summary, CRUD)",
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
mcp_server = Server("finance-server")
sse_transport = SseServerTransport("/messages")


@mcp_server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    Lists available tools for expense management.
    """
    return EXPENSE_TOOLS


@mcp_server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """
    Executes expense CRUD operations interacting with the database via persistence.py.
    """
    logger.info(f"Executing MCP tool (Expenses): '{name}' with arguments: {arguments}")
    
    try:
        if name == "record_expense":
            amount = float(arguments["amount"])
            description = str(arguments["description"])
            category = str(arguments["category"])
            
            saved = save_expense(description=description, amount=amount, category=category)
            result = {"message": "Expense recorded successfully", "expense": saved}
            
        elif name == "query_expenses":
            category_filter = arguments.get("category")
            summary = get_expense_summary()
            
            # If category filter is specified, filter the items
            if category_filter:
                cat_lower = category_filter.lower()
                filtered_items = [
                    item for item in summary["items"]
                    if item.get("category") and item["category"].lower() == cat_lower
                ]
                # Recalculate total and count for the filter
                filtered_total = sum(item["amount"] for item in filtered_items)
                result = {
                    "message": f"Expense summary filtered by category '{category_filter}'",
                    "summary": {
                        "total": filtered_total,
                        "count": len(filtered_items),
                        "by_category": {category_filter: filtered_total} if filtered_items else {},
                        "items": filtered_items
                    }
                }
            else:
                result = {"message": "Total expense summary", "summary": summary}
        
        elif name == "budget":
            # Dedicated tool to get budget summary
            summary = get_expense_summary()
            result = {"message": "Budget summary", "summary": summary}
                
        elif name == "modify_expense":
            expense_id = int(arguments["id"])
            amount = arguments.get("amount")
            description = arguments.get("description")
            category = arguments.get("category")
            
            # Convert types if present
            if amount is not None:
                amount = float(amount)
            if description is not None:
                description = str(description)
            if category is not None:
                category = str(category)
                
            res = db_modify_expense(
                expense_id=expense_id,
                description=description,
                amount=amount,
                category=category
            )
            result = res
            
        elif name == "delete_expense":
            expense_id = int(arguments["id"])
            res = db_delete_expense(expense_id=expense_id)
            result = res
            
        else:
            raise ValueError(f"Expense tool '{name}' not supported")
            
        result_str = json.dumps(result, ensure_ascii=False)
        logger.info(f"Tool '{name}' executed successfully. Response: {result_str}")
        return [
            types.TextContent(
                type="text",
                text=result_str
            )
        ]
        
    except Exception as e:
        logger.exception(f"Error executing expense tool '{name}'")
        return [
            types.TextContent(
                type="text",
                text=f"Error in execution of expense tool '{name}': {str(e)}"
            )
        ]


from starlette.routing import Route

# Define ASGI class wrappers to prevent Starlette from wrapping them with request_response
class SSEASGIApp:
    async def __call__(self, scope, receive, send):
        logger.info("Received SSE connection request for the Expenses MCP server")
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
    Returns the availability status of the expense server with complete metadata.
    """
    return {
        "status": "online",
        "tool_count": len(EXPENSE_TOOLS),
        "tools": [
            {
                "name": t.name,
                "description": t.description,
                "inputSchema": t.inputSchema
            }
            for t in EXPENSE_TOOLS
        ]
    }


def run():
    reload = os.getenv("UVICORN_RELOAD", "false").lower() == "true"
    uvicorn.run("app.mcp.finance.server:app", host="0.0.0.0", port=8002, reload=reload, reload_dirs=["app"] if reload else None)


if __name__ == "__main__":
    run()
