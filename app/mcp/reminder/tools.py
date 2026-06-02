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
        description="Queries and lists reminders registered in the system. If a date_filter is provided (format: YYYY-MM-DD), returns only reminders scheduled for that specific date. Without a filter, returns all reminders ordered by due time ascending.",
        inputSchema={
            "type": "object",
            "properties": {
                "date_filter": {
                    "type": "string",
                    "description": "Optional date filter in YYYY-MM-DD format to retrieve only reminders for a specific day. Example: 2026-06-01"
                }
            }
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

