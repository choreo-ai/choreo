"""Offline tests for sequence/parallel combinators."""

from __future__ import annotations

import pytest
from langchain_core.runnables import RunnableLambda

from choreoai.core import InMemoryRunContext
from choreoai.orchestrate import parallel, sequence


@pytest.mark.asyncio
async def test_sequence_threads_value():
    a = RunnableLambda(lambda x: f"{x}-a")
    b = RunnableLambda(lambda x: f"{x}-b")
    pipe = sequence(a, b, name="ab")
    out = await pipe.ainvoke("x")
    assert out == "x-a-b"


@pytest.mark.asyncio
async def test_sequence_threads_run_context():
    async def step1(inp):
        value = inp["value"] if isinstance(inp, dict) else inp
        ctx = inp.get("run_context") if isinstance(inp, dict) else None
        if hasattr(ctx, "set"):
            ctx.set("seen", "step1")
        return {"value": f"{value}-1", "run_context": ctx}

    async def step2(inp):
        value = inp["value"] if isinstance(inp, dict) else inp
        ctx = inp.get("run_context") if isinstance(inp, dict) else None
        assert ctx is not None
        assert ctx.get("seen") == "step1"
        return {"value": f"{value}-2", "run_context": ctx}

    pipe = sequence(
        RunnableLambda(func=lambda x: x, afunc=step1),
        RunnableLambda(func=lambda x: x, afunc=step2),
    )
    ctx = InMemoryRunContext(run_id="r1")
    out = await pipe.ainvoke({"value": "x", "run_context": ctx})
    assert out["value"] == "x-1-2"
    assert out["run_context"]["run_id"] == "r1"


@pytest.mark.asyncio
async def test_parallel_named_branches():
    left = RunnableLambda(lambda x: f"L:{x}")
    right = RunnableLambda(lambda x: f"R:{x}")
    pipe = parallel(left=left, right=right, name="lr")
    out = await pipe.ainvoke("z")
    assert out["value"]["left"] == "L:z"
    assert out["value"]["right"] == "R:z"


@pytest.mark.asyncio
async def test_parallel_sequence_of_runnables():
    a = RunnableLambda(lambda x: x + 1)
    b = RunnableLambda(lambda x: x * 2)
    pipe = parallel([a, b])
    out = await pipe.ainvoke(3)
    assert out["value"]["0"] == 4
    assert out["value"]["1"] == 6


def test_sequence_requires_steps():
    with pytest.raises(ValueError):
        sequence()


def test_parallel_requires_steps():
    with pytest.raises(ValueError):
        parallel()
