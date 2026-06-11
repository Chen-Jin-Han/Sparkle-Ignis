from __future__ import annotations

import json
import re
import textwrap
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


DEFAULT_GUIDELINES = [
    "Report language: Chinese.",
    "Focus on architecture, workflow, engineering implementation, and risks.",
    "Each section should include concrete implementation suggestions.",
    "Output should be suitable for technical interview and project documentation.",
]


@dataclass
class SparkleTask:
    """A complete research task for Sparkle."""

    query: str
    max_sections: int = 4
    source_paths: list[Path] = field(default_factory=list)
    guidelines: list[str] = field(default_factory=lambda: list(DEFAULT_GUIDELINES))
    output_dir: Path = Path("outputs/sparkle")
    publish_formats: dict[str, bool] = field(
        default_factory=lambda: {"markdown": True, "json": True}
    )
    verbose: bool = True

    @classmethod
    def from_file(cls, task_file: Path) -> "SparkleTask":
        with task_file.open("r", encoding="utf-8") as handle:
            data = json.load(handle)

        source_paths = [Path(item) for item in data.get("source_paths", [])]
        return cls(
            query=data["query"],
            max_sections=int(data.get("max_sections", 4)),
            source_paths=source_paths,
            guidelines=data.get("guidelines", DEFAULT_GUIDELINES),
            output_dir=Path(data.get("output_dir", "outputs/sparkle")),
            publish_formats=data.get(
                "publish_formats", {"markdown": True, "json": True}
            ),
            verbose=bool(data.get("verbose", True)),
        )


@dataclass
class FlameAgentResult:
    agent_name: str
    role: str
    summary: str
    payload: dict


