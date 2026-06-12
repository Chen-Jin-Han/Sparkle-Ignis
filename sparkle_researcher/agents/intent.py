from __future__ import annotations

from collections import Counter

from ..config import settings
from ..models import Evidence, QueryIntent
from ..registry import detect_agent_mentions, scan_agents


COMPARISON_TERMS = ["对比", "比较", "区别", "不同", "各自", "多种", "多个", "主流", "横向", "综述", "总结一下各"]


class IntentAgent:
    def route(self, question: str, evidence: list[Evidence], selected_agent_ids: list[str] | None = None) -> QueryIntent:
        agents = scan_agents()
        valid_ids = {agent.id for agent in agents}
        selected = [agent_id for agent_id in (selected_agent_ids or []) if agent_id in valid_ids]
        if selected:
            mode = "multi" if len(selected) > 1 else "single"
            return QueryIntent(
                mode=mode,
                selected_agent_ids=selected,
                rationale="用户在前端手动指定了 Agent。",
                confidence=0.98,
            )

        mentions = detect_agent_mentions(question, agents)
        is_comparison = any(term in question for term in COMPARISON_TERMS)
        if mentions:
            mode = "multi" if len(mentions) > 1 or is_comparison else "single"
            return QueryIntent(
                mode=mode,
                selected_agent_ids=mentions[: settings.multi_agent_limit],
                rationale="从问题中识别到明确的模型/厂商名称。",
                confidence=0.9,
            )

        ranked_agents = [agent_id for agent_id, _ in Counter(item.agent_id for item in evidence).most_common()]
        if not ranked_agents:
            fallback = agents[0].id if agents else ""
            return QueryIntent(mode="single", selected_agent_ids=[fallback], rationale="未检索到明显对象，使用默认 Agent。", confidence=0.2)

        selected_count = settings.multi_agent_limit if is_comparison else 1
        return QueryIntent(
            mode="multi" if selected_count > 1 else "single",
            selected_agent_ids=ranked_agents[:selected_count],
            rationale="根据 RAG 检索命中的文档分布自动路由。",
            confidence=0.72 if is_comparison else 0.76,
        )
