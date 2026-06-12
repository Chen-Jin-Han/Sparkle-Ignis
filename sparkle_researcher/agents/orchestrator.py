from __future__ import annotations

from ..config import settings
from ..deepseek_client import DeepSeekClient
from ..models import AgentResult, ChatResult
from ..rag import RagIndex
from ..registry import agent_map, scan_agents
from .audit import AnswerAuditAgent
from .intent import IntentAgent
from .knowledge import LLMKnowledgeAgent
from .relevance import DocumentRelevanceAgent
from .synthesis import SynthesisAgent


class ResearchOrchestrator:
    def __init__(self, index: RagIndex | None = None) -> None:
        self.index = index or RagIndex()
        self.client = DeepSeekClient()
        self.relevance_agent = DocumentRelevanceAgent()
        self.intent_agent = IntentAgent()
        self.synthesis_agent = SynthesisAgent(self.client)
        self.audit_agent = AnswerAuditAgent(self.client)

    def chat(self, question: str, selected_agent_ids: list[str] | None = None) -> ChatResult:
        question = question.strip()
        if not question:
            return ChatResult(status="error", question=question, answer="请输入问题。", thinking=[])

        broad_evidence = self.index.search(question, top_k=max(10, settings.retrieval_top_k))
        relevance = self.relevance_agent.check(question, broad_evidence, selected_agent_ids)
        thinking = [f"相关性审查：{relevance.reason}"]
        if not relevance.is_relevant:
            return ChatResult(
                status="rejected",
                question=question,
                answer="这个问题没有落在当前 LLM 技术文档范围内，因此我不能基于这些资料回答。请改问某个模型、技术报告、架构、训练、评测或对比相关的问题。",
                thinking=thinking,
                evidence=relevance.evidence,
            )

        intent = self.intent_agent.route(question, broad_evidence, selected_agent_ids)
        thinking.append(
            f"意图识别：{intent.rationale} 路由模式={intent.mode}，目标 Agent={', '.join(intent.selected_agent_ids)}。"
        )

        agents = agent_map()
        downstream_results: list[AgentResult] = []
        for agent_id in intent.selected_agent_ids:
            info = agents.get(agent_id)
            if not info:
                continue
            agent_evidence = self.index.search(question, agent_ids=[agent_id], top_k=settings.retrieval_top_k)
            result = LLMKnowledgeAgent(info, self.client).answer(question, agent_evidence)
            downstream_results.append(result)
            thinking.extend([f"{result.agent_name}：{item}" for item in result.thinking_summary[:3]])

        if not downstream_results:
            return ChatResult(
                status="error",
                question=question,
                answer="没有找到可用的下游 Agent。",
                thinking=thinking,
                intent=intent,
                evidence=broad_evidence,
            )

        if intent.mode == "single" and len(downstream_results) == 1:
            final_result = downstream_results[0]
        else:
            final_result = self.synthesis_agent.synthesize(question, downstream_results)
            thinking.extend([f"综合 Agent：{item}" for item in final_result.thinking_summary[:4]])

        audit = self.audit_agent.review(question, final_result.answer, final_result.evidence)
        thinking.append("答案审核：" + "；".join(audit.notes[:4]))
        answer = audit.revised_answer or final_result.answer
        evidence = final_result.evidence or [item for result in downstream_results for item in result.evidence]

        return ChatResult(
            status="ok",
            question=question,
            answer=answer,
            thinking=thinking,
            intent=intent,
            agents=downstream_results,
            evidence=evidence[: settings.retrieval_top_k * max(1, len(downstream_results))],
            audit=audit,
        )

    def list_agents(self) -> list[dict[str, object]]:
        return [
            {
                "id": agent.id,
                "name": agent.name,
                "pdf_count": agent.pdf_count,
                "documents": agent.documents,
                "aliases": agent.aliases,
            }
            for agent in scan_agents()
        ]
