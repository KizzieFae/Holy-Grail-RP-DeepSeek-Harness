"""Derived semantic index for story knowledge (#50)."""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

EMBEDDING_PROVIDER_VERSION = "tfidf_v1"
TEST_EMBEDDING_PROVIDER_VERSION = "deterministic_hash_v1"


def _tokenize(text: str) -> list[str]:
    return [token for token in re.findall(r"[a-z0-9']+", text.lower()) if token]


class EmbeddingProvider(Protocol):
    provider_id: str

    def embed(self, text: str) -> list[float]: ...


class DeterministicHashEmbeddingProvider:
    """Test-friendly deterministic embedding provider."""

    provider_id = TEST_EMBEDDING_PROVIDER_VERSION
    dimensions = 64

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in _tokenize(text):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for index in range(self.dimensions):
                vector[index] += digest[index % len(digest)] / 255.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


class TfidfEmbeddingProvider:
    """Lightweight local TF-IDF embedding — no external dependencies."""

    provider_id = EMBEDDING_PROVIDER_VERSION
    dimensions = 256

    def __init__(self) -> None:
        self._vocabulary: dict[str, int] = {}

    def _vectorize(self, text: str) -> list[float]:
        counts: dict[str, int] = {}
        for token in _tokenize(text):
            counts[token] = counts.get(token, 0) + 1
        if not counts:
            return [0.0] * self.dimensions
        vector = [0.0] * self.dimensions
        for token, count in counts.items():
            index = self._vocabulary.setdefault(token, len(self._vocabulary) % self.dimensions)
            vector[index] += float(count)
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

    def embed(self, text: str) -> list[float]:
        return self._vectorize(text)


def default_embedding_provider(*, test_mode: bool = False) -> EmbeddingProvider:
    if test_mode:
        return DeterministicHashEmbeddingProvider()
    return TfidfEmbeddingProvider()


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left)) or 1.0
    right_norm = math.sqrt(sum(b * b for b in right)) or 1.0
    return dot / (left_norm * right_norm)


@dataclass
class SemanticIndexState:
    embedding_provider: str = EMBEDDING_PROVIDER_VERSION
    vectors: dict[str, list[float]] = field(default_factory=dict)
    content_hashes: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "embedding_provider": self.embedding_provider,
            "vectors": self.vectors,
            "content_hashes": self.content_hashes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SemanticIndexState:
        return cls(
            embedding_provider=str(data.get("embedding_provider", EMBEDDING_PROVIDER_VERSION)),
            vectors={str(k): list(v) for k, v in dict(data.get("vectors") or {}).items()},
            content_hashes={str(k): str(v) for k, v in dict(data.get("content_hashes") or {}).items()},
        )


class SemanticIndexBackend:
    def __init__(
        self,
        *,
        index_path: Path,
        embedding_provider: EmbeddingProvider | None = None,
        test_mode: bool = False,
    ) -> None:
        self.index_path = index_path
        self.embedding_provider = embedding_provider or default_embedding_provider(test_mode=test_mode)
        self.state = self._load()

    def _load(self) -> SemanticIndexState:
        if not self.index_path.exists():
            return SemanticIndexState(embedding_provider=self.embedding_provider.provider_id)
        data = json.loads(self.index_path.read_text(encoding="utf-8"))
        state = SemanticIndexState.from_dict(data)
        if state.embedding_provider != self.embedding_provider.provider_id:
            return SemanticIndexState(embedding_provider=self.embedding_provider.provider_id)
        return state

    def save(self) -> None:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.index_path.write_text(
            json.dumps(self.state.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def upsert(self, record_id: str, *, text: str, content_hash: str) -> None:
        self.state.vectors[record_id] = self.embedding_provider.embed(text)
        self.state.content_hashes[record_id] = content_hash
        self.save()

    def remove(self, record_id: str) -> None:
        self.state.vectors.pop(record_id, None)
        self.state.content_hashes.pop(record_id, None)
        self.save()

    def is_stale(self, record_id: str, content_hash: str) -> bool:
        return self.state.content_hashes.get(record_id) != content_hash

    def rank(
        self,
        query_text: str,
        candidate_ids: list[str],
        *,
        limit: int,
    ) -> list[str]:
        if not candidate_ids:
            return []
        query_vector = self.embedding_provider.embed(query_text)
        scored: list[tuple[float, str]] = []
        for record_id in candidate_ids:
            vector = self.state.vectors.get(record_id)
            if vector is None:
                continue
            scored.append((cosine_similarity(query_vector, vector), record_id))
        scored.sort(key=lambda item: (-item[0], item[1]))
        return [record_id for _score, record_id in scored[: max(1, limit)]]

    def rebuild(self, records: list[tuple[str, str, str]]) -> None:
        """Rebuild from (record_id, embedding_text, content_hash) tuples."""
        self.state = SemanticIndexState(embedding_provider=self.embedding_provider.provider_id)
        for record_id, text, content_hash in records:
            self.state.vectors[record_id] = self.embedding_provider.embed(text)
            self.state.content_hashes[record_id] = content_hash
        self.save()

    @property
    def available(self) -> bool:
        return bool(self.state.vectors)
