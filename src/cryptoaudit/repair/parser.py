"""Strict parser for LLM repair output."""

import ast
import re

DEFAULT_MAX_CODE_CHARS = 100_000
_FENCE = re.compile(r"```[ \t]*(?:python|py|python3)?[ \t]*\r?\n(.*?)```", re.DOTALL | re.IGNORECASE)


class OutputParseError(ValueError):
    pass


def parse_llm_output(text: str, max_chars: int = DEFAULT_MAX_CODE_CHARS) -> str:
    """
    Accept exactly one fenced code block containing a complete, syntactically valid module.
    Anything else is rejected: no heuristics, no repair of malformed output.
    """
    blocks = _FENCE.findall(text)
    if len(blocks) != 1:
        raise OutputParseError(f"Expected exactly one fenced Python code block, found {len(blocks)}")
    code = blocks[0]
    if not code.strip():
        raise OutputParseError("Code block is empty")
    if len(code) > max_chars:
        raise OutputParseError(f"Code block exceeds {max_chars} characters")
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        raise OutputParseError(f"Code block is not valid Python: line {exc.lineno}: {exc.msg}") from exc
    if not tree.body:
        raise OutputParseError("Code block contains no statements")
    return code if code.endswith("\n") else code + "\n"
