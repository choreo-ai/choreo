"""Recovery policies: what to do when a step fails or a guardrail trips.

Design (ADR 0004): recovery is owned value-add. Policies map failures to
retry-with-feedback, replan, fallback, escalate, or abort -- without requiring
users to subclass agents.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from choreo.core.context import RunContext


class RecoveryAction(str, Enum):
    """Closed set of recovery actions the core loop understands."""

    RETRY_WITH_FEEDBACK = "retry_with_feedback"
    """Retry the same step, injecting feedback (error text / guardrail reason)."""

    REPLAN = "replan"
    """Ask the planner/agent to choose a different approach or tool sequence."""

    FALLBACK = "fallback"
    """Switch to a configured fallback node, model, or tool."""

    ESCALATE = "escalate"
    """Surface to a human or outer supervisor (HITL / parent graph)."""

    ABORT = "abort"
    """Stop the run with a controlled failure."""


@dataclass(frozen=True)
class RecoveryContext:
    """Facts available to a policy when deciding recovery.

    Attributes:
        error: Exception or error string from the failed attempt.
        attempt: 1-based attempt count for this step.
        node_id: Node/agent where the failure occurred.
        guardrail_name: Set when failure originated from a guardrail trip.
        stage: Guardrail stage or step phase label, if any.
        last_input: Input that failed (for feedback / replan prompts).
        last_output: Partial output, if any.
        metadata: Extra detail (tool name, model id, status codes).
    """

    error: str
    attempt: int
    node_id: str | None = None
    guardrail_name: str | None = None
    stage: str | None = None
    last_input: Any = None
    last_output: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RecoveryDecision:
    """Policy output interpreted by the agent/engine loop.

    Attributes:
        action: Which recovery action to take.
        feedback: Message injected into the next attempt (retry/replan).
        fallback_target: Name or handle of fallback node/model when
            ``action is FALLBACK``.
        reason: Human-readable explanation for logs and events.
        metadata: Open bag for subscribers and evals.
        max_attempts: Optional cap hint for the loop (policy may still be
            re-consulted each failure).
    """

    action: RecoveryAction
    feedback: str | None = None
    fallback_target: str | None = None
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    max_attempts: int | None = None


class RecoveryPolicy(ABC):
    """Decides how to recover from a failed step or tripped guardrail.

    The run loop calls ``adecide`` after a failure; it does not execute the
    action itself beyond what the engine supports (e.g. escalate may map to
    LangGraph ``interrupt``).
    """

    name: str
    """Stable policy name for config and events."""

    @abstractmethod
    async def adecide(
        self,
        recovery_context: RecoveryContext,
        *,
        context: RunContext | None = None,
    ) -> RecoveryDecision:
        """Return the next recovery action.

        Args:
            recovery_context: Failure facts for this attempt.
            context: Optional run context (budgets, counters, scratch).

        Returns:
            A ``RecoveryDecision`` the loop must honor.
        """
        ...
