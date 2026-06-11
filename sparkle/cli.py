from __future__ import annotations

import argparse
import json
from pathlib import Path

from .workflow import SparkleTask, SparkleWorkflow


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the Sparkle technical research multi-agent workflow."
    )
    parser.add_argument(
        "--task-file",
        type=Path,
        default=Path("sparkle/config/default_task.json"),
        help="Path to a Sparkle task JSON file.",
    )
    parser.add_argument("--query", help="Override the task query.")
    parser.add_argument(
        "--source",
        action="append",
        default=[],
        help="Add a local source file or directory. Can be passed multiple times.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Override the output directory.",
    )
    parser.add_argument(
        "--max-sections",
        type=int,
        help="Override max section count.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Disable agent progress logs.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    task = SparkleTask.from_file(args.task_file)

    if args.query:
        task.query = args.query
    if args.source:
        task.source_paths.extend(Path(item) for item in args.source)
    if args.output_dir:
        task.output_dir = args.output_dir
    if args.max_sections:
        task.max_sections = args.max_sections
    if args.quiet:
        task.verbose = False

    result = SparkleWorkflow(task).run()
    print(json.dumps(result["artifacts"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
