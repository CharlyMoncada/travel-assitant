"""
Output guardrail — hybrid approach: fast regex pre-filter + LLM semantic inspector.

Architecture mirrors the input guardrail:
  1. Regex pre-filter (< 1 ms, no API cost): catches unambiguous, high-confidence
     information leaks — Python tracebacks, known API key formats, template tokens,
     literal system-prompt markers, tool-call markup.
  2. LLM inspector (gpt-4o-mini, one structured call): detects subtle / indirect
     leaks that regex cannot express — obfuscated or partial secrets, paraphrased
     system-prompt fragments, inadvertent PII from other sessions, code or
     implementation details embedded in the response.

Rationale for the hybrid design:
- Pure regex: excellent for technical signatures but blind to semantic/indirect
  leakage ("my key begins with sk-...").
- Pure LLM: adds ~300 ms latency on every response + API cost; overkill for the
  majority of responses that are trivially clean.
- Hybrid: deterministic fast-path eliminates most cases instantly; LLM handles
  the nuanced ones. Fails-open (allow through) on API errors to preserve
  availability — the same policy as the input guardrail.
"""

from __future__ import annotations

import logging
import re

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.services.llm import get_openai_model

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public rejection messages
# ---------------------------------------------------------------------------

REJECTION_MESSAGE_OUTPUT_LEAK = (
    "Sorry, I encountered an internal consistency error. Let's try again."
)

REJECTION_MESSAGE_OUTPUT_ERROR = (
    "Sorry, an internal error occurred while generating the response. Please try again."
)

# ---------------------------------------------------------------------------
# Stage 1 — Regex pre-filter
# High-confidence, unambiguous output leak signatures.
# ---------------------------------------------------------------------------

_OUTPUT_PATTERNS: list[tuple[str, re.Pattern]] = [
    # LLM template tokens in the response
    ("template_token_leak",
     re.compile(
         r"(\[INST\]|<<SYS>>|<</SYS>>|<\|system\|>|<\|user\|>|\[SYSTEM\]|###\s*(system|instruction))",
         re.IGNORECASE,
     )),
    # Raw Python tracebacks and common exception types
    ("raw_error_leak",
     re.compile(
         r"(Traceback\s+\(most\s+recent\s+call\s+last\):"
         r"|ZeroDivisionError:|NameError:|TypeError:|AttributeError:"
         r"|ValueError:|KeyError:|ImportError:|RuntimeError:)",
         re.IGNORECASE,
     )),
    # Literal system-prompt markers from the agents
    ("instruction_leak",
     re.compile(
         r"(CRITICAL BEHAVIOR RULES|MANDATORY tool for answering|Strict RAG answer generator"
         r"|get_finance_system_prompt|get_reminder_system_prompt|get_recommender_system_prompt"
         r"|CRITICAL RULE.*NEVER ASK|AVAILABLE SUB-AGENTS|ROUTING RESPONSE FORMAT"
         r"|You are the Intelligent Supervisor)",
         re.IGNORECASE,
     )),
    # API key / secret token patterns
    ("secret_leak",
     re.compile(
         r"(sk-[A-Za-z0-9]{20,}|Bearer\s+[A-Za-z0-9\-_\.]{20,}"
         r"|OPENAI_API_KEY\s*=|BRAVE_API_KEY\s*=|TELEGRAM_BOT_TOKEN\s*=)",
         re.IGNORECASE,
     )),
    # Internal tool/function call markup
    ("tool_call_leak",
     re.compile(
         r"(<tool_call>|<function_call>|<\|tool_call\|>|\{\"tool_name\"\s*:|\"function\"\s*:\s*\"[a-z_]+\")",
         re.IGNORECASE,
     )),
]


