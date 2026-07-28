import sys
import os
sys.path.insert(0, os.path.abspath("."))

import unittest
from app.agents.finance.prompts import get_finance_system_prompt
from app.agents.reminder.prompts import get_reminder_system_prompt

class TestPromptsRefactor(unittest.TestCase):
    def test_finance_prompt_optimizations(self):
        prompt = get_finance_system_prompt()
        self.assertLess(len(prompt), 2500)
        self.assertIn("CURRENCY DIRECTIVE", prompt)
        self.assertIn("Euros (€)", prompt)
        self.assertIn("do NOT call any tool", prompt)
        self.assertIn("dollars, USD, $, pounds, GBP, £, yen, ¥, pesos", prompt)
        self.assertIn("El asistente actualmente opera únicamente con gastos en Euros (€)", prompt)

    def test_reminder_prompt_optimizations(self):
        prompt = get_reminder_system_prompt()
        self.assertLess(len(prompt), 2500)
        self.assertIn("query_reminders", prompt)
        self.assertIn("record_reminder", prompt)
        self.assertIn("delete_reminder", prompt)

if __name__ == "__main__":
    unittest.main()
