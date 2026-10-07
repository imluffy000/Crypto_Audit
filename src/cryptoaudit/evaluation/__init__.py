"""Research analysis: scanner overestimation, category difficulty, compatibility breaks, tool comparison."""

from cryptoaudit.evaluation.report import to_markdown
from cryptoaudit.evaluation.research import Proportion, ResearchFindings, ScannerAssessment, analyze, wilson_interval

__all__ = ["Proportion", "ResearchFindings", "ScannerAssessment", "analyze", "to_markdown", "wilson_interval"]
