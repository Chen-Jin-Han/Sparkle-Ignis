# Sparkle Multi-Agent Workflow

Sparkle 是一个技术调研与报告生成多 Agent 工作流系统，基于 GitHub 开源项目
[GPT Researcher](https://github.com/assafelovic/gpt-researcher) 改造。

## 简历对齐

从简历中可识别到的相关经历包括：

- CrewAI 多 Agent 工作流，包含 Planner、Researcher、Executor、Reviewer 等角色。
- Linux、Docker、Kubernetes、Nginx、MySQL、Redis 等部署与运维基础。
- Flutter、Vue、Python、C/C++ 等开发经历。
- PyTorch、TensorFlow、MindSpore，以及 Transformer、BERT、GPT、YOLO、CNN、RNN/LSTM、GAN、Mamba。
- LLaMA-Factory、Qwen / LLaMA、LoRA、推理测试和 instruction tuning。

Sparkle 的实现把这些经历串成一个可演示的项目：调研任务输入后，由多个 Agent 共同完成资料采集、规划、撰写、审查、修订和发布。

## Agent 命名

所有 AI Agent 都使用与火焰相关的英文名：

| Agent | 职责 |
| --- | --- |
| Ignis | 全局编排、状态管理、任务生命周期控制 |
| Ember | 收集本地资料、代码、配置和未来的 Web/GitHub 检索结果 |
| Flare | 生成报告标题、章节计划和写作约束 |
| Blaze | 按章节执行深入技术调研并生成草稿 |
| Cinder | 审查草稿质量、证据和工程完整性 |
| Forge | 根据审查意见自动修订草稿 |
| Kindle | 汇总章节并生成完整技术报告 |
| Pyre | 发布 Markdown、JSON，后续可扩展 PDF / DOCX |

## 双工作流

Sparkle 现在包含两条可用路径：

- `sparkle` 本地工作流：不需要 API key，适合面试演示、离线验证和项目讲解。
- `multi_agents` 生产工作流：沿用 GPT Researcher + LangGraph，需要配置 LLM 和检索器 API key，适合真实联网调研。

## 本地运行

```bash
python -m sparkle.cli
```

输出目录默认为：

```text
outputs/sparkle/
```

自定义任务：

```bash
python -m sparkle.cli --query "AI Agent 论文调研系统" --source docs --max-sections 4
```

## Docker 一键部署

Windows 下可以直接运行：

```bat
start-sparkle.bat
```

或者运行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start-sparkle.ps1
```

启动后访问：

```text
http://localhost:8080
```

停止容器：

```bat
stop-sparkle.bat
```

也可以手动执行：

```bash
docker compose --env-file .env.sparkle -f docker-compose.sparkle.yml up -d --build
docker compose --env-file .env.sparkle -f docker-compose.sparkle.yml down
```

## DeepSeek 配置

Sparkle 不会把 API Key 写进代码仓库。使用 DeepSeek 时：

1. 复制 `.env.sparkle.example` 为 `.env.sparkle`。
2. 设置 `SPARKLE_USE_DEEPSEEK=true`。
3. 将你的 DeepSeek API Key 写入 `DEEPSEEK_API_KEY`。

默认配置：

```env
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
```

## 生产工作流

配置环境变量后运行：

```bash
python multi_agents/main.py
```

默认任务文件：

```text
multi_agents/task.json
```

## 工程化扩展

- 后端：FastAPI + LangGraph，暴露任务创建、状态查询、报告下载接口。
- 前端：Flutter 或 Next.js，展示 Agent 日志、流程状态、报告预览。
- 存储：MySQL 保存任务与报告元数据，Redis 做缓存、队列或实时状态。
- 部署：Docker 打包，Kubernetes 管理 Deployment / Service / Ingress，Nginx 反向代理。
- 质量：最大修订次数、引用校验、来源白名单、日志追踪、人工反馈节点和自动评测集。
