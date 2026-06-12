from __future__ import annotations

from ..deepseek_client import DeepSeekClient
from ..models import AgentResult, Evidence
from .knowledge import trim


class SynthesisAgent:
    def __init__(self, client: DeepSeekClient | None = None) -> None:
        self.client = client or DeepSeekClient()

    def synthesize(self, question: str, results: list[AgentResult]) -> AgentResult:
        evidence = [item for result in results for item in result.evidence]
        if self.client.enabled:
            try:
                return self._llm_synthesize(question, results, evidence)
            except Exception as exc:
                fallback = self._fallback_synthesize(question, results, evidence)
                fallback.thinking_summary.append(f"DeepSeek API 调用失败，已切换本地综合：{exc}")
                return fallback
        return self._fallback_synthesize(question, results, evidence)

    def _llm_synthesize(self, question: str, results: list[AgentResult], evidence: list[Evidence]) -> AgentResult:
        system_prompt = (
            "你是上游综合 Agent，负责整合多个下游 LLM 技术文档 Agent 的结论。"
            "只依据下游答案和证据，输出中文。不要输出隐藏推理链。"
            "返回 JSON："
            '{"thinking_summary":["..."],"answer":"...","confidence":0.0}'
        )
        agent_blocks = "\n\n".join(
            f"## {result.agent_name}\n思考摘要：{'; '.join(result.thinking_summary)}\n答案：{result.answer}"
            for result in results
        )
        data = self.client.chat_json(system_prompt, f"问题：{question}\n\n下游 Agent 结果：\n{agent_blocks}", max_tokens=2600)
        return AgentResult(
            agent_id="synthesis",
            agent_name="综合 Agent",
            answer=str(data.get("answer", "")).strip(),
            thinking_summary=[str(item) for item in data.get("thinking_summary", [])][:6],
            evidence=evidence,
            confidence=float(data.get("confidence", 0.7)),
        )

    def _fallback_synthesize(self, question: str, results: list[AgentResult], evidence: list[Evidence]) -> AgentResult:
        thinking = [
            f"综合 Agent 收到 {len(results)} 个下游 Agent 的结果。",
            "本地综合模式会保留各 Agent 的关键结论，并按问题组织横向摘要。",
        ]
        lines = ["综合多个 Agent 的检索结果，可以得到以下结论："]
        for result in results:
            lines.append(f"\n### {result.agent_name}")
            lines.append(trim(result.answer, 900))
        lines.append("\n建议在配置 DeepSeek API 后再次提问，以获得更凝练的横向对比表述。")
        return AgentResult(
            agent_id="synthesis",
            agent_name="综合 Agent",
            answer="\n".join(lines),
            thinking_summary=thinking,
            evidence=evidence,
            confidence=min([result.confidence for result in results], default=0.5),
        )
