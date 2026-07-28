import os
import sys

sys.path.insert(0, os.path.abspath("."))

from app.agents.finance.prompts import get_finance_system_prompt
from app.agents.reminder.prompts import get_reminder_system_prompt

fin_prompt = get_finance_system_prompt()
rem_prompt = get_reminder_system_prompt()

print(f"Finance Prompt Size: {len(fin_prompt)} chars")
print(f"Reminder Prompt Size: {len(rem_prompt)} chars")

assert len(fin_prompt) < 2500, f"Finance prompt too long: {len(fin_prompt)}"
assert len(rem_prompt) < 2500, f"Reminder prompt too long: {len(rem_prompt)}"
assert "CURRENCY DIRECTIVE" in fin_prompt
assert "Euros (€)" in fin_prompt
assert "query_reminders" in rem_prompt

print("ALL VERIFICATIONS PASSED SUCCESSFULLY!")
