"""RunContext: per-run state that lives inside the graph state.

Design (ADR 0006): budget ledger and event cursor must survive LangGraph
checkpoint/resume. Do not store these only in thread-locals or closures.
"""

from __future__ import annotations

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
