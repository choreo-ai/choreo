"""Offline tests for InMemoryBudget and Budget/Trace middleware."""

from __future__ import annotations

import pytest

from choreoai.core import (
    BudgetMiddleware,
    InMemoryRunContext,
    ListSubscriber,
    OnionMiddlewareStack,
    SimpleEventEmitter,
    TraceMiddleware,
)
from choreoai.reliability import BudgetExhausted, BudgetDimensions, InMemoryBudget


def test_in_memory_budget_check_and_consume():
    budget = InMemoryBudget(caps={"tokens": 10, "steps": 2})
    ok = budget.check({"tokens": 3})
    assert ok.allowed
    decision = budget.consume({"tokens": 3})
    assert decision.allowed
    assert budget.snapshot().consumed["tokens"] == 3.0
    denied = budget.check({"tokens": 100})
    assert not denied.allowed
    assert denied.dimension == "tokens"


def test_consume_strict_raises():
    budget = InMemoryBudget(caps={"steps": 1})
    budget.consume({"steps": 1})
    with pytest.raises(BudgetExhausted):
        budget.consume({"steps": 1}, strict=True)
    soft = budget.consume({"steps": 1}, strict=False)
    assert soft.allowed is False


def test_budget_uses_run_context_ledger():
    budget = InMemoryBudget(caps={"steps": 5})
    ctx = InMemoryRunContext(
        budget_ledger={"caps": {"steps": 5}, "consumed": {}, "labels": {}}
    )
    budget.consume({"steps": 2}, context=ctx)
    assert ctx.budget_ledger()["consumed"]["steps"] == 2.0
    assert budget.snapshot(context=ctx).remaining("steps") == 3.0


@pytest.mark.asyncio
async def test_budget_middleware_enforces_cap():
    budget = InMemoryBudget(caps={"steps": 1})
    ctx = InMemoryRunContext(
        budget_ledger={"caps": {"steps": 1}, "consumed": {}, "labels": {}}
    )
    calls: list[int] = []

    async def node(value: int) -> int:
        calls.append(value)
        return value + 1

    stack = OnionMiddlewareStack(
        [BudgetMiddleware(budget, amounts={BudgetDimensions.STEPS.value: 1})],
        node=node,
    )
    assert await stack.ainvoke(1, context=ctx) == 2
    with pytest.raises(BudgetExhausted):
        await stack.ainvoke(2, context=ctx)
    assert calls == [1]


@pytest.mark.asyncio
async def test_trace_middleware_emits_step_finished():
    emitter = SimpleEventEmitter()
    sub = ListSubscriber()
    emitter.subscribe(sub)
    ctx = InMemoryRunContext(run_id="run-1")

    async def node(value: str) -> str:
        return value.upper()

    stack = OnionMiddlewareStack(
        [TraceMiddleware(emitter=emitter, node_id="upper")],
        node=node,
    )
    assert await stack.ainvoke("hi", context=ctx) == "HI"
    assert len(sub.events) == 1
    assert sub.events[0].type == "step_finished"
    assert sub.events[0].success is True
    assert sub.events[0].step_name == "upper"


@pytest.mark.asyncio
async def test_trace_and_budget_onion_order():
    budget = InMemoryBudget(caps={"steps": 2})
    emitter = SimpleEventEmitter()
    sub = ListSubscriber()
    emitter.subscribe(sub)
    ctx = InMemoryRunContext(
        budget_ledger={"caps": {"steps": 2}, "consumed": {}, "labels": {}}
    )

    async def node(value: str) -> str:
        return f"ok:{value}"

    stack = OnionMiddlewareStack(
        [
            TraceMiddleware(emitter=emitter, node_id="n"),
            BudgetMiddleware(budget),
        ],
        node=node,
    )
    assert await stack.ainvoke("a", context=ctx) == "ok:a"
    assert budget.snapshot(context=ctx).consumed["steps"] == 1.0
    assert any(e.type == "step_finished" for e in sub.events)
