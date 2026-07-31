"""sequence / parallel combinators returning LCEL Runnables that thread RunContext."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import Any

from langchain_core.runnables import Runnable, RunnableConfig, RunnableLambda

from choreoai.core.context import InMemoryRunContext, RunContext


def _as_runnable(node: Runnable[Any, Any] | Any) -> Runnable[Any, Any]:
    if isinstance(node, Runnable):
        return node
    if callable(node):
        return RunnableLambda(node)
    raise TypeError(f"Expected Runnable or callable, got {type(node)!r}")


def _unpack(input_value: Any) -> tuple[Any, RunContext | None]:
    if isinstance(input_value, dict) and (
        "run_context" in input_value or "value" in input_value or "input" in input_value
    ):
        value = input_value.get("value", input_value.get("input", input_value))
        rc = input_value.get("run_context")
        if isinstance(rc, RunContext):
            return value, rc
        if isinstance(rc, dict):
            return value, InMemoryRunContext.from_state_dict(rc)
        return value, None
    return input_value, None


def _pack(value: Any, context: RunContext | None) -> Any:
    if context is None:
        return value
    return {
        "value": value,
        "output": value,
        "run_context": context.to_state_dict()
        if hasattr(context, "to_state_dict")
        else context,
    }


def _child_input(value: Any, context: RunContext | None) -> Any:
    if context is None:
        return value
    if isinstance(value, dict) and "messages" in value:
        packed = dict(value)
        packed["run_context"] = context
        return packed
    return {"value": value, "input": value, "run_context": context}


def _child_output(result: Any) -> tuple[Any, RunContext | None]:
    if isinstance(result, dict) and (
        "run_context" in result or "value" in result or "output" in result
    ):
        value = result.get("output", result.get("value", result))
        rc = result.get("run_context")
        if isinstance(rc, RunContext):
            return value, rc
        if isinstance(rc, dict):
            return value, InMemoryRunContext.from_state_dict(rc)
        return value, None
    return result, None


def sequence(
    *steps: Runnable[Any, Any],
    name: str = "sequence",
) -> Runnable[Any, Any]:
    """Run steps left-to-right, threading value and ``RunContext``.

    Returns an LCEL ``Runnable``. Input may be a plain value or a dict with
    ``value``/``input`` and optional ``run_context``.
    """
    if not steps:
        raise ValueError("sequence() requires at least one step")
    runnables = [_as_runnable(s) for s in steps]

    async def _ainvoke(input_value: Any, config: RunnableConfig | None = None) -> Any:
        value, context = _unpack(input_value)
        for step in runnables:
            result = await step.ainvoke(_child_input(value, context), config=config)
            value, child_ctx = _child_output(result)
            if child_ctx is not None:
                context = child_ctx
        return _pack(value, context)

    def _invoke(input_value: Any, config: RunnableConfig | None = None) -> Any:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(_ainvoke(input_value, config))
        raise RuntimeError("sequence.invoke() cannot run inside an event loop; use ainvoke()")

    runnable: Runnable[Any, Any] = RunnableLambda(_invoke, afunc=_ainvoke).with_config(
        {"run_name": name}
    )
    return runnable


def parallel(
    steps: Sequence[Runnable[Any, Any]] | None = None,
    *,
    name: str = "parallel",
    **named: Runnable[Any, Any],
) -> Runnable[Any, Any]:
    """Run steps concurrently; return a dict of results and threaded ``RunContext``.

    Accepts either a sequence of runnables (keys ``0``, ``1``, ...) or keyword
    named branches. Each branch receives the same input value and context.
    """
    mapping: dict[str, Runnable[Any, Any]] = {}
    if steps is not None:
        for i, step in enumerate(steps):
            mapping[str(i)] = _as_runnable(step)
    for key, step in named.items():
        mapping[key] = _as_runnable(step)
    if not mapping:
        raise ValueError("parallel() requires at least one step")

    async def _ainvoke(input_value: Any, config: RunnableConfig | None = None) -> Any:
        value, context = _unpack(input_value)
        child_in = _child_input(value, context)

        async def _run(key: str, step: Runnable[Any, Any]) -> tuple[str, Any, RunContext | None]:
            result = await step.ainvoke(child_in, config=config)
            out, ctx = _child_output(result)
            return key, out, ctx

        pairs = await asyncio.gather(
            *[_run(k, s) for k, s in mapping.items()]
        )
        results: dict[str, Any] = {}
        # Prefer the context with the highest event cursor (most progressed).
        best_ctx = context
        best_cursor = context.event_cursor if context is not None else -1
        for key, out, ctx in pairs:
            results[key] = out
            if ctx is not None and ctx.event_cursor >= best_cursor:
                best_ctx = ctx
                best_cursor = ctx.event_cursor

        packed: dict[str, Any] = {"value": results, "output": results}
        if best_ctx is not None:
            packed["run_context"] = (
                best_ctx.to_state_dict()
                if hasattr(best_ctx, "to_state_dict")
                else best_ctx
            )
        return packed

    def _invoke(input_value: Any, config: RunnableConfig | None = None) -> Any:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(_ainvoke(input_value, config))
        raise RuntimeError("parallel.invoke() cannot run inside an event loop; use ainvoke()")

    runnable: Runnable[Any, Any] = RunnableLambda(_invoke, afunc=_ainvoke).with_config(
        {"run_name": name}
    )
    return runnable
