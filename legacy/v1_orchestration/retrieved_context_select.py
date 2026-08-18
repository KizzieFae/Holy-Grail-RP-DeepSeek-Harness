"""Phase 2: deterministic authored-index retrieval for RetrievedContextBundle.

No transcript ingestion, vectors, or graph. Runtime bundle build runs only from
``prompt_retrieval_assembly.build_character_retrieved_context_bundle`` (invoked by ``app_turn_prompting``).

Mechanical split (Issue #166): leaf modules + thin façade; caps live here for monkeypatch compatibility.
"""

from __future__ import annotations

from typing import Literal

MAX_RETRIEVED_ITEMS = 8
MAX_RETRIEVED_CHARS = 8000

# Phase 3.1: per-source_kind subcaps (trim: priority DESC, source_ref ASC, keep head).
MAX_KIND_LORE_ITEMS = 1
MAX_KIND_LORE_CHARS = 600
MAX_KIND_SCENE_TEMPLATE_ITEMS = 3
MAX_KIND_SETUP_NOTE_ITEMS = 2
MAX_KIND_CHARACTER_CARD_ITEMS = 4

NonAuthoritative = Literal[True]

from authored_retrieval_index import (  # noqa: E402
    AuthoredIndexChunk,
    AuthoredRetrievalIndex,
    load_authored_retrieval_index,
)
from retrieved_context_ops import get_index_path_from_env, log_retrieval_if_active  # noqa: E402
from retrieved_episodic_merge import (  # noqa: E402
    episodic_compiled_to_retrieved_item,
    filter_episodic_items_by_structured_prompt_overlap,
    merge_retrieved_context_with_episodic,
    structured_prompt_id_sets_for_episodic_suppression,
)
from retrieved_selection_authored import (  # noqa: E402
    _dedupe_items,
    select_authored_retrieved_items_pre_global_cap,
    select_retrieved_context_bundle,
)
