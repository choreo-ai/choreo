"""Core ChoreoAI contracts: middleware, guardrails, run context, events.

Substrate types (Runnable, BaseTool, BaseChatModel) are adopted from
``langchain-core``; this package owns the opt-in value-add shapes only.
"""

from choreo.core.context import InMemoryRunContext, RunContext
from choreo.core.events import (
    Event,
    EventEmitter,
    GuardrailTripped,
    ListSubscriber,
    LLMCalled,
    RunFinished,
    RunStarted,
    SimpleEventEmitter,
    StepFinished,
    Subscriber,
    ToolCalled,
)
from choreo.core.guardrail import Guardrail, GuardrailResult, GuardrailStage
from choreo.core.middleware import Middleware, MiddlewareStack, call_next
from choreo.core.middleware_impl import (
    BudgetMiddleware,
    OnionMiddlewareStack,
    TraceMiddleware,
)

__all__ = [
    "BudgetMiddleware",
    "Event",
    "EventEmitter",
    "Guardrail",
    "GuardrailResult",
    "GuardrailStage",
    "GuardrailTripped",
    "InMemoryRunContext",
    "LLMCalled",
    "ListSubscriber",
    "Middleware",
    "MiddlewareStack",
    "OnionMiddlewareStack",
    "RunContext",
    "RunFinished",
    "RunStarted",
    "SimpleEventEmitter",
    "StepFinished",
    "Subscriber",
    "ToolCalled",
    "TraceMiddleware",
    "call_next",
]
