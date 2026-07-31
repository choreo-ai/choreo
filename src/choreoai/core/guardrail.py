"""Guardrails: validation/safety checks that can trip recovery.

Design (ADR 0003, ADR 0004): guardrails are opt-in value-add. Core owns *when*
checks run (pre-input / post-output) and how a trip feeds recovery; users own
the check logic via this interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from choreoai.core.context import RunContext


class GuardrailStage(str, Enum):
    """When a guardrail is evaluated relative to the wrapped node."""

    PRE = "pre"
    """Before the node runs; typically validates or rewrites input."""

    POST = "post"
    """After the node runs; typically validates output or side effects."""


@dataclass(frozen=True)
class GuardrailResult:
    """Outcome of a single guardrail evaluation.

    Attributes:
        allowed: If False, the check tripped; recovery should consult policy.
        stage: Stage at which the check ran.
        reason: Human-readable explanation (safe for logs/events).
        metadata: Optional structured detail for subscribers/evals.
        rewritten_value: If set, replace input (PRE) or output (POST) with this
            value when ``allowed`` is True. ``None`` means pass through.
    """

    allowed: bool
    stage: GuardrailStage
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    rewritten_value: Any | None = None


class Guardrail(ABC):
    """A single validation or safety check.

    Guardrails are pure-ish async callables over a value plus ``RunContext``.
    They do not invoke the node themselves; middleware or the agent loop calls
    them at the appropriate stage and interprets ``GuardrailResult``.

    On trip (``allowed is False``), core emits ``GuardrailTripped`` and consults
    the active ``RecoveryPolicy`` (see ``choreoai.reliability.recovery``).
    """

    name: str
    """Stable identifier for events and config."""

    stage: GuardrailStage
    """Default stage this guardrail is registered for."""

    @abstractmethod
    async def aevaluate(
        self,
        value: Any,
        *,
        stage: GuardrailStage,
        context: RunContext | None = None,
    ) -> GuardrailResult:
        """Evaluate ``value`` at ``stage``.

        Args:
            value: Candidate input (PRE) or output (POST).
            stage: Stage being evaluated; may differ from ``self.stage`` if the
                same class is reused.
            context: Optional per-run context for budget- or history-aware rules.

        Returns:
            ``GuardrailResult`` indicating allow/deny and optional rewrite.
        """
        ...
