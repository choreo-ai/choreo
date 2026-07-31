"""2-agent researcher + synthesizer pipeline demo (budgets + traces).

Uses the real default Claude model (``claude-sonnet-5``) and requires
``ANTHROPIC_API_KEY``. This module is intentionally NOT collected by pytest
(guarded below).

Run::

    set ANTHROPIC_API_KEY=...
    python examples/research_pipeline.py "What is LangGraph?"
"""

from __future__ import annotations

import asyncio
import os
import sys

# Guard: never execute the live pipeline under pytest collection/import.
if "pytest" in sys.modules:
    raise RuntimeError(
        "examples/research_pipeline.py must not run under pytest "
        "(requires ANTHROPIC_API_KEY and network)"
    )


async def _run(question: str) -> None:
    from langchain_core.tools import tool

    from choreoai.agents import LLMAgent
    from choreoai.core import (
        BudgetMiddleware,
        InMemoryRunContext,
        ListSubscriber,
        SimpleEventEmitter,
        TraceMiddleware,
    )
    from choreoai.core.middleware_impl import OnionMiddlewareStack
    from choreoai.models import get_default_model
    from choreoai.orchestrate import sequence
    from choreoai.reliability import InMemoryBudget

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY is not set; aborting demo.", file=sys.stderr)
        sys.exit(1)

    emitter = SimpleEventEmitter()
    subscriber = ListSubscriber(name="demo_trace")
    emitter.subscribe(subscriber)

    @tool
    def note(text: str) -> str:
        """Record a short research note (demo tool)."""
        return f"noted: {text}"

    model = get_default_model()
    researcher = LLMAgent(
        name="researcher",
        instructions=(
            "You are a researcher. Use the note tool once if helpful, "
            "then answer briefly with key facts."
        ),
        tools=[note],
        model=model,
        max_steps=4,
        emitter=emitter,
    )
    synthesizer = LLMAgent(
        name="synthesizer",
        instructions=(
            "You are a synthesizer. Turn research notes into a short summary."
        ),
        tools=[],
        model=model,
        max_steps=2,
        emitter=emitter,
    )

    budget = InMemoryBudget(caps={"steps": 10})
    pipeline = sequence(researcher, synthesizer, name="research_pipeline")
    context = InMemoryRunContext(
        budget_ledger={"caps": {"steps": 10}, "consumed": {}, "labels": {}}
    )

    async def run_pipeline(value: object) -> object:
        return await pipeline.ainvoke({"value": value, "run_context": context})

    stack = OnionMiddlewareStack(
        [
            TraceMiddleware(emitter=emitter, node_id="pipeline"),
            BudgetMiddleware(budget, amounts={"steps": 1}),
        ],
        node=run_pipeline,
    )
    result = await stack.ainvoke(question, context=context)

    print("=== output ===")
    if isinstance(result, dict):
        print(result.get("output", result.get("value", result)))
    else:
        print(result)

    print("=== budget ===")
    print(budget.snapshot(context=context))

    print("=== events ({}) ===".format(len(subscriber.events)))
    for event in subscriber.events:
        print("  [{}] {} node={}".format(event.seq, event.type, event.node_id))


def main() -> None:
    question = " ".join(sys.argv[1:]).strip() or "What is LangGraph in one paragraph?"
    asyncio.run(_run(question))


if __name__ == "__main__":
    main()
