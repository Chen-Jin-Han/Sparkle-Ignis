# Sparkle Research Brief

Sparkle 是一个面向技术调研与报告生成的多 Agent 工作流系统，底座来自 GitHub 开源项目 GPT Researcher。
系统目标是把自然语言调研任务拆解为可追踪、可审查、可发布的工程流程。

## Resume Alignment

简历中可识别的技术经历包括 CrewAI 多 Agent 工作流、Planner / Researcher / Executor / Reviewer 角色设计、
Linux、Docker、Kubernetes、Nginx、MySQL、Redis、Flutter、Vue、PyTorch、TensorFlow、MindSpore、
Transformer、BERT、GPT、YOLO、CNN、RNN/LSTM、GAN、Mamba，以及使用 LLaMA-Factory 进行 Qwen / LLaMA
系列模型的数据准备、LoRA、推理测试和 instruction tuning。

## Workflow Requirements

Sparkle 的工作流包括任务接收、资料采集、研究规划、并行分节调研、草稿审查、自动修订、总报告写作和产物发布。
每个 AI Agent 都使用与火焰相关的英文名：

- Ignis: 负责全局编排、状态管理和任务生命周期。
- Ember: 负责收集本地资料、代码、配置和未来的 Web/GitHub 检索结果。
- Flare: 负责把初步资料转成报告标题、章节计划和写作约束。
- Blaze: 负责对每个章节进行深入技术调研并生成草稿。
- Cinder: 负责按照指南审查草稿，检查证据、完整性和工程可落地性。
- Forge: 负责根据审查意见修订草稿，补齐架构和实现细节。
- Kindle: 负责把所有章节汇总为完整技术报告。
- Pyre: 负责导出 Markdown、JSON，以及后续可扩展的 PDF / DOCX。

## Engineering Direction

生产版本可以继续沿用 GPT Researcher 的 LangGraph 多 Agent 结构，接入 Tavily、DuckDuckGo、Arxiv、
Semantic Scholar、GitHub MCP 等检索器。后端可以使用 FastAPI 暴露任务接口，前端可以用 Flutter 或 Next.js
展示任务进度、Agent 日志和报告。部署上可使用 Docker 打包，Kubernetes 管理 Deployment、Service 和 Ingress，
Nginx 做反向代理，MySQL 保存任务与报告元数据，Redis 提供缓存、队列或任务状态通道。

## Quality And Risk

主要风险包括检索噪声、引用失真、模型幻觉、长上下文成本、多 Agent 循环失控和报告结构漂移。
缓解方式包括来源白名单、引用校验、最大修订次数、结构化中间结果、日志追踪、人工反馈节点和自动评测集。
