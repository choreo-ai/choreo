"""RunContext: per-run state that lives inside the graph state.

Design (ADR 0006): budget ledger and event cursor must survive LangGraph
checkpoint/resume. Do not store these only in thread-locals or closures.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Any


class RunContext(ABC):
    """Mutable per-run context shared by middleware, guardrails, and nodes.

    Intended to be stored on the LangGraph state under a dedicated channel
    (e.g. ``run_context``) with a reducer that merges ledger and cursor updates
    safely under parallel node execution.

    Minimum contents (ADR 0006):

    - **Budget ledger** -- consumed amounts vs caps (see
      ``choreo.reliability.budget``).
    - **Event cursor** -- monotonic sequence for the typed event stream.

    Implementations must be serializable enough for the configured checkpointer
    (JSON-friendly primitives or documented codec).
    """

    @property
    @abstractmethod
    def run_id(self) -> str:
        """Stable id for this run/thread attempt (for events and logs)."""
        ...

    @property
    @abstractmethod
    def event_cursor(self) -> int:
        """Monotonic counter of events emitted so far in this run.

        Subscribers use this for ordering and deduplication after resume.
        """
        ...

    @abstractmethod
    def next_event_seq(self) -> int:
        """Advance the event cursor and return the new sequence number.

        Returns:
            The sequence assigned to the event about to be emitted.
        """
        ...

    @abstractmethod
    def budget_ledger(self) -> dict[str, Any]:
        """Return a JSON-friendly snapshot of the budget ledger.

        The concrete shape matches ``BudgetSnapshot`` / ledger fields owned by
        ``choreo.reliability.budget``. Stored inside state so resume continues
        with the same consumption counts.
        """
        ...

    @abstractmethod
    def update_budget_ledger(self, patch: dict[str, Any]) -> None:
        """Merge a partial ledger update into this context.

        Args:
            patch: Dimension deltas or absolute fields as defined by Budget.
                Reducer semantics for graph state are implementation-defined
                but must be associative for concurrent patches.
        """
        ...

    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """Read an extension value (user or middleware scratch state)."""
        ...

    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """Write an extension value. Values should be checkpoint-safe."""
        ...

    @abstractmethod
    def to_state_dict(self) -> dict[str, Any]:
        """Serialize for graph state / checkpointer."""
        ...

    @classmethod
    @abstractmethod
    def from_state_dict(cls, data: dict[str, Any]) -> RunContext:
        """Deserialize from graph state."""
        ...


def _default_ledger(
    caps: dict[str, float] | None = None,
    consumed: dict[str, float] | None = None,
    labels: dict[str, str] | None = None,
) -> dict[str, Any]:
    return {
        "caps": dict(caps or {}),
        "consumed": dict(consumed or {}),
        "labels": dict(labels or {}),
    }


class InMemoryRunContext(RunContext):
    """Concrete ``RunContext`` with an in-process ledger and event cursor.

    JSON-friendly via ``to_state_dict`` / ``from_state_dict`` for LangGraph
    checkpointing (ADR 0006).
    """

    def __init__(
        self,
        *,
        run_id: str | None = None,
        event_cursor: int = 0,
        budget_ledger: dict[str, Any] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self._run_id = run_id or str(uuid.uuid4())
        self._event_cursor = int(event_cursor)
        ledger = budget_ledger or {}
        self._budget_ledger = _default_ledger(
            caps=ledger.get("caps"),
            consumed=ledger.get("consumed"),
            labels=ledger.get("labels"),
        )
        self._extra: dict[str, Any] = dict(extra or {})

    @property
    def run_id(self) -> str:
        return self._run_id

    @property
    def event_cursor(self) -> int:
        return self._event_cursor

    def next_event_seq(self) -> int:
        self._event_cursor += 1
        return self._event_cursor

    def budget_ledger(self) -> dict[str, Any]:
        return {
            "caps": dict(self._budget_ledger["caps"]),
            "consumed": dict(self._budget_ledger["consumed"]),
            "labels": dict(self._budget_ledger["labels"]),
        }

    def update_budget_ledger(self, patch: dict[str, Any]) -> None:
        if "caps" in patch and patch["caps"] is not None:
            self._budget_ledger["caps"] = dict(patch["caps"])
        if "consumed" in patch and patch["consumed"] is not None:
            self._budget_ledger["consumed"] = dict(patch["consumed"])
        if "labels" in patch and patch["labels"] is not None:
            self._budget_ledger["labels"] = dict(patch["labels"])
        # Support delta-style patches: {"delta": {"tokens": 10}}
        delta = patch.get("delta")
        if isinstance(delta, dict):
            consumed = self._budget_ledger["consumed"]
            for key, amount in delta.items():
                consumed[key] = float(consumed.get(key, 0.0)) + float(amount)

    def get(self, key: str, default: Any = None) -> Any:
        return self._extra.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._extra[key] = value

    def to_state_dict(self) -> dict[str, Any]:
        return {
            "run_id": self._run_id,
            "event_cursor": self._event_cursor,
            "budget_ledger": self.budget_ledger(),
            "extra": dict(self._extra),
        }

    @classmethod
    def from_state_dict(cls, data: dict[str, Any]) -> InMemoryRunContext:
        if not data:
            return cls()
        return cls(
            run_id=data.get("run_id"),
            event_cursor=int(data.get("event_cursor", 0)),
            budget_ledger=data.get("budget_ledger"),
            extra=data.get("extra"),
        )
