from __future__ import annotations

import re


CHINESE_QUERY_HINTS: list[tuple[str, str]] = [
    ("演进", "evolution development progression roadmap version scaling"),
    ("发展", "development evolution progression"),
    ("过程", "process pipeline stages training inference deployment"),
    ("框架", "framework architecture system design pipeline"),
    ("架构", "architecture framework components design"),
    ("训练", "training pretraining post-training alignment reinforcement learning"),
    ("推理", "inference decoding serving latency efficiency"),
    ("多模态", "multimodal vision audio video language"),
    ("安全", "safety alignment red teaming evaluation guard"),
    ("评测", "benchmark evaluation results performance"),
    ("对比", "compare comparison difference trade-off"),
    ("比较", "compare comparison difference trade-off"),
    ("区别", "difference contrast comparison"),
    ("总结", "summary summarize overview"),
    ("原理", "mechanism method approach design principle"),
    ("技术路线", "technical route methodology architecture evolution"),
]


def expand_query(question: str) -> str:
    additions = [english for chinese, english in CHINESE_QUERY_HINTS if chinese in question]
    normalized = normalize_model_tokens(question)
    if additions:
        return f"{question}\n{normalized}\n{' '.join(additions)}"
    return f"{question}\n{normalized}"


def normalize_model_tokens(text: str) -> str:
    fixed = text
    replacements = {
        "kimiai": "Kimi KIMI Moonshot Mooncake K1.5 K2 K2.5",
        "kimi ai": "Kimi KIMI Moonshot Mooncake K1.5 K2 K2.5",
        "deep seek": "DeepSeek",
        "通义千问": "Qwen",
        "智谱": "GLM ChatGLM Zhipu",
        "豆包": "Seed Doubao ByteDance",
        "chat gpt": "ChatGPT GPT OpenAI",
    }
    lowered = fixed.lower()
    for source, target in replacements.items():
        if source in lowered:
            fixed += f" {target}"
    version_tokens = re.findall(r"[A-Za-z]+[- ]?\d+(?:\.\d+)?[A-Za-z-]*", text)
    if version_tokens:
        fixed += " " + " ".join(version_tokens)
    return fixed
