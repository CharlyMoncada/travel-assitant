import re
import logging

logger = logging.getLogger(__name__)

REJECTION_MESSAGE_OUTPUT_LEAK = (
    "Sorry, I encountered an internal consistency error. Let's try again."
)

REJECTION_MESSAGE_OUTPUT_ERROR = (
    "Sorry, an internal error occurred while generating the response. Please try again."
)


def check_output_integrity(text: str) -> tuple[bool, str | None]:
    # 1. Template tokens leakage check
    template_pattern = re.compile(
        r"(\[INST\]|<<SYS>>|<</SYS>>|<\|system\|>|<\|user\|>|\[SYSTEM\]|###\s*(system|instruction))",
        re.IGNORECASE,
    )
    if template_pattern.search(text):
        return False, "template_token_leak"

    # 2. Raw Python tracebacks/exceptions leak check
    traceback_pattern = re.compile(
        r"(Traceback\s+\(most\s+recent\s+call\s+last\):|ZeroDivisionError:|NameError:|TypeError:|AttributeError:|ValueError:|KeyError:|ImportError:|RuntimeError:)",
        re.IGNORECASE,
    )
    if traceback_pattern.search(text):
        return False, "raw_error_leak"

    # 3. Instruction/System Prompt leakage check — covers known agent prompt markers
    leakage_pattern = re.compile(
        r"(CRITICAL BEHAVIOR RULES|MANDATORY tool for answering|Strict RAG answer generator"
        r"|get_finance_system_prompt|get_reminder_system_prompt|get_recommender_system_prompt"
        r"|CRITICAL RULE.*NEVER ASK|AVAILABLE SUB-AGENTS|ROUTING RESPONSE FORMAT"
        r"|You are the Intelligent Supervisor)",
        re.IGNORECASE,
    )
    if leakage_pattern.search(text):
        return False, "instruction_leak"

    # 4. Potential API key / secret token leak
    secret_pattern = re.compile(
        r"(sk-[A-Za-z0-9]{20,}|Bearer\s+[A-Za-z0-9\-_\.]{20,}|OPENAI_API_KEY\s*=|BRAVE_API_KEY\s*=|TELEGRAM_BOT_TOKEN\s*=)",
        re.IGNORECASE,
    )
    if secret_pattern.search(text):
        logger.warning("Output guardrail: potential secret token detected in response")
        return False, "secret_leak"

    # 5. Internal tool / function call markup leak
    tool_call_pattern = re.compile(
        r"(<tool_call>|<function_call>|<\|tool_call\|>|\{\"tool_name\"\s*:|\"function\"\s*:\s*\"[a-z_]+\")",
        re.IGNORECASE,
    )
    if tool_call_pattern.search(text):
        return False, "tool_call_leak"

    return True, None
