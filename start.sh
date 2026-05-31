#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate venv if not already active
if [[ -z "$VIRTUAL_ENV" ]]; then
    if [[ -f ".venv/bin/activate" ]]; then
        source .venv/bin/activate
    else
        echo "ERROR: No .venv found. Run: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
        exit 1
    fi
fi

mkdir -p logs

echo "Starting Finance MCP Server  (port 8002)..."
python -m app.mcp.finance.server > logs/finance.log 2>&1 &
FINANCE_PID=$!

echo "Starting Reminder MCP Server (port 8003)..."
python -m app.mcp.reminder.server > logs/reminder.log 2>&1 &
REMINDER_PID=$!

# Give MCP servers a moment to bind their ports before the main backend connects
sleep 2

echo "Starting Main Backend        (port 8000)..."
python -m app.main > logs/main.log 2>&1 &
MAIN_PID=$!

echo ""
echo "All services running. PIDs: finance=$FINANCE_PID  reminder=$REMINDER_PID  main=$MAIN_PID"
echo "Logs: logs/finance.log | logs/reminder.log | logs/main.log"
echo ""
echo "Press Ctrl+C to stop all services."

# Forward Ctrl+C to all child processes
trap "echo 'Stopping...'; kill $FINANCE_PID $REMINDER_PID $MAIN_PID 2>/dev/null; exit 0" SIGINT SIGTERM

# Tail all three logs in parallel so output is visible in one terminal
tail -f logs/finance.log logs/reminder.log logs/main.log
