from __future__ import annotations

from ..deepseek_client import DeepSeekClient
from ..models import AuditResult, Evidence


class AnswerAuditAgent:
    def __init__(self, client: DeepSeekClient | None = None) -> None:
        self.client = client or DeepSeekClient()

    def review(self, question: str, answer: str, evidence: list[Evidence]) -> AuditResult:
        notes: list[str] = []
        if not evidence:
            notes.append("未找到可引用证据，答案可信度较低。")
        if len(answer.strip()) < 20:
            notes.append("答案过短，可能没有充分回应问题。")
        cited_titles = {item.title for item in evidence[:8]}
        if cited_titles:
            notes.append("答案已附带 RAG 证据，主要来源：" + "、".join(list(cited_titles)[:5]) + "。")

        if self.client.enabled:
            try:
                llm_result = self._llm_review(question, answer, evidence)
                notes.extend(llm_result.notes)
                return llm_result
            except Exception as exc:
                notes.append(f"DeepSeek 审核调用失败，使用本地规则审核：{exc}")

        return AuditResult(passed=not any("过短" in note for note in notes), notes=notes)

    def _llm_review(self, question: str, answer: str, evidence: list[Evidence]) -> AuditResult:
        system_prompt = (
            "你是答案审核 Agent。检查答案是否严格基于证据、是否答非所问、是否有明显编造。"
            "如果需要小幅修正，请给 revised_answer；否则 revised_answer 为 null。"
            "返回 JSON："
            '{"passed":true,"notes":["..."],"revised_answer":null}'
        )
        evidence_text = "\n".join(f"- {item.agent_name}/{item.title} p.{item.page}: {item.text[:500]}" for item in evidence[:8])
        data = self.client.chat_json(
            system_prompt,
            f"问题：{question}\n\n答案：{answer}\n\n证据：\n{evidence_text}",
            max_tokens=1600,
        )
        return AuditResult(
            passed=bool(data.get("passed", False)),
            notes=[str(item) for item in data.get("notes", [])][:8],
            revised_answer=data.get("revised_answer"),
        )
