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
        r"(Traceback\s+\(most\s+recent\s+call\s+last\):|ZeroDivisionError:|NameError:|TypeError:|AttributeError:|ValueError:|KeyError:)",
        re.IGNORECASE,
    )
    if traceback_pattern.search(text):
        return False, "raw_error_leak"

    # 3. Instruction/System Prompt leakage check
    leakage_pattern = re.compile(
        r"(CRITICAL BEHAVIOR RULES|MANDATORY tool for answering|Strict RAG answer generator|get_finance_system_prompt)",
        re.IGNORECASE,
    )
    if leakage_pattern.search(text):
        return False, "instruction_leak"

    return True, None
