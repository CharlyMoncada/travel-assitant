import os
import sys

sys.path.insert(0, os.path.abspath("."))

from app.agents.recommender.prompts import get_recommender_system_prompt

prompt = get_recommender_system_prompt()
print(f"Recommender Prompt Size: {len(prompt)} chars")

assert "TOOLS" in prompt
assert "OUTPUT FORMAT" in prompt
assert "CLASSIFICATION RULES" in prompt
assert "max 5" in prompt or "maximum 5" in prompt

print("RECOMMENDER PROMPT VERIFICATION PASSED SUCCESSFULLY!")
