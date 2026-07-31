"""Core Choreo contracts: middleware, guardrails, run context, events.

Substrate types (Runnable, BaseTool, BaseChatModel) are adopted from
``langchain-core``; this package owns the opt-in value-add shapes only.
"""

from choreo.core.context import RunContext
from choreo.core.events import (
    Event,
    GuardrailTripped,
    LLMCalled,
    RunFinished,
    RunStarted,
    StepFinished,
    Subscriber,
    ToolCalled,
)
from choreo.core.guardrail import Guardrail, GuardrailResult, GuardrailStage
from choreo.core.middleware import Middleware, MiddlewareStack, call_next

__all__ = [
    "Event",
    "Guardrail",
    "GuardrailResult",
    "GuardrailStage",
    "GuardrailTripped",
    "LLMCalled",
    "Middleware",
    "MiddlewareStack",
    "RunContext",
    "RunFinished",
    "RunStarted",
    "StepFinished",
    "Subscriber",
    "ToolCalled",
    "call_next",
]
