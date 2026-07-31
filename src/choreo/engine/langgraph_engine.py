"""Compile sequence/parallel agent plans to a LangGraph StateGraph.

Requires optional extra: ``pip install choreo[langgraph]``.

Middleware wraps each node *before* ``add_node`` (ADR 0003, ADR 0005).
``RunContext`` lives in graph state (ADR 0006). Checkpointer: ``InMemorySaver``.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from typing import Any, TypedDict

from langchain_core.runnables import Runnable

from choreo.core.context import InMemoryRunContext, RunContext
from choreo.core.middleware import Middleware
from choreo.core.middleware_impl import OnionMiddlewareStack


class GraphState(TypedDict, total=False):
    """Graph state channel layout for Choreo plans."""

    value: Any
    output: Any
    run_context: dict[str, Any]


def _require_langgraph() -> tuple[Any, Any, Any, Any]:
    try:
        from langgraph.checkpoint.memory import InMemorySaver
        from langgraph.graph import END, START, StateGraph
    except ImportError as exc:  # pragma: no cover - exercised when extra missing
        raise ImportError(
            "choreo.engine requires langgraph; install with: pip install choreo[langgraph]"
        ) from exc
    return StateGraph, START, END, InMemorySaver


def wrap_node_with_middleware(
    node: Runnable[Any, Any] | Callable[[Any], Awaitable[Any]],
    middleware: Sequence[Middleware] | None = None,
    *,
    node_id: str | None = None,
) -> Callable[[GraphState], Awaitable[GraphState]]:
    """Wrap a Runnable/callable with middleware onion; return a graph node fn.

    The returned async function reads/writes ``GraphState`` including
    ``run_context``. Middleware is applied before the node body runs.
    """
    layers = list(middleware or [])
    stack = OnionMiddlewareStack(layers)

    async def _call_node(value: Any, context: RunContext) -> Any:
        if isinstance(node, Runnable):
            result = await node.ainvoke(
                {"value": value, "input": value, "run_context": context}
            )
        else:
            result = await node(value)

        if isinstance(result, dict) and (
            "value" in result or "output" in result or "run_context" in result
        ):
            return result.get("output", result.get("value", result))
        return result

    async def graph_node(state: GraphState) -> GraphState:
        raw_ctx = state.get("run_context") or {}
        if isinstance(raw_ctx, RunContext):
            context: RunContext = raw_ctx
        else:
            context = InMemoryRunContext.from_state_dict(dict(raw_ctx))

        value = state.get("value", state.get("output"))

        async def terminal(v: Any) -> Any:
            return await _call_node(v, context)

        wrapped = stack.wrap_with_context(terminal, context=context)
        output = await wrapped(value)

        return {
            "value": output,
            "output": output,
            "run_context": context.to_state_dict()
            if hasattr(context, "to_state_dict")
            else dict(raw_ctx),
        }

    if node_id:
        graph_node.__name__ = f"choreo_node_{node_id}"
    return graph_node


def compile_plan(
    steps: Sequence[tuple[str, Runnable[Any, Any] | Callable[[Any], Awaitable[Any]]]],
    *,
    middleware: Sequence[Middleware] | None = None,
    checkpointer: Any | None = None,
    parallel_groups: Sequence[Sequence[str]] | None = None,
) -> Any:
    """Compile a plan of named steps into a LangGraph compiled graph.

    Args:
        steps: Ordered ``(name, node)`` pairs. By default nodes run in sequence.
        middleware: Applied around *each* node before ``add_node``.
        checkpointer: Defaults to ``InMemorySaver()``.
        parallel_groups: Optional list of node-name groups that should run in
            parallel (fan-out from the previous barrier, fan-in to the next).
            Names must appear in ``steps``. When omitted, all steps are sequential.

    Returns:
        A compiled LangGraph graph (``CompiledStateGraph``).
    """
    StateGraph, START, END, InMemorySaver = _require_langgraph()

    if not steps:
        raise ValueError("compile_plan() requires at least one step")

    names = [name for name, _ in steps]
    if len(set(names)) != len(names):
        raise ValueError("step names must be unique")

    node_map = {name: node for name, node in steps}
    saver = checkpointer if checkpointer is not None else InMemorySaver()

    graph = StateGraph(GraphState)
    for name, node in steps:
        # Middleware wraps BEFORE add_node (ADR 0003 / ADR 0005).
        wrapped = wrap_node_with_middleware(node, middleware, node_id=name)
        graph.add_node(name, wrapped)

    # Build edge plan: sequential by default; optional parallel groups.
    if not parallel_groups:
        graph.add_edge(START, names[0])
        for left, right in zip(names, names[1:]):
            graph.add_edge(left, right)
        graph.add_edge(names[-1], END)
    else:
        ordered_blocks: list[Sequence[str]] = list(parallel_groups)
        flat = [n for block in ordered_blocks for n in block]
        if set(flat) != set(names) or len(flat) != len(names):
            raise ValueError("parallel_groups must partition the step names exactly")
        # START -> first block
        first = ordered_blocks[0]
        for n in first:
            graph.add_edge(START, n)
        for i in range(len(ordered_blocks) - 1):
            current = ordered_blocks[i]
            nxt = ordered_blocks[i + 1]
            # Fan-in/out: every node in current connects to every node in next
            # when current is multi and next is multi; for sequential blocks
            # (len==1) this is a single edge.
            for a in current:
                for b in nxt:
                    graph.add_edge(a, b)
        for n in ordered_blocks[-1]:
            graph.add_edge(n, END)

    return graph.compile(checkpointer=saver)


async def arun_plan(
    compiled: Any,
    value: Any,
    *,
    run_context: RunContext | dict[str, Any] | None = None,
    thread_id: str = "choreo-default",
) -> GraphState:
    """Invoke a compiled plan with ``RunContext`` seeded into state."""
    if run_context is None:
        ctx_dict = InMemoryRunContext().to_state_dict()
    elif isinstance(run_context, RunContext):
        ctx_dict = run_context.to_state_dict()
    else:
        ctx_dict = dict(run_context)

    result = await compiled.ainvoke(
        {"value": value, "output": value, "run_context": ctx_dict},
        config={"configurable": {"thread_id": thread_id}},
    )
    return result
