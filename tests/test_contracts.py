"""Smoke tests: value-add contracts import and expose expected symbols."""

from enum import Enum

import choreo.core as core
import choreo.reliability as reliability
from choreo.core.events import ChoreoEvent, EventEmitter
from choreo.core.guardrail import GuardrailResult, GuardrailStage
from choreo.core.middleware import Middleware, NextCall
from choreo.reliability.budget import BudgetDecision, BudgetDimensions, BudgetExhausted
from choreo.reliability.recovery import RecoveryAction, RecoveryContext, RecoveryDecision


def test_core_contract_exports():
    for name in (
        "Middleware",
        "MiddlewareStack",
        "Guardrail",
        "GuardrailResult",
        "GuardrailStage",
        "RunContext",
        "InMemoryRunContext",
        "Event",
        "EventEmitter",
        "SimpleEventEmitter",
        "Subscriber",
        "RunStarted",
        "RunFinished",
        "LLMCalled",
        "ToolCalled",
        "GuardrailTripped",
        "StepFinished",
        "BudgetMiddleware",
        "TraceMiddleware",
        "OnionMiddlewareStack",
    ):
        assert hasattr(core, name), name


def test_reliability_contract_exports():
    for name in (
        "Budget",
        "BudgetDecision",
        "BudgetDimensions",
        "BudgetExhausted",
        "BudgetSnapshot",
        "InMemoryBudget",
        "RecoveryAction",
        "RecoveryContext",
        "RecoveryDecision",
        "RecoveryPolicy",
    ):
        assert hasattr(reliability, name), name


def test_recovery_actions_are_closed_set():
    assert issubclass(RecoveryAction, Enum)
    assert {a.value for a in RecoveryAction} == {
        "retry_with_feedback",
        "replan",
        "fallback",
        "escalate",
        "abort",
    }


def test_guardrail_stages():
    assert GuardrailStage.PRE.value == "pre"
    assert GuardrailStage.POST.value == "post"
    result = GuardrailResult(allowed=True, stage=GuardrailStage.PRE, reason="ok")
    assert result.allowed and result.rewritten_value is None


def test_budget_dimensions_and_exhausted():
    assert BudgetDimensions.TOKENS.value == "tokens"
    decision = BudgetDecision(allowed=False, reason="cap", dimension="tokens")
    err = BudgetExhausted("done", decision=decision)
    assert err.decision is decision


def test_recovery_context_defaults():
    ctx = RecoveryContext(error="boom", attempt=1)
    assert ctx.node_id is None
    decision = RecoveryDecision(action=RecoveryAction.ABORT, reason="stop")
    assert decision.action is RecoveryAction.ABORT


def test_middleware_and_emitter_are_abstract():
    assert hasattr(Middleware, "ainvoke")
    assert hasattr(EventEmitter, "emit")
    assert NextCall is not None
    # ChoreoEvent union exists for type checkers / docs
    assert ChoreoEvent is not None
