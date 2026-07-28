import sys
import os
sys.path.insert(0, os.path.abspath("."))

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock

from app.agents.supervisor.prompts import SUPERVISOR_SYSTEM_PROMPT, MEMORY_RULE
from app.agents.supervisor.agent import run_supervisor, RoutingDecision


class TestSupervisorPromptRefactor(unittest.TestCase):
    def test_supervisor_prompt_size(self):
        # Verificar que el prompt se haya reducido significativamente (< 2000 caracteres)
        self.assertLess(len(SUPERVISOR_SYSTEM_PROMPT), 2000)
        self.assertEqual(MEMORY_RULE, "")

    def test_supervisor_prompt_contains_core_routes(self):
        self.assertIn("finance", SUPERVISOR_SYSTEM_PROMPT)
        self.assertIn("reminder", SUPERVISOR_SYSTEM_PROMPT)
        self.assertIn("general", SUPERVISOR_SYSTEM_PROMPT)
        self.assertIn("recommender", SUPERVISOR_SYSTEM_PROMPT)

class TestSupervisorExecution(unittest.IsolatedAsyncioTestCase):
    async def test_run_supervisor_routing(self):
        mock_llm = MagicMock()
        mock_structured_llm = MagicMock()
        
        mock_decision = RoutingDecision(routes=["finance"], response=None)
        mock_structured_llm.ainvoke = AsyncMock(return_value=mock_decision)
        mock_llm.with_structured_output.return_value = mock_structured_llm
        
        routes, response_text = await run_supervisor(mock_llm, [], "mis gastos de hoy")
        
        self.assertEqual(routes, ["finance"])
        self.assertEqual(response_text, "")

if __name__ == "__main__":
    unittest.main()
