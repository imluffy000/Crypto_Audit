"""Output generation: console, JSON and Markdown reports and research analysis."""

from cryptoaudit.reporting.console_report import render_console_report, render_module_run
from cryptoaudit.reporting.json_report import format_json_report, module_run_to_dict
from cryptoaudit.reporting.markdown_report import to_markdown
from cryptoaudit.reporting.research import analyze, compare_strategies

__all__ = [
    "analyze",
    "compare_strategies",
    "format_json_report",
    "module_run_to_dict",
    "render_console_report",
    "render_module_run",
    "to_markdown",
]
