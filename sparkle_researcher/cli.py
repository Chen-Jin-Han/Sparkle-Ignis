from __future__ import annotations

import argparse
import json
import sys

from .agents import ResearchOrchestrator
from .models import to_jsonable
from .rag import RagIndex


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Sparkle Researcher utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list-agents")
    subparsers.add_parser("status")
    build_parser = subparsers.add_parser("build-index")
    build_parser.add_argument("--agent", action="append", default=[])
    build_parser.add_argument("--full", action="store_true")
    chat_parser = subparsers.add_parser("chat")
    chat_parser.add_argument("question")
    chat_parser.add_argument("--agent", action="append", default=[])
    args = parser.parse_args()

    index = RagIndex()
    orchestrator = ResearchOrchestrator(index)

    if args.command == "list-agents":
        print(json.dumps(orchestrator.list_agents(), ensure_ascii=False, indent=2))
    elif args.command == "status":
        print(json.dumps(index.status(), ensure_ascii=False, indent=2))
    elif args.command == "build-index":
        print(json.dumps(index.build(agent_ids=args.agent, full=args.full), ensure_ascii=False, indent=2))
    elif args.command == "chat":
        result = orchestrator.chat(args.question, selected_agent_ids=args.agent)
        print(json.dumps(to_jsonable(result), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
