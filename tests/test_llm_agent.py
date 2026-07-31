"""Offline tests for LLMAgent tool loop (fake BaseChatModel, no network)."""

from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage
from langchain_core.runnables import Runnable

from choreoai.agents import LLMAgent
from choreoai.core import ListSubscriber, SimpleEventEmitter
from fakes import FakeChatModel


@pytest.mark.asyncio
async def test_llm_agent_is_runnable(fake_final_only):
    agent = LLMAgent(model=fake_final_only, instructions="You are helpful.")
    assert isinstance(agent, Runnable)
    out = await agent.ainvoke("hello")
    assert out == "final answer"


@pytest.mark.asyncio
async def test_tool_loop_dispatches_and_returns_final(fake_with_tool, add_tool):
    emitter = SimpleEventEmitter()
    sub = ListSubscriber()
    emitter.subscribe(sub)

    agent = LLMAgent(
        name="math",
        instructions="Use tools.",
        tools=[add_tool],
        model=fake_with_tool,
        max_steps=5,
        emitter=emitter,
    )
    out = await agent.ainvoke("2+3?")
    assert out == "sum is 5"

    types = [e.type for e in sub.events]
    assert "run_started" in types
    assert "llm_called" in types
    assert "tool_called" in types
    assert "step_finished" in types
    assert "run_finished" in types

    tool_events = [e for e in sub.events if e.type == "tool_called"]
    assert len(tool_events) == 1
    assert tool_events[0].tool_name == "add"
    assert tool_events[0].success is True
    assert fake_with_tool.call_count == 2


@pytest.mark.asyncio
async def test_max_steps_stops_loop(add_tool):
    # Always request the same tool; never produce a final answer.
    model = FakeChatModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "add", "args": {"a": 1, "b": 1}, "id": "c1"}
                ],
            ),
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "add", "args": {"a": 1, "b": 1}, "id": "c2"}
                ],
            ),
        ]
    )
    agent = LLMAgent(
        tools=[add_tool],
        model=model,
        max_steps=2,
    )
    out = await agent.ainvoke("loop")
    # After max_steps LLM rounds with only tool calls, loop stops (aborted).
    # Last message is a ToolMessage with the tool result ("2" from 1+1).
    assert model.call_count == 2
    assert out is not None


@pytest.mark.asyncio
async def test_unknown_tool_records_error(add_tool):
    model = FakeChatModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "missing", "args": {}, "id": "c1"}
                ],
            ),
            AIMessage(content="done"),
        ]
    )
    emitter = SimpleEventEmitter()
    sub = ListSubscriber()
    emitter.subscribe(sub)
    agent = LLMAgent(tools=[add_tool], model=model, emitter=emitter)
    out = await agent.ainvoke("x")
    assert out == "done"
    tool_events = [e for e in sub.events if e.type == "tool_called"]
    assert tool_events[0].success is False


def test_sync_invoke_works(fake_final_only):
    agent = LLMAgent(model=fake_final_only)
    assert agent.invoke("hi") == "final answer"
