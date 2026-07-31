"""Offline tests for LangGraph engine compile_plan (no Anthropic)."""

from __future__ import annotations

import pytest
from langchain_core.runnables import RunnableLambda

from choreoai.core import (
    BudgetMiddleware,
    InMemoryRunContext,
    ListSubscriber,
    SimpleEventEmitter,
    TraceMiddleware,
)
from choreoai.reliability import BudgetExhausted, InMemoryBudget

langgraph = pytest.importorskip("langgraph")

from choreoai.engine.langgraph_engine import arun_plan, compile_plan  # noqa: E402


@pytest.mark.asyncio
async def test_compile_sequence_plan():
    a = RunnableLambda(lambda x: f"{x}-a" if not isinstance(x, dict) else f"{x.get('value')}-a")
    b = RunnableLambda(lambda x: f"{x}-b" if not isinstance(x, dict) else f"{x.get('value')}-b")

    # Nodes receive packed dict from wrap_node_with_middleware
    async def node_a(inp):
        v = inp["value"] if isinstance(inp, dict) else inp
        return f"{v}-a"

    async def node_b(inp):
        v = inp["value"] if isinstance(inp, dict) else inp
        return f"{v}-b"

    from langchain_core.runnables import RunnableLambda as RL

    compiled = compile_plan(
        [
            ("a", RL(func=lambda x: x, afunc=node_a)),
            ("b", RL(func=lambda x: x, afunc=node_b)),
        ]
    )
    result = await arun_plan(compiled, "x", thread_id="t-seq")
    assert result["value"] == "x-a-b"
    assert "run_context" in result


@pytest.mark.asyncio
async def test_engine_budget_middleware_raises():
    async def node(inp):
        v = inp["value"] if isinstance(inp, dict) else inp
        return f"ok:{v}"

    from langchain_core.runnables import RunnableLambda as RL

    budget = InMemoryBudget(caps={"steps": 1})
    mw = [BudgetMiddleware(budget, amounts={"steps": 1})]
    compiled = compile_plan(
        [
            ("n1", RL(func=lambda x: x, afunc=node)),
            ("n2", RL(func=lambda x: x, afunc=node)),
        ],
        middleware=mw,
    )
    ctx = InMemoryRunContext(
        budget_ledger={"caps": {"steps": 1}, "consumed": {}, "labels": {}}
    )
    with pytest.raises(BudgetExhausted):
        await arun_plan(compiled, "x", run_context=ctx, thread_id="t-budget")


@pytest.mark.asyncio
async def test_engine_trace_middleware_emits():
    async def node(inp):
        v = inp["value"] if isinstance(inp, dict) else inp
        return v.upper()

    from langchain_core.runnables import RunnableLambda as RL

    emitter = SimpleEventEmitter()
    sub = ListSubscriber()
    emitter.subscribe(sub)
    compiled = compile_plan(
        [("upper", RL(func=lambda x: x, afunc=node))],
        middleware=[TraceMiddleware(emitter=emitter, node_id="upper")],
    )
    result = await arun_plan(compiled, "hi", thread_id="t-trace")
    assert result["value"] == "HI"
    assert any(e.type == "step_finished" for e in sub.events)
