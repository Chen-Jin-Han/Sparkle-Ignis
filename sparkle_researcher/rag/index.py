from __future__ import annotations

import json
import pickle
import threading
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from ..config import settings
from ..models import Evidence, RagChunk
from ..registry import LLMAgentInfo, scan_agents
from .pdf_loader import extract_pdf_pages
from .query import expand_query
from .text_splitter import split_text


class RagIndex:
    """Hybrid index.

    The metadata index is tiny and fast, so it is used for relevance and routing.
    Full PDF text is indexed lazily per downstream Agent after routing.
    """

    def __init__(self, llm_dir: Path | None = None, index_dir: Path | None = None):
        self.llm_dir = llm_dir or settings.llm_dir
        self.index_dir = index_dir or settings.index_dir
        self.agent_index_dir = self.index_dir / "agents"
        self.metadata_path = self.index_dir / "metadata_index.pkl"
        self.metadata_manifest_path = self.index_dir / "metadata_manifest.json"
        self._lock = threading.Lock()
        self.metadata_payload: dict[str, Any] | None = None
        self.agent_payloads: dict[str, dict[str, Any]] = {}
        self.last_build_seconds: float | None = None

    def status(self) -> dict[str, Any]:
        agents = scan_agents(self.llm_dir)
        current_signature = self._signature()
        manifest = self._read_manifest(self.metadata_manifest_path)
        metadata_built = self.metadata_path.exists() and self.metadata_manifest_path.exists()
        metadata_stale = manifest.get("signature") != current_signature if manifest else True
        built_agent_ids = self._built_agent_ids(agents)
        return {
            "built": metadata_built,
            "loaded": self.metadata_payload is not None,
            "stale": metadata_stale,
            "chunk_count": manifest.get("chunk_count", 0),
            "document_count": manifest.get("document_count", sum(agent.pdf_count for agent in agents)),
            "agent_count": manifest.get("agent_count", len(agents)),
            "agent_index_count": len(built_agent_ids),
            "built_agents": built_agent_ids,
            "built_at": manifest.get("built_at"),
            "last_build_seconds": self.last_build_seconds,
        }

    def build(self, agent_ids: list[str] | None = None, *, full: bool = False) -> dict[str, Any]:
        if full:
            self.build_metadata(force=True)
            for agent in scan_agents(self.llm_dir):
                if agent_ids is None or agent.id in set(agent_ids):
                    self.build_agent(agent.id, force=True)
            return self.status()
        if agent_ids:
            self.build_metadata(force=False)
            for agent_id in agent_ids:
                self.build_agent(agent_id, force=True)
            return self.status()
        return self.build_metadata(force=True)

    def build_metadata(self, *, force: bool = False) -> dict[str, Any]:
        started = time.time()
        with self._lock:
            if not force and self.metadata_path.exists() and not self._metadata_stale():
                self.load_metadata()
                return self.status()

            self.index_dir.mkdir(parents=True, exist_ok=True)
            chunks = self._metadata_chunks()
            payload = self._fit_payload(chunks)
            with self.metadata_path.open("wb") as handle:
                pickle.dump(payload, handle)

            agents = scan_agents(self.llm_dir)
            manifest = {
                "built_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "signature": self._signature(),
                "chunk_count": len(chunks),
                "document_count": sum(agent.pdf_count for agent in agents),
                "agent_count": len(agents),
                "kind": "metadata",
            }
            self.metadata_manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            self.metadata_payload = payload
            self.last_build_seconds = round(time.time() - started, 2)
            return self.status()

    def build_agent(self, agent_id: str, *, force: bool = False) -> dict[str, Any]:
        started = time.time()
        agents = {agent.id: agent for agent in scan_agents(self.llm_dir)}
        if agent_id not in agents:
            raise ValueError(f"Unknown agent id: {agent_id}")
        manifest_path = self._agent_manifest_path(agent_id)
        index_path = self._agent_index_path(agent_id)
        if not force and index_path.exists() and manifest_path.exists() and not self._agent_stale(agent_id):
            self.load_agent(agent_id)
            return self.status()

        with self._lock:
            self.agent_index_dir.mkdir(parents=True, exist_ok=True)
            chunks = self._extract_agent_chunks(agents[agent_id])
            if not chunks:
                chunks = self._metadata_chunks([agents[agent_id]])
            payload = self._fit_payload(chunks)
            with index_path.open("wb") as handle:
                pickle.dump(payload, handle)

            manifest = {
                "built_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "signature": self._agent_signature(agent_id),
                "chunk_count": len(chunks),
                "document_count": agents[agent_id].pdf_count,
                "agent_id": agent_id,
                "kind": "agent",
            }
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            self.agent_payloads[agent_id] = payload
            self.last_build_seconds = round(time.time() - started, 2)
            return self.status()

    def load_metadata(self) -> None:
        if self.metadata_payload is not None and not self._metadata_stale():
            return
        if not self.metadata_path.exists() or self._metadata_stale():
            self.build_metadata(force=True)
            return
        with self.metadata_path.open("rb") as handle:
            self.metadata_payload = pickle.load(handle)

    def load_agent(self, agent_id: str) -> None:
        if agent_id in self.agent_payloads and not self._agent_stale(agent_id):
            return
        index_path = self._agent_index_path(agent_id)
        if not index_path.exists() or self._agent_stale(agent_id):
            self.build_agent(agent_id)
            return
        with index_path.open("rb") as handle:
            self.agent_payloads[agent_id] = pickle.load(handle)

    def search(self, question: str, agent_ids: list[str] | None = None, top_k: int | None = None) -> list[Evidence]:
        top_k = top_k or settings.retrieval_top_k
        if agent_ids:
            payloads: list[dict[str, Any]] = []
            for agent_id in agent_ids:
                self.load_agent(agent_id)
                payload = self.agent_payloads.get(agent_id)
                if payload:
                    payloads.append(payload)
            return self._search_payloads(question, payloads, top_k)

        self.load_metadata()
        return self._search_payloads(question, [self.metadata_payload] if self.metadata_payload else [], top_k)

    def _search_payloads(self, question: str, payloads: list[dict[str, Any]], top_k: int) -> list[Evidence]:
        ranked: list[Evidence] = []
        for payload in payloads:
            if not payload:
                continue
            ranked.extend(self._search_payload(question, payload, top_k))
        ranked.sort(key=lambda item: item.score, reverse=True)
        return ranked[:top_k]

    def _search_payload(self, question: str, payload: dict[str, Any], top_k: int) -> list[Evidence]:
        chunks = [RagChunk(**item) for item in payload["chunks"]]
        if not chunks:
            return []
        expanded = expand_query(question)
        word_vectorizer = payload["word_vectorizer"]
        char_vectorizer = payload["char_vectorizer"]
        word_query = word_vectorizer.transform([expanded])
        char_query = char_vectorizer.transform([expanded])
        word_scores = cosine_similarity(word_query, payload["word_matrix"]).ravel()
        char_scores = cosine_similarity(char_query, payload["char_matrix"]).ravel()
        scores = (word_scores * 0.72) + (char_scores * 0.28)
        count = min(max(top_k * 8, top_k), len(chunks))
        candidate_indices = np.argpartition(scores, -count)[-count:]
        ordered = sorted(candidate_indices, key=lambda idx: scores[idx], reverse=True)
        evidence: list[Evidence] = []
        per_document: dict[str, int] = {}
        for idx in ordered:
            chunk = chunks[int(idx)]
            if per_document.get(chunk.document, 0) >= 3:
                continue
            evidence.append(
                Evidence(
                    chunk_id=chunk.chunk_id,
                    agent_id=chunk.agent_id,
                    agent_name=chunk.agent_name,
                    document=chunk.document,
                    title=chunk.title,
                    path=chunk.path,
                    page=chunk.page,
                    text=chunk.text,
                    score=round(float(scores[idx]), 4),
                )
            )
            per_document[chunk.document] = per_document.get(chunk.document, 0) + 1
            if len(evidence) >= top_k:
                break
        return evidence

    def _fit_payload(self, chunks: list[RagChunk]) -> dict[str, Any]:
        if not chunks:
            raise RuntimeError(f"No searchable text was extracted from {self.llm_dir}")
        texts = [chunk.searchable_text for chunk in chunks]
        word_vectorizer = TfidfVectorizer(
            lowercase=True,
            max_features=100_000,
            ngram_range=(1, 2),
            token_pattern=r"(?u)\b\w+\b",
            min_df=1,
        )
        char_vectorizer = TfidfVectorizer(
            lowercase=True,
            analyzer="char_wb",
            ngram_range=(3, 5),
            max_features=120_000,
            min_df=1,
        )
        return {
            "chunks": [asdict(chunk) for chunk in chunks],
            "word_vectorizer": word_vectorizer,
            "char_vectorizer": char_vectorizer,
            "word_matrix": word_vectorizer.fit_transform(texts),
            "char_matrix": char_vectorizer.fit_transform(texts),
        }

    def _metadata_chunks(self, agents: list[LLMAgentInfo] | None = None) -> list[RagChunk]:
        chunks: list[RagChunk] = []
        for agent in agents or scan_agents(self.llm_dir):
            aliases = " ".join(agent.aliases)
            for document in agent.documents:
                path = Path(agent.folder) / document
                title = Path(document).stem
                text = (
                    f"{agent.name} {agent.id} {aliases}. "
                    f"Technical report PDF title: {title}. "
                    f"Document belongs to {agent.name} LLM family."
                )
                chunks.append(
                    RagChunk(
                        chunk_id=f"metadata:{agent.id}:{document}",
                        agent_id=agent.id,
                        agent_name=agent.name,
                        document=document,
                        title=title,
                        path=str(path),
                        page=0,
                        text=text,
                    )
                )
        return chunks

    def _extract_agent_chunks(self, agent: LLMAgentInfo) -> list[RagChunk]:
        chunks: list[RagChunk] = []
        for document in agent.documents:
            path = Path(agent.folder) / document
            try:
                pages = extract_pdf_pages(path)
            except Exception:
                pages = []
            for page in pages:
                pieces = split_text(page.text, settings.chunk_size, settings.chunk_overlap)
                for piece_index, piece in enumerate(pieces):
                    chunks.append(
                        RagChunk(
                            chunk_id=f"{agent.id}:{document}:p{page.page_number}:c{piece_index}",
                            agent_id=agent.id,
                            agent_name=agent.name,
                            document=document,
                            title=Path(document).stem,
                            path=str(path),
                            page=page.page_number,
                            text=piece,
                        )
                    )
        return chunks

    def _metadata_stale(self) -> bool:
        manifest = self._read_manifest(self.metadata_manifest_path)
        return manifest.get("signature") != self._signature()

    def _agent_stale(self, agent_id: str) -> bool:
        manifest = self._read_manifest(self._agent_manifest_path(agent_id))
        return manifest.get("signature") != self._agent_signature(agent_id)

    def _signature(self) -> list[dict[str, Any]]:
        if not self.llm_dir.exists():
            return []
        return [self._file_signature(path) for path in sorted(self.llm_dir.rglob("*.pdf"), key=lambda p: str(p).lower())]

    def _agent_signature(self, agent_id: str) -> list[dict[str, Any]]:
        agents = {agent.id: agent for agent in scan_agents(self.llm_dir)}
        agent = agents.get(agent_id)
        if not agent:
            return []
        return [self._file_signature(Path(agent.folder) / document) for document in agent.documents]

    def _file_signature(self, path: Path) -> dict[str, Any]:
        try:
            stat = path.stat()
            relative = str(path.relative_to(self.llm_dir))
            return {"path": relative, "size": stat.st_size, "mtime_ns": stat.st_mtime_ns}
        except OSError:
            return {"path": str(path), "size": 0, "mtime_ns": 0}

    def _read_manifest(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _agent_index_path(self, agent_id: str) -> Path:
        return self.agent_index_dir / f"{agent_id}.pkl"

    def _agent_manifest_path(self, agent_id: str) -> Path:
        return self.agent_index_dir / f"{agent_id}.json"

    def _built_agent_ids(self, agents: list[LLMAgentInfo]) -> list[str]:
        built: list[str] = []
        for agent in agents:
            if self._agent_index_path(agent.id).exists() and not self._agent_stale(agent.id):
                built.append(agent.id)
        return built
