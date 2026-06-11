from __future__ import annotations

import argparse
import json
import mimetypes
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from .deepseek import DeepSeekClient
from .workflow import SparkleTask, SparkleWorkflow


ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = Path(__file__).resolve().parent / "web"
DEFAULT_TASK_FILE = Path(__file__).resolve().parent / "config" / "default_task.json"


class SparkleRequestHandler(BaseHTTPRequestHandler):
    server_version = "SparkleHTTP/1.0"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/status":
            self._send_json(self._status_payload())
            return
        if parsed.path.startswith("/outputs/"):
            self._serve_output(parsed.path)
            return
        self._serve_static(parsed.path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/run":
            self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)
            return

        try:
            body = self._read_json_body()
            result = self._run_workflow(body)
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        self._send_json(result)

    def _run_workflow(self, body: dict) -> dict:
        task = SparkleTask.from_file(DEFAULT_TASK_FILE)
        task.source_paths = [self._resolve_repo_path(path) for path in task.source_paths]
        query = str(body.get("query") or task.query).strip()
        task.query = query
        task.max_sections = int(body.get("max_sections") or task.max_sections)
        task.output_dir = ROOT / "outputs" / "sparkle"
        task.verbose = False

        extra_sources = body.get("source_paths") or []
        for source in extra_sources:
            task.source_paths.append(self._resolve_repo_path(Path(str(source))))

        result = SparkleWorkflow(task).run()
        use_deepseek = bool(body.get("use_deepseek"))
        client = DeepSeekClient(use_deepseek=use_deepseek)
        enhanced = client.polish_report(result["report"], query)
        if enhanced != result["report"]:
            result["report"] = enhanced
            markdown_path = result["artifacts"].get("markdown")
            if markdown_path:
                Path(markdown_path).write_text(enhanced, encoding="utf-8")

        result["deepseek"] = {
            "requested": use_deepseek,
            "enabled": client.enabled,
            "model": client.model,
            "base_url": client.base_url,
            "has_api_key": bool(client.api_key),
        }
        result["download_urls"] = self._artifact_urls(result["artifacts"])
        return result

    def _resolve_repo_path(self, path: Path) -> Path:
        return path if path.is_absolute() else ROOT / path

    def _artifact_urls(self, artifacts: dict[str, str]) -> dict[str, str]:
        urls = {}
        for name, artifact in artifacts.items():
            try:
                relative = Path(artifact).resolve().relative_to((ROOT / "outputs").resolve())
            except ValueError:
                continue
            urls[name] = "/outputs/" + relative.as_posix()
        return urls

    def _status_payload(self) -> dict:
        deepseek = DeepSeekClient()
        return {
            "name": "Sparkle",
            "has_deepseek_key": bool(deepseek.api_key),
            "deepseek_model": deepseek.model,
            "deepseek_base_url": deepseek.base_url,
            "default_deepseek_enabled": deepseek.enabled,
            "agents": [
                {"name": name, "role": role}
                for name, role in SparkleWorkflow.agents.values()
            ],
        }

    def _serve_static(self, request_path: str) -> None:
        if request_path in {"", "/"}:
            file_path = WEB_DIR / "index.html"
        else:
            clean_path = unquote(request_path).lstrip("/")
            file_path = WEB_DIR / clean_path

        self._serve_file(file_path, base_dir=WEB_DIR)

    def _serve_output(self, request_path: str) -> None:
        clean_path = unquote(request_path).removeprefix("/outputs/")
        self._serve_file(ROOT / "outputs" / clean_path, base_dir=ROOT / "outputs")

    def _serve_file(self, file_path: Path, base_dir: Path) -> None:
        try:
            resolved = file_path.resolve()
            resolved.relative_to(base_dir.resolve())
        except ValueError:
            self._send_json({"error": "Forbidden"}, status=HTTPStatus.FORBIDDEN)
            return

        if not resolved.exists() or not resolved.is_file():
            self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)
            return

        content_type = mimetypes.guess_type(str(resolved))[0] or "application/octet-stream"
        data = resolved.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def _send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format: str, *args: object) -> None:
        if os.getenv("SPARKLE_HTTP_LOGS", "false").lower() == "true":
            super().log_message(format, *args)


def run_server(host: str, port: int) -> None:
    server = ThreadingHTTPServer((host, port), SparkleRequestHandler)
    print(f"Sparkle web app running at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping Sparkle web app...")
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Sparkle local web app.")
    parser.add_argument("--host", default=os.getenv("SPARKLE_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.getenv("SPARKLE_PORT", "8080")))
    args = parser.parse_args()
    run_server(args.host, args.port)


if __name__ == "__main__":
    main()
