from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class LLMAgentInfo:
    id: str
    name: str
    folder: str
    pdf_count: int
    documents: list[str]
    aliases: list[str] = field(default_factory=list)


@dataclass
class RagChunk:
    chunk_id: str
    agent_id: str
    agent_name: str
    document: str
    title: str
    path: str
    page: int
    text: str

    @property
    def searchable_text(self) -> str:
        return f"{self.agent_name} {self.agent_id} {self.title} {self.document}\n{self.text}"


@dataclass
class Evidence:
    chunk_id: str
    agent_id: str
    agent_name: str
    document: str
    title: str
    path: str
    page: int
    text: str
    score: float

    @property
    def label(self) -> str:
        return f"{self.agent_name} / {self.title} p.{self.page}"


@dataclass
class RelevanceDecision:
    is_relevant: bool
    reason: str
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class QueryIntent:
    mode: Literal["single", "multi"]
    selected_agent_ids: list[str]
    rationale: str
    confidence: float


@dataclass
class AgentResult:
    agent_id: str
    agent_name: str
    answer: str
    thinking_summary: list[str]
    evidence: list[Evidence]
    confidence: float


@dataclass
class AuditResult:
    passed: bool
    notes: list[str]
    revised_answer: str | None = None


@dataclass
class ChatResult:
    status: Literal["ok", "rejected", "error"]
    question: str
    answer: str
    thinking: list[str]
    intent: QueryIntent | None = None
    agents: list[AgentResult] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    audit: AuditResult | None = None


def to_jsonable(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return {key: to_jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    return value
