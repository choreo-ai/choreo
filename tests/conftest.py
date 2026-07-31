"""Shared pytest fixtures: fake chat model, tools (offline, no API key)."""

from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage
from langchain_core.tools import tool

from fakes import FakeChatModel


@pytest.fixture
def add_tool():
    @tool
    def add(a: int, b: int) -> int:
        """Add two integers."""
        return a + b

    return add


@pytest.fixture
def fake_final_only():
    return FakeChatModel(responses=[AIMessage(content="final answer")])


@pytest.fixture
def fake_with_tool(add_tool):
    return FakeChatModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "add", "args": {"a": 2, "b": 3}, "id": "call_1"}
                ],
            ),
            AIMessage(content="sum is 5"),
        ]
    )
