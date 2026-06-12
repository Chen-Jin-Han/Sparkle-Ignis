from __future__ import annotations

import re

from ..config import settings
from ..models import Evidence, RelevanceDecision
from ..registry import detect_agent_mentions, scan_agents


TECHNICAL_TERMS = [
    "ai",
    "llm",
    "model",
    "agent",
    "rag",
    "transformer",
    "多模态",
    "模型",
    "大模型",
    "架构",
    "训练",
    "推理",
    "评测",
    "技术",
    "论文",
    "报告",
    "框架",
    "演进",
]


class DocumentRelevanceAgent:
    def check(self, question: str, evidence: list[Evidence], selected_agent_ids: list[str] | None = None) -> RelevanceDecision:
        agents = scan_agents()
        mentions = detect_agent_mentions(question, agents)
        selected = selected_agent_ids or []
        max_score = evidence[0].score if evidence else 0.0
        has_technical_term = any(term.lower() in question.lower() for term in TECHNICAL_TERMS)
        has_chinese_technical = bool(re.search(r"(模型|大模型|架构|训练|推理|评测|论文|技术|框架|演进)", question))

        if max_score >= settings.relevance_threshold:
            return RelevanceDecision(
                is_relevant=True,
                reason=f"检索到相关技术文档片段，最高相关度 {max_score:.4f}。",
                evidence=evidence[:3],
            )
        if (mentions or selected) and (has_technical_term or has_chinese_technical):
            names = ", ".join(mentions or selected)
            return RelevanceDecision(
                is_relevant=True,
                reason=f"问题显式指向 {names} 且包含技术文档语义，允许进入对应 Agent。",
                evidence=evidence[:3],
            )
        return RelevanceDecision(
            is_relevant=False,
            reason="问题没有命中 LLM 技术文档，也没有明确的模型/论文/架构/训练/评测语义。",
            evidence=evidence[:3],
        )
