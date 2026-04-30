from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class ArticleBriefNormalized(BaseModel):
    """PRD：简略提纲结构化（必填六项 + 可选参数）。"""

    topic: str = Field(..., description="选题")
    angle: str = Field(..., description="切入角度")
    thesis: str = Field(..., description="核心命题")
    argument_framework: str = Field(..., description="论证框架")
    narrative_skeleton: str = Field(..., description="叙事骨架")
    target_audience: str = Field(..., description="目标读者")
    target_word_count: int = Field(default=5000, ge=500, le=20000)
    style_intensity: str | None = Field(default=None, description="低/中/高")
    tone_preference: str | None = None
    forbidden_phrases: list[str] = Field(default_factory=list)
    references_text: str | None = None
    extras: dict[str, Any] = Field(default_factory=dict)

    @field_validator(
        "topic",
        "angle",
        "thesis",
        "argument_framework",
        "narrative_skeleton",
        "target_audience",
        mode="before",
    )
    @classmethod
    def strip_required(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip()
        return v


class OutlineParagraph(BaseModel):
    purpose: str
    evidence_slots: list[str] = Field(default_factory=list)


class OutlineSection(BaseModel):
    section_title: str
    section_goal: str
    paragraphs: list[OutlineParagraph]


class OutlineDocument(BaseModel):
    title: str
    sections: list[OutlineSection]
    closing_notes: str | None = None

    def flatten_evidence_placeholder_count(self) -> int:
        n = 0
        for s in self.sections:
            for p in s.paragraphs:
                n += len(p.evidence_slots)
        return n


class DraftBundle(BaseModel):
    """按章节正文片段（有序）。"""
    sections_body: list[str]
    concatenated_raw: str
    concatenated_polished: str


class JudgeScores(BaseModel):
    style_similarity_0_100: float = Field(..., ge=0, le=100)
    structure_completeness_0_100: float = Field(..., ge=0, le=100)
    naturalness_0_100: float = Field(..., ge=0, le=100)
    rationales: dict[str, str] = Field(default_factory=dict)


class ScoreCard(BaseModel):
    rule_scores: JudgeScores
    llm_scores: JudgeScores | None = None
    fused_total_0_100: float | None = None
    fused_breakdown: dict[str, Any] | None = None
    explanations: dict[str, Any] = Field(default_factory=dict)
