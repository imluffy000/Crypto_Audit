"""Explanation models: the evidence-based 'why' attached to every repair result."""

from typing import List

from pydantic import BaseModel, Field

from cryptoaudit.models.experiment import Verdict


class ExplanationSection(BaseModel):
    title: str
    points: List[str] = Field(default_factory=list)


class Explanation(BaseModel):
    source: str = "evidence"
    verdict: Verdict
    headline: str
    sections: List[ExplanationSection] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
