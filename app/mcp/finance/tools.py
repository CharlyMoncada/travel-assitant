import mcp.types as types

# Definition of structured finance tools
EXPENSE_TOOLS = [
    types.Tool(
        name="record_expense",
        description="Records a new financial expense in the system, specifying the amount, description, and category.",
        inputSchema={
            "type": "object",
            "properties": {
                "amount": {
                    "type": "number",
                    "description": "Amount or cost of the expense in euros. Example: 25.50"
                },
                "description": {
                    "type": "string",
                    "description": "Detailed concept or description of the expense. Example: Taxi to airport"
                },
                "category": {
                    "type": "string",
                    "description": "Category the expense belongs to. Example: transport, food, accommodation, leisure, others"
                }
            },
            "required": ["amount", "description", "category"]
        }
    ),
    types.Tool(
        name="budget",
        description="Generates a summary of the budget and registered expenses.",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
    types.Tool(
        name="query_expenses",
        description="Queries the registered expenses and the total budget summary, with an optional category filter.",
        inputSchema={
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Optional category filter for the search. Example: food"
                }
            }
        }
    ),
    types.Tool(
        name="modify_expense",
        description="Modifies one or more fields (description, amount, category) of an existing expense identified by its unique ID.",
        inputSchema={
            "type": "object",
            "properties": {
                "id": {
                    "type": "integer",
                    "description": "Unique numerical ID of the expense to modify."
                },
                "amount": {
                    "type": "number",
                    "description": "New amount of the expense in euros (optional)."
                },
                "description": {
                    "type": "string",
                    "description": "New description for the expense (optional)."
                },
                "category": {
                    "type": "string",
                    "description": "New category for the expense (optional)."
                }
            },
            "required": ["id"]
        }
    ),
    types.Tool(
        name="delete_expense",
        description="Permanently deletes an expense from the database using its unique ID.",
        inputSchema={
            "type": "object",
            "properties": {
                "id": {
                    "type": "integer",
                    "description": "Unique numerical ID of the expense to delete."
                }
            },
            "required": ["id"]
        }
    )
]