class SparkleWorkflow:
    """A deterministic multi-agent workflow for technical research reports.

    This workflow mirrors the production LangGraph flow in ``multi_agents`` but
    keeps a no-key path for demos, technical interviews, and local validation.
    """

    agents = {
        "orchestrator": ("Ignis", "orchestrates the whole Sparkle workflow"),
        "scout": ("Ember", "collects local research material"),
        "planner": ("Flare", "turns research material into a report plan"),
        "researcher": ("Blaze", "drafts section-level technical findings"),
        "reviewer": ("Cinder", "reviews drafts against quality guidelines"),
        "reviser": ("Forge", "revises drafts using reviewer feedback"),
        "writer": ("Kindle", "assembles the final report"),
        "publisher": ("Pyre", "publishes report artifacts"),
    }

    def __init__(self, task: SparkleTask):
        self.task = task
        self.results: list[FlameAgentResult] = []

    def run(self) -> dict:
        self._log("Ignis", f"Starting Sparkle research: {self.task.query}")
        corpus = self._ember_collect_sources()
        plan = self._flare_plan(corpus)
        drafts = [self._blaze_research(section, corpus) for section in plan["sections"]]
        reviewed = [self._forge_revise(draft) for draft in drafts]
        report = self._kindle_write(plan, reviewed)
        artifacts = self._pyre_publish(report, plan, reviewed)
        return {
            "task": self.task.query,
            "agents": [result.__dict__ for result in self.results],
            "plan": plan,
            "artifacts": artifacts,
            "report": report,
        }

    def _ember_collect_sources(self) -> list[dict[str, str]]:
        documents = []
        for path in self._iter_source_files(self.task.source_paths):
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                text = path.read_text(encoding="gb18030", errors="ignore")
            documents.append(
                {
                    "title": path.stem,
                    "path": str(path),
                    "text": self._normalize_text(text),
                }
            )

        if not documents:
            documents.append(
                {
                    "title": "Sparkle built-in research brief",
                    "path": "built-in",
                    "text": self._built_in_brief(),
                }
            )

        self._record(
            "Ember",
            "Source scout",
            f"Collected {len(documents)} research source(s).",
            {"sources": [{"title": item["title"], "path": item["path"]} for item in documents]},
        )
        return documents

    def _flare_plan(self, corpus: list[dict[str, str]]) -> dict:
        candidate_sections = [
            "项目定位与应用场景",
            "多 Agent 架构设计",
            "技术调研与信息检索流程",
            "报告生成、审查与发布流程",
            "工程化部署与可观测性",
            "风险控制与后续优化",
        ]
        selected = candidate_sections[: max(1, self.task.max_sections)]
        plan = {
            "title": f"Sparkle 技术调研与报告生成多 Agent 工作流系统",
            "date": time.strftime("%Y-%m-%d"),
            "sections": selected,
            "guidelines": self.task.guidelines,
            "source_count": len(corpus),
        }
        self._record(
            "Flare",
            "Research planner",
            f"Planned {len(selected)} report section(s).",
            plan,
        )
        return plan

    def _blaze_research(self, section: str, corpus: list[dict[str, str]]) -> dict:
        keywords = self._keywords_for_section(section)
        evidence = self._select_evidence(corpus, keywords)
        if not evidence:
            evidence = self._select_evidence(corpus, [])

        bullet_points = self._build_section_points(section, evidence)
        draft = {
            "section": section,
            "keywords": keywords,
            "evidence": evidence[:5],
            "draft": "\n".join(f"- {point}" for point in bullet_points),
        }
        self._record(
            "Blaze",
            "Depth researcher",
            f"Drafted section: {section}",
            {"section": section, "evidence_count": len(draft["evidence"])},
        )
        return draft

    def _cinder_review(self, draft: dict) -> dict:
        notes = []
        text = draft["draft"]
        if len(text) < 180:
            notes.append("Draft is too short for an interview-ready technical report.")
        if "Sparkle" not in text:
            notes.append("Draft should explicitly connect the design back to Sparkle.")
        if not draft.get("evidence"):
            notes.append("Draft needs evidence from source material.")
        if not notes:
            notes.append("Accepted. The draft is specific enough for publication.")

        review = {"section": draft["section"], "notes": notes, "accepted": notes[0].startswith("Accepted")}
        self._record(
            "Cinder",
            "Quality reviewer",
            f"Reviewed section: {draft['section']}",
            review,
        )
        return review

    def _forge_revise(self, draft: dict) -> dict:
        review = self._cinder_review(draft)
        if review["accepted"]:
            revised = draft
        else:
            additions = [
                "- Sparkle 在该部分采用可落地的工程方案，保证从任务输入到报告产物可追踪。",
                "- 该设计补充了质量门禁、输出目录和结构化中间结果，便于演示、测试和二次扩展。",
            ]
            revised = {**draft, "draft": draft["draft"] + "\n" + "\n".join(additions)}

        self._record(
            "Forge",
            "Draft reviser",
            f"Revised section: {draft['section']}",
            {"section": draft["section"], "changed": revised is not draft},
        )
        return revised

    def _kindle_write(self, plan: dict, drafts: list[dict]) -> str:
        guidelines = "\n".join(f"- {item}" for item in self.task.guidelines)
        sections = "\n\n".join(
            f"## {draft['section']}\n{draft['draft']}" for draft in drafts
        )
        agent_table = "\n".join(
            f"| {name} | {role} |" for name, role in self.agents.values()
        )
        report = textwrap.dedent(
            f"""
            # {plan['title']}

            生成日期：{plan['date']}

            ## 摘要
            Sparkle 是面向技术调研与报告生成的多 Agent 工作流系统。它以 GitHub 开源项目 GPT Researcher 的研究能力为底座，
            结合本地可运行的 Sparkle 工作流，将调研、规划、并行撰写、质量审查、修订和发布串成闭环。

            ## Agent 分工
            | Agent | Role |
            | --- | --- |
            {agent_table}

            ## 写作约束
            {guidelines}

            {sections}

            ## 结论
            Sparkle 的核心价值不是单次文本生成，而是把调研任务拆成可观测、可审查、可复用的多 Agent 流程。
            在面试或项目答辩中，可以重点说明 LangGraph/CrewAI 式编排思想、检索增强生成、质量反馈回路、报告多格式发布、
            以及 Docker/Kubernetes/Nginx/MySQL/Redis 等工程化部署路径。
            """
        ).strip()
        self._record(
            "Kindle",
            "Report writer",
            "Assembled the final technical report.",
            {"characters": len(report)},
        )
        return report

    def _pyre_publish(self, report: str, plan: dict, drafts: list[dict]) -> dict[str, str]:
        slug = self._slugify(self.task.query)
        output_dir = self.task.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        artifacts = {}
        if self.task.publish_formats.get("markdown", True):
            markdown_path = output_dir / f"{slug}.md"
            markdown_path.write_text(report, encoding="utf-8")
            artifacts["markdown"] = str(markdown_path)

        if self.task.publish_formats.get("json", True):
            json_path = output_dir / f"{slug}.json"
            json_path.write_text(
                json.dumps(
                    {
                        "task": self.task.query,
                        "plan": plan,
                        "drafts": drafts,
                        "agents": [result.__dict__ for result in self.results],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            artifacts["json"] = str(json_path)

        self._record(
            "Pyre",
            "Report publisher",
            f"Published {len(artifacts)} artifact(s).",
            artifacts,
        )
        return artifacts

    def _iter_source_files(self, source_paths: Iterable[Path]) -> Iterable[Path]:
        for source in source_paths:
            path = source
            if not path.is_absolute():
                path = Path.cwd() / path
            if path.is_dir():
                yield from sorted(
                    item
                    for item in path.rglob("*")
                    if item.suffix.lower() in {".md", ".txt", ".py", ".json", ".toml"}
                )
            elif path.exists():
                yield path

    def _select_evidence(self, corpus: list[dict[str, str]], keywords: list[str]) -> list[str]:
        evidence: list[str] = []
        for document in corpus:
            sentences = re.split(r"(?<=[。.!?])\s+|\n+", document["text"])
            for sentence in sentences:
                normalized = sentence.strip()
                if not normalized:
                    continue
                if not keywords or any(word.lower() in normalized.lower() for word in keywords):
                    evidence.append(f"{normalized} ({document['title']})")
                if len(evidence) >= 8:
                    return evidence
        return evidence

    def _build_section_points(self, section: str, evidence: list[str]) -> list[str]:
        evidence_hint = evidence[0] if evidence else "当前任务要求构建完整调研与报告链路。"
        templates = {
            "项目定位与应用场景": [
                f"Sparkle 定位为技术调研与报告生成助手，适合课程项目、科研选题、竞品分析和面试作品集展示；依据：{evidence_hint}",
                "系统输入为自然语言研究任务，输出为结构化 Markdown/JSON 报告，并保留 Agent 中间结果。",
                "该定位贴合简历中的 CrewAI、多 Agent、Flutter、云原生和大模型微调经历，便于形成完整项目叙事。",
            ],
            "多 Agent 架构设计": [
                "Ignis 负责编排全局状态，Ember 采集资料，Flare 制定大纲，Blaze 进行分节调研。",
                "Cinder 与 Forge 形成审查和修订闭环，Kindle 负责成文，Pyre 负责产物发布。",
                f"这种职责拆分降低单 Agent 上下文压力，也让每个节点都可以单独替换为 CrewAI、LangGraph 或本地模型实现；依据：{evidence_hint}",
            ],
            "技术调研与信息检索流程": [
                "Ember 先读取本地文档、代码和配置，生产可追踪证据池；接入线上检索器时可扩展 Tavily、DuckDuckGo、Arxiv 或 GitHub MCP。",
                "Flare 根据证据池生成章节计划，Blaze 按章节并行调研，减少长报告生成时的信息遗漏。",
                f"检索结果在进入写作前被压缩为 evidence，避免把整篇网页或源码直接塞进提示词；依据：{evidence_hint}",
            ],
            "报告生成、审查与发布流程": [
                "Kindle 将分节草稿统一成摘要、Agent 分工、写作约束、主体章节和结论。",
                "Cinder 检查证据、长度、与 Sparkle 目标的关联度；Forge 自动补齐缺失的工程细节。",
                f"Pyre 输出 Markdown 与 JSON，JSON 记录 plan、drafts 和 agents，方便前端展示或后续入库；依据：{evidence_hint}",
            ],
            "工程化部署与可观测性": [
                "后端可以沿用 FastAPI/LangGraph 服务化入口，前端可用 Flutter 或 Next.js 展示任务状态和报告产物。",
                "Docker 镜像负责封装依赖，Kubernetes Deployment/Service/Ingress 负责弹性部署，Nginx 负责反向代理。",
                f"MySQL 可保存任务与报告元数据，Redis 可作为队列、缓存或任务状态通道；依据：{evidence_hint}",
            ],
            "风险控制与后续优化": [
                "主要风险包括检索噪声、引用失真、长上下文成本、模型幻觉和多 Agent 循环失控。",
                "可以通过来源白名单、引用校验、最大修订次数、日志追踪和人工反馈节点降低风险。",
                f"后续可加入 LoRA 微调的领域模型、向量数据库记忆和报告评分评测集；依据：{evidence_hint}",
            ],
        }
        return templates.get(section, [f"Sparkle section draft: {section}. Evidence: {evidence_hint}"])

    def _keywords_for_section(self, section: str) -> list[str]:
        keyword_map = {
            "项目定位与应用场景": ["Sparkle", "research", "report", "CrewAI", "Agent"],
            "多 Agent 架构设计": ["agent", "workflow", "LangGraph", "CrewAI", "planner"],
            "技术调研与信息检索流程": ["research", "retriever", "source", "RAG", "GitHub"],
            "报告生成、审查与发布流程": ["report", "review", "publish", "markdown", "docx"],
            "工程化部署与可观测性": ["Docker", "Kubernetes", "Nginx", "MySQL", "Redis"],
            "风险控制与后续优化": ["risk", "hallucination", "LoRA", "evaluation", "quality"],
        }
        return keyword_map.get(section, [])

    def _built_in_brief(self) -> str:
        return textwrap.dedent(
            """
            Sparkle is a technical research and report generation multi-agent workflow.
            The system is adapted from GPT Researcher and keeps a local runnable path.
            The resume context includes CrewAI multi-agent workflow design, Planner,
            Researcher, Executor and Reviewer roles, Linux, Docker, Kubernetes, Nginx,
            MySQL, Redis, Flutter, Vue, PyTorch, TensorFlow, MindSpore, Transformer,
            BERT, GPT, YOLO, CNN, RNN/LSTM, GAN, Mamba, and LLaMA-Factory LoRA practice.
            Sparkle should highlight research planning, retrieval augmented generation,
            draft review, revision, and report publishing.
            """
        ).strip()

    def _normalize_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    def _slugify(self, text: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", text).strip("-").lower()
        return slug[:80] or "sparkle-report"

    def _record(self, agent_name: str, role: str, summary: str, payload: dict) -> None:
        self.results.append(
            FlameAgentResult(
                agent_name=agent_name,
                role=role,
                summary=summary,
                payload=payload,
            )
        )
        self._log(agent_name, summary)

    def _log(self, agent_name: str, message: str) -> None:
        if self.task.verbose:
            print(f"{agent_name}: {message}")
