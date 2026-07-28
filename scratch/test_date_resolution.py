import os
import sys

sys.path.insert(0, os.path.abspath("."))

from app.utils.date_resolution import (
    get_current_date_resolution_context,
    get_date_resolution_prompt_directives,
)
from app.agents.finance.prompts import get_finance_system_prompt
from app.agents.reminder.prompts import get_reminder_system_prompt
from app.agents.general.prompts import get_general_system_prompt
from app.agents.recommender.prompts import get_recommender_system_prompt

ctx = get_current_date_resolution_context()
directives = get_date_resolution_prompt_directives(ctx)

print(f"Directives length: {len(directives)} chars")
assert "DATE RESOLUTION" in directives
assert ctx["current_date_iso"] in directives

fin = get_finance_system_prompt()
rem = get_reminder_system_prompt()
gen = get_general_system_prompt()
rec = get_recommender_system_prompt()

print(f"Finance Prompt: {len(fin)} chars")
print(f"Reminder Prompt: {len(rem)} chars")
print(f"General Prompt: {len(gen)} chars")
print(f"Recommender Prompt: {len(rec)} chars")

assert "DATE RESOLUTION" in fin
assert "DATE RESOLUTION" in rem
assert "DATE RESOLUTION" in gen
assert "DATE RESOLUTION" in rec

print("ALL DATE RESOLUTION & SYSTEM PROMPTS TESTS PASSED 100%!")
