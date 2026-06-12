from __future__ import annotations

import argparse
import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from ..agents import ResearchOrchestrator
from ..config import settings
from ..models import to_jsonable
from ..rag import RagIndex


class AppState:
    def __init__(self) -> None:
        self.index = RagIndex()
        self.orchestrator = ResearchOrchestrator(self.index)


STATE = AppState()


class ResearchHandler(BaseHTTPRequestHandler):
    server_version = "SparkleResearcher/0.1"

    def do_OPTIONS(self) -> None:
        self._send_empty(HTTPStatus.NO_CONTENT)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/agents":
            self._send_json({"agents": STATE.orchestrator.list_agents()})
            return
        if parsed.path == "/api/index/status":
            self._send_json(STATE.index.status())
            return
        self._serve_static(parsed.path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/index/rebuild":
            try:
                self._send_json(STATE.index.build())
            except Exception as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return
        if parsed.path == "/api/chat":
            payload = self._read_json()
            question = str(payload.get("question", ""))
            agent_ids = payload.get("agent_ids") or []
            if isinstance(agent_ids, str):
                agent_ids = [] if agent_ids == "auto" else [agent_ids]
            try:
                result = STATE.orchestrator.chat(question, selected_agent_ids=agent_ids)
                self._send_json(to_jsonable(result))
            except Exception as exc:
                self._send_json({"status": "error", "answer": f"处理失败：{exc}"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return
        self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: object) -> None:
        return

    def _read_json(self) -> dict[str, object]:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def _serve_static(self, path: str) -> None:
        if path in ["", "/"]:
            path = "/index.html"
        static_root = settings.frontend_dist_dir if settings.frontend_dist_dir.exists() else settings.frontend_dir
        target = (static_root / path.lstrip("/")).resolve()
        root = static_root.resolve()
        if not str(target).startswith(str(root)) or not target.exists() or not target.is_file():
            target = root / "index.html"
        content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        data = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self._headers(content_type)
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self._headers("application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_empty(self, status: HTTPStatus) -> None:
        self.send_response(status)
        self._headers("text/plain; charset=utf-8")
        self.end_headers()

    def _headers(self, content_type: str) -> None:
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")


def run(host: str, port: int) -> None:
    settings.index_dir.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((host, port), ResearchHandler)
    print(f"Sparkle Researcher running at http://{host}:{port}")
    print(f"LLM docs: {settings.llm_dir}")
    print("Press Ctrl+C to stop.")
    server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Sparkle Researcher local web app.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    run(args.host, args.port)
