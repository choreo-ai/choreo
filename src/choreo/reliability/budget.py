"""Budget: caps and ledger for production runs.

Design (ADR 0004, ADR 0006): budgets are opt-in value-add. The ledger lives in
``RunContext`` so consumption survives LangGraph checkpoint/resume.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from choreo.core.context import RunContext


class BudgetDimensions(str, Enum):
    """Billable or limitable dimensions a budget may track."""

    TOKENS = "tokens"
    COST_USD = "cost_usd"
    STEPS = "steps"
    WALL_TIME_MS = "wall_time_ms"
    TOOL_CALLS = "tool_calls"
    LLM_CALLS = "llm_calls"


@dataclass(frozen=True)
class BudgetSnapshot:
    """Point-in-time view of caps and consumption.

    Attributes:
        caps: Max allowed per dimension (missing key = unlimited).
        consumed: Amount used per dimension.
        labels: Optional tags (tenant, feature flag) for multi-tenant ledgers.
    """

    caps: dict[str, float] = field(default_factory=dict)
    consumed: dict[str, float] = field(default_factory=dict)
    labels: dict[str, str] = field(default_factory=dict)

    def remaining(self, dimension: str) -> float | None:
        """Return remaining capacity for ``dimension``, or None if uncapped."""
        if dimension not in self.caps:
            return None
        return max(0.0, self.caps[dimension] - self.consumed.get(dimension, 0.0))


@dataclass(frozen=True)
class BudgetDecision:
    """Result of checking whether an operation may proceed.

    Attributes:
        allowed: False if any relevant cap would be exceeded.
        reason: Explanation when denied.
        dimension: Which dimension blocked, if any.
        snapshot: Ledger view after the hypothetical check (not yet committed
            unless ``consume`` was used).
    """

    allowed: bool
    reason: str = ""
    dimension: str | None = None
    snapshot: BudgetSnapshot | None = None


class BudgetExhausted(Exception):
    """Raised when a consume/check fails because a cap is hit.

    Recovery policies may map this to abort, escalate, or replan.
    """

    def __init__(self, message: str, *, decision: BudgetDecision | None = None) -> None:
        super().__init__(message)
        self.decision = decision


class Budget(ABC):
    """Tracks and enforces resource caps for a run.

    Typical use inside budget middleware:

    1. ``check`` estimated cost before an LLM/tool call.
    2. Perform the call if allowed.
    3. ``consume`` actual usage (tokens, duration, etc.).
    4. Persist ledger via ``RunContext.update_budget_ledger``.

    Implementations should treat the ``RunContext`` ledger as source of truth
    when a context is provided, so resume continues from checkpointed totals.
    """

    name: str
    """Stable name for config and events."""

    @abstractmethod
    def snapshot(self, *, context: RunContext | None = None) -> BudgetSnapshot:
        """Return current caps and consumption."""
        ...

    @abstractmethod
    def check(
        self,
        amounts: dict[str, float],
        *,
        context: RunContext | None = None,
    ) -> BudgetDecision:
        """Return whether ``amounts`` fit under remaining caps without mutating.

        Args:
            amounts: Proposed consumption by dimension key (see
                ``BudgetDimensions`` values).
            context: Optional run context whose ledger is authoritative.
        """
        ...

    @abstractmethod
    def consume(
        self,
        amounts: dict[str, float],
        *,
        context: RunContext | None = None,
        strict: bool = True,
    ) -> BudgetDecision:
        """Apply ``amounts`` to the ledger.

        Args:
            amounts: Actual consumption by dimension.
            context: If provided, update ``context`` ledger for checkpointing.
            strict: When True, raise ``BudgetExhausted`` if the check fails;
                when False, return a denied ``BudgetDecision`` without raising.

        Returns:
            Decision reflecting post-consume snapshot when allowed.
        """
        ...

    @abstractmethod
    def is_exhausted(
        self,
        *,
        context: RunContext | None = None,
        dimensions: list[str] | None = None,
    ) -> bool:
        """Return True if any (or named) dimension has no remaining capacity."""
        ...
