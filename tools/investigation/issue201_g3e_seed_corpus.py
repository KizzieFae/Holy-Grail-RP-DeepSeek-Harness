#!/usr/bin/env python3
"""Issue #201 G3-E runtime corpus seeding with manifest recovery + semantic index rebuild."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_V2 = _ROOT / "v2"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain_api.story_knowledge_contract import StoryKnowledgeRecord  # noqa: E402
from domain_api.story_knowledge_repository import StoryKnowledgeRepository  # noqa: E402
from domain_api.story_knowledge_service import StoryKnowledgeService  # noqa: E402
from domain_api.story_semantic_index import SemanticIndexBackend  # noqa: E402


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def seed_scope(
    *,
    data_dir: Path,
    memory_scope_id: str,
    records_path: Path,
    expected_count: int | None,
    expected_sha256: str | None,
    rewrite_memory_scope_id: str | None = None,
) -> dict[str, object]:
    store_root = data_dir / "sessions" / "_story_knowledge"
    store_root.mkdir(parents=True, exist_ok=True)
    repo = StoryKnowledgeRepository(store_root)
    target = repo.records_path(memory_scope_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    if rewrite_memory_scope_id:
        with target.open("w", encoding="utf-8") as handle:
            for line in records_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                payload["memory_scope_id"] = rewrite_memory_scope_id
                handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    else:
        shutil.copy2(records_path, target)
    source_sha = _sha256_file(records_path)
    recovered = repo.recover_truncated_tail(memory_scope_id)
    service = StoryKnowledgeService(repo)
    indexed = service.rebuild_semantic_index(memory_scope_id)
    index = SemanticIndexBackend(index_path=repo.semantic_index_path(memory_scope_id))
    manifest = repo.load_manifest(memory_scope_id)
    ok_count = expected_count is None or recovered == expected_count
    ok_sha = expected_sha256 is None or source_sha == expected_sha256
    return {
        "schema": "issue201_g3e_corpus_seed_v1",
        "memory_scope_id": memory_scope_id,
        "data_dir": str(data_dir),
        "records_path": str(records_path),
        "records_sha256": source_sha,
        "record_count": recovered,
        "manifest_record_count": manifest.record_count,
        "semantic_index_rebuilt": indexed,
        "semantic_index_available": index.available,
        "expected_count_match": ok_count,
        "expected_sha256_match": ok_sha,
        "seed_ok": ok_count and ok_sha and index.available and recovered > 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed G3-E corpus into runtime story-knowledge store")
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--memory-scope-id", required=True)
    parser.add_argument("--records", required=True)
    parser.add_argument("--expected-count", type=int, default=None)
    parser.add_argument("--expected-sha256", default=None)
    parser.add_argument("--rewrite-memory-scope-id", default=None)
    args = parser.parse_args()
    result = seed_scope(
        data_dir=Path(args.data_dir),
        memory_scope_id=args.memory_scope_id,
        records_path=Path(args.records),
        expected_count=args.expected_count,
        expected_sha256=args.expected_sha256,
        rewrite_memory_scope_id=args.rewrite_memory_scope_id,
    )
    print(json.dumps(result, indent=2))
    return 0 if result["seed_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
