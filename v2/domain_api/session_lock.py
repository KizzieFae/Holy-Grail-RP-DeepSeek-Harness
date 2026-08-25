"""Per-session synchronization for Domain Host session mutation (#39)."""

from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import Iterator


class SessionLockRegistry:
    """One re-entrant lock per hg_scene_id for safe concurrent HTTP handlers."""

    def __init__(self) -> None:
        self._guard = threading.Lock()
        self._locks: dict[str, threading.RLock] = {}

    def _lock_for(self, hg_scene_id: str) -> threading.RLock:
        with self._guard:
            lock = self._locks.get(hg_scene_id)
            if lock is None:
                lock = threading.RLock()
                self._locks[hg_scene_id] = lock
            return lock

    @contextmanager
    def session_scope(self, hg_scene_id: str) -> Iterator[None]:
        lock = self._lock_for(hg_scene_id)
        lock.acquire()
        try:
            yield
        finally:
            lock.release()
