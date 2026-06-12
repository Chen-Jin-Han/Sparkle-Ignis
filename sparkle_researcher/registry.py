from __future__ import annotations

import re
from pathlib import Path

from .config import settings
from .models import LLMAgentInfo


AGENT_ALIASES: dict[str, list[str]] = {
    "chatgpt": ["chatgpt", "gpt", "gpt-4", "openai", "o1", "o3", "chat gpt"],
    "claude": ["claude", "anthropic", "constitutional ai"],
    "deepseek": ["deepseek", "deep seek", "深度求索"],
    "gemini": ["gemini", "google", "bard"],
    "gemma": ["gemma", "paligemma", "shieldgemma", "codegemma"],
    "glm": ["glm", "chatglm", "zhipu", "智谱", "cogvlm", "cogview"],
    "kimi": ["kimi", "kimiai", "moonshot", "moon cake", "mooncake", "月之暗面"],
    "llama": ["llama", "llama 2", "llama 3", "meta", "code llama"],
    "minimax": ["minimax", "mini max", "abab", "海螺"],
    "qwen": ["qwen", "通义", "千问", "qwen2", "qwen3", "qwen-vl"],
    "seed": ["seed", "doubao", "豆包", "bytedance", "字节", "seedance", "seedream"],
}


def normalize_agent_id(name: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if normalized == "llama":
        return "llama"
    return normalized


def scan_agents(llm_dir: Path | None = None) -> list[LLMAgentInfo]:
    root = llm_dir or settings.llm_dir
    if not root.exists():
        return []

    agents: list[LLMAgentInfo] = []
    for folder in sorted([item for item in root.iterdir() if item.is_dir()], key=lambda p: p.name.lower()):
        pdfs = sorted(folder.glob("*.pdf"), key=lambda p: p.name.lower())
        if not pdfs:
            continue
        agent_id = normalize_agent_id(folder.name)
        aliases = AGENT_ALIASES.get(agent_id, [])
        agents.append(
            LLMAgentInfo(
                id=agent_id,
                name=folder.name,
                folder=str(folder),
                pdf_count=len(pdfs),
                documents=[pdf.name for pdf in pdfs],
                aliases=aliases,
            )
        )
    return agents


def agent_map(llm_dir: Path | None = None) -> dict[str, LLMAgentInfo]:
    return {agent.id: agent for agent in scan_agents(llm_dir)}


def detect_agent_mentions(question: str, agents: list[LLMAgentInfo]) -> list[str]:
    text = question.lower()
    detected: list[str] = []
    for agent in agents:
        terms = [agent.id, agent.name.lower(), *[alias.lower() for alias in agent.aliases]]
        if any(_contains_term(text, term) for term in terms):
            detected.append(agent.id)
    return detected


def _contains_term(text: str, term: str) -> bool:
    term = term.strip().lower()
    if not term:
        return False
    if re.search(r"[\u4e00-\u9fff]", term):
        return term in text
    return re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", text) is not None