def _check_output_patterns(text: str) -> tuple[bool, str | None]:
    """
    Returns (is_clean, leak_type).
    is_clean=False means the pre-filter caught a leak.
    """
    for name, pattern in _OUTPUT_PATTERNS:
        if pattern.search(text):
            if name == "secret_leak":
                logger.warning("Output guardrail pre-filter: potential secret token detected")
            else:
                logger.warning("Output guardrail pre-filter: pattern '%s' matched", name)
            return False, name
    return True, None


# ---------------------------------------------------------------------------
# Stage 2 — LLM semantic inspector
# ---------------------------------------------------------------------------

_OUTPUT_INSPECTOR_SYSTEM_PROMPT = """\
You are a strict output safety inspector for a Travel Assistant chatbot.
Your ONLY job is to analyze the assistant's response and determine if it accidentally
leaks internal information that should never reach the end user.
You must NEVER modify or summarize the response — only classify it.

CLASSIFY AS NOT CLEAN (is_clean=false) if the response contains:

1. PARTIAL or OBFUSCATED SECRETS: hints at API keys, tokens, or passwords even without
   the full value (e.g. "my key starts with sk-", "the token ends in XYZ").

2. INDIRECT SYSTEM PROMPT LEAKAGE: the response reveals that the assistant has specific
   internal instructions, rules, or configuration beyond what a normal assistant would say.
   Examples of leaks:
     - "I am configured to route finance queries to a separate finance module."
     - "My internal rules say I cannot discuss non-European destinations."
     - "I have a prompt that tells me to always use the get_weather tool first."
   Note: saying "I can help you with travel expenses" is NOT a leak — it is a normal
   description of capability.

3. INTERNAL CODE or IMPLEMENTATION DETAILS: Python function names, class names, variable
   names, SQL queries, or internal architecture details that are not relevant to the user's
   question.

4. PII FROM OTHER SESSIONS: user data (names, expenses, reminders, preferences) that
   clearly belongs to a different conversation session.

CLASSIFY AS CLEAN (is_clean=true) if the response is:
- A normal answer about travel, hotels, flights, weather, packing, expenses, or reminders.
- A greeting, clarification, or apology that doesn't reveal internal information.
- An explanation of the assistant's general capabilities (NOT implementation specifics).

When in doubt, classify as clean to avoid blocking legitimate responses.
"""


class OutputIntegrityDecision(BaseModel):
    is_clean: bool = Field(
        description="True if the response is safe to return to the user. False if it contains an indirect information leak."
    )
    leak_type: str | None = Field(
        default=None,
        description="One of: 'partial_secret_leak', 'indirect_prompt_leak', 'code_leak', 'cross_session_pii'. Null if is_clean=True.",
    )


async def check_output_integrity(text: str) -> tuple[bool, str | None]:
    """
    Full hybrid output integrity check.

    Returns:
        (is_clean, leak_type)
        - is_clean: False if a leak was detected.
        - leak_type: string identifying the type of leak, or None if clean.

    Flow:
        1. Regex pre-filter (instant, no API call).
        2. LLM semantic inspector (async, structured output).
        3. On LLM API error: log warning and allow the response through (fail-open).
    """
    # Stage 1 — regex pre-filter
    is_clean_regex, regex_leak_type = _check_output_patterns(text)
    if not is_clean_regex:
        return False, regex_leak_type

    # Stage 2 — LLM semantic inspection
    try:
        llm = ChatOpenAI(model=get_openai_model(), temperature=0.0)
        structured_llm = llm.with_structured_output(OutputIntegrityDecision)

        decision: OutputIntegrityDecision = await structured_llm.ainvoke([
            SystemMessage(content=_OUTPUT_INSPECTOR_SYSTEM_PROMPT),
            HumanMessage(content=text),
        ])

        logger.info(
            "LLM output guardrail decision: is_clean=%s, leak_type=%s",
            decision.is_clean,
            decision.leak_type,
        )

        if not decision.is_clean:
            return False, decision.leak_type or "semantic_leak"

        return True, None

    except Exception as exc:
        logger.warning(
            "LLM output guardrail API error — failing open (response allowed): %s", exc
        )
        return True, None
