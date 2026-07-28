import os
import sys

sys.path.insert(0, os.path.abspath("."))

from app.agents.general.prompts import get_general_system_prompt

prompt = get_general_system_prompt()
print(f"General Prompt Size: {len(prompt)} chars")

assert "rules" in prompt
assert "travel_search" in prompt
assert "European" in prompt
assert len(prompt) < 1600, f"Prompt too long: {len(prompt)}"

print("GENERAL PROMPT VERIFICATION PASSED SUCCESSFULLY!")
