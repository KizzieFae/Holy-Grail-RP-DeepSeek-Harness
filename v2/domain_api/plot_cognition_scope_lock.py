"""Scope-keyed synchronization for Plot Cognition Overlay persistence (#59)."""

from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import Iterator


class PlotCognitionScopeLockRegistry:
    """One re-entrant lock per plot_cognition_scope_id."""

    def __init__(self) -> None:
        self._guard = threading.Lock()
        self._locks: dict[str, threading.RLock] = {}

    def _lock_for(self, plot_cognition_scope_id: str) -> threading.RLock:
        with self._guard:
            lock = self._locks.get(plot_cognition_scope_id)
            if lock is None:
                lock = threading.RLock()
                self._locks[plot_cognition_scope_id] = lock
            return lock

    @contextmanager
    def scope_lock(self, plot_cognition_scope_id: str) -> Iterator[None]:
        lock = self._lock_for(plot_cognition_scope_id)
        lock.acquire()
        try:
            yield
        finally:
            lock.release()
