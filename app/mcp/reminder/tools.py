import mcp.types as types

# Definition of structured reminder tools
REMINDER_TOOLS = [
    types.Tool(
        name="record_reminder",
        description="Creates a new reminder or task in the travel itinerary manager, specifying the title, due time, and an optional note.",
        inputSchema={
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Title or name of the reminder. Example: Flight check-in"
                },
                "due_time": {
                    "type": "string",
                    "description": "Date and time of the reminder in free format. Example: tomorrow at 10:00, 2026-06-01 18:00"
                },
                "note": {
                    "type": "string",
                    "description": "Additional note or details of the reminder (optional). Example: Do not forget the passport"
                }
            },
            "required": ["title", "due_time"]
        }
    ),
    types.Tool(
        name="query_reminders",
        description="Queries and lists all reminders registered in the system, ordered from most recent to oldest.",
        inputSchema={
            "type": "object",
            "properties": {}
        }
    ),
    types.Tool(
        name="modify_reminder",
        description="Modifies one or more fields (title, due time, note) of an existing reminder identified by its unique ID.",
        inputSchema={
            "type": "object",
            "properties": {
                "id": {
                    "type": "integer",
                    "description": "Unique numerical ID of the reminder to modify."
                },
                "title": {
                    "type": "string",
                    "description": "New title for the reminder (optional)."
                },
                "due_time": {
                    "type": "string",
                    "description": "New date/time for the reminder (optional)."
                },
                "note": {
                    "type": "string",
                    "description": "New note for the reminder (optional)."
                }
            },
            "required": ["id"]
        }
    ),
    types.Tool(
        name="delete_reminder",
        description="Permanently deletes a reminder from the database using its unique ID.",
        inputSchema={
            "type": "object",
            "properties": {
                "id": {
                    "type": "integer",
                    "description": "Unique numerical ID of the reminder to delete."
                }
            },
            "required": ["id"]
        }
    )
]

