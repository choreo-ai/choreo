"""Typed event stream: public observability contract.

Design (ADR 0007): tracing, metrics, and evals are subscribers. Core emits
typed events; engines may bridge LangGraph streams into this model, but the
public shapes are owned by ChoreoAI.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal, Union


@dataclass(frozen=True, kw_only=True)
class Event:
    """Base fields shared by every ChoreoAI event.

    Attributes:
        type: Discriminator string matching the concrete event kind.
        run_id: Run this event belongs to (from ``RunContext.run_id``).
        seq: Monotonic sequence from ``RunContext.next_event_seq()``.
        ts: Event timestamp (UTC recommended).
        node_id: Optional node/agent name when applicable.
        metadata: Open bag for implementation and user tags.
    """

    type: str
    run_id: str
    seq: int
    ts: datetime
    node_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, kw_only=True)
class RunStarted(Event):
    """Emitted once when a run begins (before the first node)."""

    type: Literal["run_started"] = "run_started"
    input_summary: str | None = None


@dataclass(frozen=True, kw_only=True)
class RunFinished(Event):
    """Emitted once when a run completes, fails, or aborts."""

    type: Literal["run_finished"] = "run_finished"
    status: Literal["ok", "error", "aborted", "escalated"] = "ok"
    error: str | None = None
    output_summary: str | None = None


@dataclass(frozen=True, kw_only=True)
class LLMCalled(Event):
    """An LLM invocation completed (or failed after retries at the model layer)."""

    type: Literal["llm_called"] = "llm_called"
    model: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    duration_ms: float | None = None
    success: bool = True
    error: str | None = None


@dataclass(frozen=True, kw_only=True)
class ToolCalled(Event):
    """A tool invocation completed or failed."""

    type: Literal["tool_called"] = "tool_called"
    tool_name: str = ""
    duration_ms: float | None = None
    success: bool = True
    error: str | None = None


@dataclass(frozen=True, kw_only=True)
class GuardrailTripped(Event):
    """A guardrail denied or blocked a value."""

    type: Literal["guardrail_tripped"] = "guardrail_tripped"
    guardrail_name: str = ""
    stage: str = ""
    reason: str = ""


@dataclass(frozen=True, kw_only=True)
class StepFinished(Event):
    """A graph/combinator step (node execution) finished."""

    type: Literal["step_finished"] = "step_finished"
    step_name: str = ""
    success: bool = True
    duration_ms: float | None = None
    error: str | None = None


# Union of public event kinds (extensible later via additional dataclasses).
ChoreoEvent = Union[
    RunStarted,
    RunFinished,
    LLMCalled,
    ToolCalled,
    GuardrailTripped,
    StepFinished,
    Event,
]


class Subscriber(ABC):
    """Consumer of the typed event stream.

    Tracing, metrics, and eval harnesses implement this. Subscribers must be
    resilient: failures in ``on_event`` should not tear down the run (enforced
    by the emitter implementation).
    """

    name: str
    """Stable name for registration and logs."""

    @abstractmethod
    async def on_event(self, event: Event) -> None:
        """Handle one event.

        Args:
            event: Typed event instance (check ``event.type`` or ``isinstance``).
        """
        ...

    async def aclose(self) -> None:
        """Optional cleanup when the run ends or the subscriber is detached."""
        return None


class EventEmitter(ABC):
    """Produces events and fans them out to subscribers.

    Owned by the run loop / middleware; not typically implemented by users.
    """

    @abstractmethod
    def subscribe(self, subscriber: Subscriber) -> None:
        """Register a subscriber for subsequent events."""
        ...

    @abstractmethod
    def unsubscribe(self, subscriber: Subscriber) -> None:
        """Remove a previously registered subscriber."""
        ...

    @abstractmethod
    async def emit(self, event: Event) -> None:
        """Persist seq via ``RunContext`` if needed and notify subscribers."""
        ...


class SimpleEventEmitter(EventEmitter):
    """In-process fan-out emitter; subscriber failures never tear down the run."""

    def __init__(self) -> None:
        self._subscribers: list[Subscriber] = []

    def subscribe(self, subscriber: Subscriber) -> None:
        if subscriber not in self._subscribers:
            self._subscribers.append(subscriber)

    def unsubscribe(self, subscriber: Subscriber) -> None:
        self._subscribers = [s for s in self._subscribers if s is not subscriber]

    async def emit(self, event: Event) -> None:
        for subscriber in list(self._subscribers):
            try:
                await subscriber.on_event(event)
            except Exception:
                # Observability must not break the run (ADR 0007).
                continue

    @property
    def subscribers(self) -> tuple[Subscriber, ...]:
        return tuple(self._subscribers)


class ListSubscriber(Subscriber):
    """Collects events in a list (useful for tests and simple traces)."""

    name = "list"

    def __init__(self, name: str = "list") -> None:
        self.name = name
        self.events: list[Event] = []

    async def on_event(self, event: Event) -> None:
        self.events.append(event)
