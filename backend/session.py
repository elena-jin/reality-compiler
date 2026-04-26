"""Session manager for Reality Compiler.

Stores previous generated designs per session and supports iteration commands.
(Mubit sponsor requirement)
"""

from __future__ import annotations

import uuid
from collections import OrderedDict
from typing import Optional

from backend.schemas import GenerationResult, SessionHistory


class SessionManager:
    """In-memory session store with LRU eviction."""

    def __init__(self, max_sessions: int = 200) -> None:
        self._sessions: OrderedDict[str, SessionHistory] = OrderedDict()
        self._max_sessions = max_sessions

    def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = SessionHistory(session_id=session_id)
        self._evict()
        return session_id

    def get_or_create(self, session_id: Optional[str]) -> SessionHistory:
        if session_id and session_id in self._sessions:
            self._sessions.move_to_end(session_id)
            return self._sessions[session_id]
        new_id = session_id or str(uuid.uuid4())
        history = SessionHistory(session_id=new_id)
        self._sessions[new_id] = history
        self._evict()
        return history

    def add_design(self, session_id: str, result: GenerationResult) -> None:
        history = self.get_or_create(session_id)
        history.designs.append(result)

    def get_latest_design(self, session_id: str) -> Optional[GenerationResult]:
        history = self._sessions.get(session_id)
        if history and history.designs:
            return history.designs[-1]
        return None

    def get_design_by_id(self, session_id: str, design_id: str) -> Optional[GenerationResult]:
        history = self._sessions.get(session_id)
        if not history:
            return None
        for design in history.designs:
            if design.id == design_id:
                return design
        return None

    def get_history(self, session_id: str) -> Optional[SessionHistory]:
        return self._sessions.get(session_id)

    def _evict(self) -> None:
        while len(self._sessions) > self._max_sessions:
            self._sessions.popitem(last=False)
