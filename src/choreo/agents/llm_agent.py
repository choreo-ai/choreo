"""LLMAgent: configurable tool-loop agent that IS an LCEL Runnable."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.runnables import Runnable, RunnableConfig
from langchain_core.tools import BaseTool

from choreo.core.context import InMemoryRunContext, RunContext
from choreo.core.events import (
    EventEmitter,
    LLMCalled,
    RunFinished,
    RunStarted,
    SimpleEventEmitter,
    StepFinished,
    ToolCalled,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _extract_context(
    input_value: Any,
    config: RunnableConfig | None,
    default: RunContext | None,
) -> RunContext:
    if isinstance(input_value, dict) and input_value.get("run_context") is not None:
        rc = input_value["run_context"]
        if isinstance(rc, RunContext):
            return rc
        if isinstance(rc, dict):
            return InMemoryRunContext.from_state_dict(rc)
    if config is not None:
        configurable = config.get("configurable") or {}
        rc = configurable.get("run_context")
        if isinstance(rc, RunContext):
            return rc
        if isinstance(rc, dict):
            return InMemoryRunContext.from_state_dict(rc)
    if default is not None:
        return default
    return InMemoryRunContext()


def _normalize_messages(input_value: Any, instructions: str) -> list[BaseMessage]:
    messages: list[BaseMessage] = []
    if instructions:
        messages.append(SystemMessage(content=instructions))

    if isinstance(input_value, str):
        messages.append(HumanMessage(content=input_value))
        return messages

    if isinstance(input_value, BaseMessage):
        messages.append(input_value)
        return messages

    if isinstance(input_value, list):
        messages.extend(input_value)
        return messages

    if isinstance(input_value, dict):
        if "messages" in input_value:
            raw = input_value["messages"]
            messages.extend(raw)
            return messages
        if "input" in input_value:
            return _normalize_messages(input_value["input"], instructions)
        if "value" in input_value:
            return _normalize_messages(input_value["value"], instructions)

    messages.append(HumanMessage(content=str(input_value)))
    return messages


def _tool_call_name(tc: Any) -> str:
    if isinstance(tc, dict):
        return str(tc.get("name") or "")
    return str(getattr(tc, "name", "") or "")


def _tool_call_args(tc: Any) -> dict[str, Any]:
    if isinstance(tc, dict):
        args = tc.get("args") or {}
        return dict(args) if isinstance(args, dict) else {"input": args}
    args = getattr(tc, "args", None) or {}
    return dict(args) if isinstance(args, dict) else {"input": args}


def _tool_call_id(tc: Any) -> str:
    if isinstance(tc, dict):
        return str(tc.get("id") or "")
    return str(getattr(tc, "id", "") or "")


class LLMAgent(Runnable[Any, Any]):
    """Single configurable agent: system instructions + tools + model tool loop.

    Implements LCEL ``Runnable`` (ADR 0002). Variation is configuration, not
    subclassing (ADR 0001).
    """

    def __init__(
        self,
        *,
        instructions: str = "",
        tools: Sequence[BaseTool] | None = None,
        model: BaseChatModel | None = None,
        max_steps: int = 10,
        name: str = "llm_agent",
        emitter: EventEmitter | None = None,
        context: RunContext | None = None,
    ) -> None:
        if model is None:
            raise ValueError(
                "LLMAgent requires a model=BaseChatModel; "
                "pass a fake model in tests or choreo.models.get_default_model() for live runs"
            )
        if max_steps < 1:
            raise ValueError("max_steps must be >= 1")
        self.instructions = instructions
        self.tools: list[BaseTool] = list(tools or [])
        self.model = model
        self.max_steps = max_steps
        self.name = name
        self.emitter = emitter if emitter is not None else SimpleEventEmitter()
        self._default_context = context
        self._tool_map = {t.name: t for t in self.tools}

    def invoke(
        self,
        input: Any,
        config: RunnableConfig | None = None,
        **kwargs: Any,
    ) -> Any:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.ainvoke(input, config, **kwargs))
        raise RuntimeError(
            "LLMAgent.invoke() cannot be called from a running event loop; use ainvoke()"
        )

    async def ainvoke(
        self,
        input: Any,
        config: RunnableConfig | None = None,
        **kwargs: Any,
    ) -> Any:
        context = _extract_context(input, config, self._default_context)
        messages = _normalize_messages(input, self.instructions)
        node_id = self.name

        await self.emitter.emit(
            RunStarted(
                run_id=context.run_id,
                seq=context.next_event_seq(),
                ts=_utcnow(),
                node_id=node_id,
                input_summary=_summarize_input(input),
            )
        )

        bound: Any = self.model
        if self.tools:
            bound = self.model.bind_tools(self.tools)

        final_text: Any = None
        status: str = "ok"
        error: str | None = None

        try:
            for step in range(self.max_steps):
                step_started = time.perf_counter()
                llm_started = time.perf_counter()
                llm_error: str | None = None
                success = True
                try:
                    ai_message = await bound.ainvoke(messages, config=config)
                except Exception as exc:
                    success = False
                    llm_error = str(exc)
                    await self.emitter.emit(
                        LLMCalled(
                            run_id=context.run_id,
                            seq=context.next_event_seq(),
                            ts=_utcnow(),
                            node_id=node_id,
                            model=getattr(self.model, "model", None)
                            or getattr(self.model, "model_name", None),
                            duration_ms=(time.perf_counter() - llm_started) * 1000.0,
                            success=False,
                            error=llm_error,
                        )
                    )
                    raise

                if not isinstance(ai_message, AIMessage):
                    # Some bindings may return content-only; normalize.
                    ai_message = AIMessage(content=str(ai_message))

                await self.emitter.emit(
                    LLMCalled(
                        run_id=context.run_id,
                        seq=context.next_event_seq(),
                        ts=_utcnow(),
                        node_id=node_id,
                        model=getattr(self.model, "model", None)
                        or getattr(self.model, "model_name", None),
                        duration_ms=(time.perf_counter() - llm_started) * 1000.0,
                        success=True,
                    )
                )
                messages.append(ai_message)

                tool_calls = list(getattr(ai_message, "tool_calls", None) or [])
                if not tool_calls:
                    final_text = ai_message.content
                    await self.emitter.emit(
                        StepFinished(
                            run_id=context.run_id,
                            seq=context.next_event_seq(),
                            ts=_utcnow(),
                            node_id=node_id,
                            step_name=f"{node_id}:step_{step}",
                            success=True,
                            duration_ms=(time.perf_counter() - step_started) * 1000.0,
                        )
                    )
                    break

                for tc in tool_calls:
                    tool_name = _tool_call_name(tc)
                    tool = self._tool_map.get(tool_name)
                    t0 = time.perf_counter()
                    if tool is None:
                        tool_result = f"error: unknown tool '{tool_name}'"
                        tool_ok = False
                        tool_err = tool_result
                    else:
                        try:
                            tool_result = await tool.ainvoke(_tool_call_args(tc), config=config)
                            tool_ok = True
                            tool_err = None
                        except Exception as exc:
                            tool_result = f"error: {exc}"
                            tool_ok = False
                            tool_err = str(exc)

                    await self.emitter.emit(
                        ToolCalled(
                            run_id=context.run_id,
                            seq=context.next_event_seq(),
                            ts=_utcnow(),
                            node_id=node_id,
                            tool_name=tool_name,
                            duration_ms=(time.perf_counter() - t0) * 1000.0,
                            success=tool_ok,
                            error=tool_err,
                        )
                    )
                    messages.append(
                        ToolMessage(
                            content=str(tool_result),
                            tool_call_id=_tool_call_id(tc) or tool_name,
                        )
                    )

                await self.emitter.emit(
                    StepFinished(
                        run_id=context.run_id,
                        seq=context.next_event_seq(),
                        ts=_utcnow(),
                        node_id=node_id,
                        step_name=f"{node_id}:step_{step}",
                        success=True,
                        duration_ms=(time.perf_counter() - step_started) * 1000.0,
                    )
                )
            else:
                # max_steps exhausted without a terminal AI message
                status = "aborted"
                error = f"max_steps ({self.max_steps}) reached without final answer"
                final_text = messages[-1].content if messages else None

        except Exception as exc:
            status = "error"
            error = str(exc)
            await self.emitter.emit(
                RunFinished(
                    run_id=context.run_id,
                    seq=context.next_event_seq(),
                    ts=_utcnow(),
                    node_id=node_id,
                    status="error",
                    error=error,
                )
            )
            raise

        await self.emitter.emit(
            RunFinished(
                run_id=context.run_id,
                seq=context.next_event_seq(),
                ts=_utcnow(),
                node_id=node_id,
                status=status if status in ("ok", "error", "aborted", "escalated") else "ok",
                error=error,
                output_summary=str(final_text)[:200] if final_text is not None else None,
            )
        )

        if isinstance(input, dict) and (
            "run_context" in input or "value" in input or "input" in input
        ):
            return {
                "value": final_text,
                "output": final_text,
                "messages": messages,
                "run_context": context.to_state_dict()
                if hasattr(context, "to_state_dict")
                else context,
            }
        return final_text


def _summarize_input(input_value: Any) -> str | None:
    if input_value is None:
        return None
    text = str(input_value)
    return text if len(text) <= 200 else text[:200] + "..."
