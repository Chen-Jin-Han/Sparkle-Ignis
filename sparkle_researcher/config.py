from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv(PROJECT_ROOT / ".env")


def _path_from_env(name: str, default: Path) -> Path:
    value = os.getenv(name)
    return Path(value).expanduser().resolve() if value else default


@dataclass(frozen=True)
class Settings:
    project_root: Path = PROJECT_ROOT
    llm_dir: Path = _path_from_env("SPARKLE_LLM_DIR", PROJECT_ROOT / "LLM")
    index_dir: Path = _path_from_env("SPARKLE_INDEX_DIR", PROJECT_ROOT / ".sparkle" / "index")
    frontend_dir: Path = _path_from_env("SPARKLE_FRONTEND_DIR", PROJECT_ROOT / "frontend")
    frontend_dist_dir: Path = _path_from_env("SPARKLE_FRONTEND_DIST_DIR", PROJECT_ROOT / "frontend" / "dist")
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_base_url: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    deepseek_model: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    request_timeout_seconds: float = float(os.getenv("SPARKLE_REQUEST_TIMEOUT", "90"))
    chunk_size: int = int(os.getenv("SPARKLE_CHUNK_SIZE", "1500"))
    chunk_overlap: int = int(os.getenv("SPARKLE_CHUNK_OVERLAP", "180"))
    retrieval_top_k: int = int(os.getenv("SPARKLE_RETRIEVAL_TOP_K", "8"))
    multi_agent_limit: int = int(os.getenv("SPARKLE_MULTI_AGENT_LIMIT", "4"))
    relevance_threshold: float = float(os.getenv("SPARKLE_RELEVANCE_THRESHOLD", "0.018"))


settings = Settings()
