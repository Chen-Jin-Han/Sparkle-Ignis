from __future__ import annotations

from collections import OrderedDict
import re

from ..deepseek_client import DeepSeekClient
from ..models import AgentResult, Evidence, LLMAgentInfo


class LLMKnowledgeAgent:
    def __init__(self, info: LLMAgentInfo, client: DeepSeekClient | None = None) -> None:
        self.info = info
        self.client = client or DeepSeekClient()

    def answer(self, question: str, evidence: list[Evidence]) -> AgentResult:
        if self.client.enabled:
            try:
                return self._llm_answer(question, evidence)
            except Exception as exc:
                fallback = self._fallback_answer(question, evidence)
                fallback.thinking_summary.append(f"DeepSeek API 调用失败，已切换本地摘要：{exc}")
                return fallback
        return self._fallback_answer(question, evidence)

    def _llm_answer(self, question: str, evidence: list[Evidence]) -> AgentResult:
        system_prompt = (
            f"你是 {self.info.name} 技术文档专家 Agent。"
            "你只能依据用户提供的文档证据回答。不要编造来源。"
            "不要输出隐藏推理链，只输出可审计的检索与判断摘要。"
            "请用中文回答，并返回 JSON："
            '{"thinking_summary":["..."],"answer":"...","confidence":0.0}'
        )
        user_prompt = f"问题：{question}\n\n文档证据：\n{format_evidence(evidence)}"
        data = self.client.chat_json(system_prompt, user_prompt, max_tokens=2200)
        return AgentResult(
            agent_id=self.info.id,
            agent_name=self.info.name,
            answer=str(data.get("answer", "")).strip(),
            thinking_summary=[str(item) for item in data.get("thinking_summary", [])][:6],
            evidence=evidence,
            confidence=float(data.get("confidence", 0.72)),
        )

    def _fallback_answer(self, question: str, evidence: list[Evidence]) -> AgentResult:
        grouped = OrderedDict()
        for item in evidence:
            grouped.setdefault(item.title, []).append(item)

        docs = list(grouped.keys())
        is_evolution = any(term in question for term in ["演进", "发展", "过程", "evolution"])
        thinking = [
            f"{self.info.name} Agent 命中 {len(evidence)} 个片段，覆盖 {len(docs)} 篇文档。",
            "使用本地 RAG 摘要模式：按文档标题、页码和高相关片段组织答案。",
        ]
        if is_evolution:
            thinking.append("问题被识别为演进类问题，优先按版本/能力扩展线索归纳。")

        if is_evolution:
            lines = self._fallback_evolution_answer(docs, grouped)
        else:
            lines = [f"基于已检索到的 {self.info.name} 文档，可以这样回答："]
            if docs:
                lines.append("")
                lines.append("主要证据来自：" + "、".join(docs[:6]) + (" 等。" if len(docs) > 6 else "。"))
            for idx, item in enumerate(evidence[:5], start=1):
                lines.append(f"\n[{idx}] {item.title} 第 {item.page} 页：{trim(item.text, 360)}")
            lines.append("\n归纳来看，答案应围绕这些证据展开；配置 DeepSeek API 后，系统会生成更完整的综合性表述。")
        return AgentResult(
            agent_id=self.info.id,
            agent_name=self.info.name,
            answer="\n".join(lines),
            thinking_summary=thinking,
            evidence=evidence,
            confidence=0.58 if evidence else 0.2,
        )

    def _fallback_evolution_answer(self, docs: list[str], grouped: OrderedDict[str, list[Evidence]]) -> list[str]:
        lines = [f"从当前命中的 {self.info.name} 文档看，技术演进可以按“训练/模型能力/服务架构”三条线理解。"]
        if docs:
            lines.append("")
            lines.append("主要证据来自：" + "、".join(docs[:6]) + (" 等。" if len(docs) > 6 else "。"))
        lines.append("")
        for index, title in enumerate(docs[:6], start=1):
            item = grouped[title][0]
            sentence = pick_informative_sentence(item.text)
            lines.append(f"{index}. {title}：{sentence}（第 {item.page} 页）")
        lines.append("")
        lines.append(
            "综合起来，演进脉络是：先围绕训练与推理资源协同提升大规模训练效率，"
            "再扩展到更强的多模态训练和长上下文能力，最后在在线服务侧通过 KVCache、prefill/decoding 解耦等系统设计支撑实际高并发应用。"
        )
        lines.append("配置 DeepSeek API 后，同一证据会交给模型生成更自然的长答案和横向归纳。")
        return lines


def format_evidence(evidence: list[Evidence]) -> str:
    blocks: list[str] = []
    for idx, item in enumerate(evidence, start=1):
        blocks.append(
            f"[{idx}] Agent={item.agent_name}; Doc={item.title}; Page={item.page}; "
            f"Score={item.score}\n{trim(item.text, 950)}"
        )
    return "\n\n".join(blocks)


def trim(text: str, limit: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "..."


def pick_informative_sentence(text: str) -> str:
    text = " ".join(text.split())
    sentences = re.split(r"(?<=[.!?])\s+", text)
    keywords = [
        "architecture",
        "framework",
        "training",
        "inference",
        "serving",
        "multimodal",
        "pre-training",
        "post-training",
        "reinforcement",
        "KVCache",
        "Mooncake",
        "Agent Swarm",
        "joint",
        "long-context",
    ]
    candidates: list[tuple[int, str]] = []
    for sentence in sentences:
        if len(sentence) < 60:
            continue
        lowered = sentence.lower()
        keyword_score = sum(1 for keyword in keywords if keyword.lower() in lowered)
        if keyword_score == 0:
            continue
        score = keyword_score
        if re.match(r"^(we|our|kimi|mooncake|hybrid|this|the)\b", sentence, flags=re.I):
            score += 3
        if re.match(r"^[0-9)\].,;:\-\s]+", sentence) or re.match(r"^[a-z]", sentence):
            score -= 2
        candidates.append((score, sentence))
    if candidates:
        candidates.sort(key=lambda item: item[0], reverse=True)
        return trim(candidates[0][1], 300)
    return trim(text, 300)
