# Sparkle: LangGraph x GPT Researcher
[LangGraph](https://python.langchain.com/docs/langgraph) is a library for building stateful, multi-actor applications with LLMs. 
Sparkle uses LangGraph and GPT Researcher to automate technical research and report generation for any given topic.

Looking for the AG2 version? See `multi_agents_ag2/` and the AG2 docs page.

## Use case
By using Langgraph, the research process can be significantly improved in depth and quality by leveraging multiple agents with specialized skills. 
Inspired by the recent [STORM](https://arxiv.org/abs/2402.14207) paper, this example showcases how a team of AI agents can work together to conduct research on a given topic, from planning to publication.

An average run generates a 5-6 page research report in multiple formats such as PDF, Docx and Markdown.

Please note: Multi-agents are utilizing the same configuration of models like GPT-Researcher does. However, only the SMART_LLM is used for the time being. Please refer to the [LLM config pages](https://docs.gptr.dev/docs/gpt-researcher/llms).

## The Sparkle Multi Agent Team
The Sparkle research team uses fire-related English names:
- **Ignis** - Oversees the research process and coordinates the other agents using LangGraph.
- **Ember** - Performs the initial browse/research pass and prepares source material.
- **Flare** - Plans the report outline and structure from the initial research.
- **Blaze** - Conducts in-depth section-level research with GPT Researcher.
- **Cinder** - Validates the correctness and completeness of drafts against the guidelines.
- **Forge** - Revises drafts based on Cinder's feedback.
- **Kindle** - Compiles and writes the final report.
- **Pyre** - Publishes the final report in Markdown, PDF, DOCX, or other configured formats.
- **Human** - Optional human-in-the-loop reviewer for plan feedback.

## How it works
Generally, the process is based on the following stages: 
1. Planning stage
2. Data collection and analysis
3. Review and revision
4. Writing and submission
5. Publication

### Architecture
<div align="center">
<img align="center" height="600" src="https://github.com/user-attachments/assets/ef561295-05f4-40a8-a57d-8178be687b18">
</div>
<br clear="all"/>

### Steps
More specifically (as seen in the architecture diagram) the process is as follows:
- Ember (gpt-researcher) - Browses the internet for initial research based on the given research task.
- Flare - Plans the report outline and structure based on the initial research.
- For each outline topic (in parallel):
  - Blaze (gpt-researcher) - Runs an in depth research on the subtopics and writes a draft.
  - Cinder - Validates the correctness of the draft given a set of criteria and provides feedback.
  - Forge - Revises the draft until it is satisfactory based on the reviewer feedback.
- Kindle - Compiles and writes the final report including an introduction, conclusion and references section from the given research findings.
- Pyre - Publishes the final report to multi formats such as PDF, Docx, Markdown, etc.

## How to run
1. Install required packages found in this root folder including `langgraph`:
    ```bash
    pip install -r requirements.txt
    ```
3. Update env variables, see the [GPT-Researcher docs](https://docs.gptr.dev/docs/gpt-researcher/llms) for more details.

2. Run the application:
    ```bash
    python main.py
    ```

## Usage
To change the research query and customize the report, edit the `task.json` file in the main directory.
#### Task.json contains the following fields:
- `query` - The research query or task.
- `model` - The OpenAI LLM to use for the agents.
- `max_sections` - The maximum number of sections in the report. Each section is a subtopic of the research query.
- `max_plan_revisions` - The maximum number of human-requested plan revisions before the workflow exits with a clear error. Set to `null` to rely on LangGraph's recursion limit instead.
- `include_human_feedback` - If true, the user can provide feedback to the agents. If false, the agents will work autonomously.
- `publish_formats` - The formats to publish the report in. The reports will be written in the `output` directory.
- `source` - The location from which to conduct the research. Options: `web` or `local`. For local, please add `DOC_PATH` env var.
- `follow_guidelines` - If true, the research report will follow the guidelines below. It will take longer to complete. If false, the report will be generated faster but may not follow the guidelines.
- `guidelines` - A list of guidelines that the report must follow.
- `verbose` - If true, the application will print detailed logs to the console.

#### For example:
```json
{
  "query": "Is AI in a hype cycle?",
  "model": "gpt-4o",
  "max_sections": 3,
  "max_plan_revisions": 3,
  "publish_formats": { 
    "markdown": true,
    "pdf": true,
    "docx": true
  },
  "include_human_feedback": false,
  "source": "web",
  "follow_guidelines": true,
  "guidelines": [
    "The report MUST fully answer the original question",
    "The report MUST be written in apa format",
    "The report MUST be written in english"
  ],
  "verbose": true
}
```

## To Deploy

```shell
pip install langgraph-cli
langgraph up
```

From there, see documentation [here](https://github.com/langchain-ai/langgraph-example) on how to use the streaming and async endpoints, as well as the playground.
