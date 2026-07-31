"""Concrete middleware layers and stack for the vertical slice.

Implements the ``Middleware`` / ``MiddlewareStack`` contracts from
``choreoai.core.middleware`` without redefining the ABCs.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable, Sequence
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from choreoai.core.context import RunContext
from choreoai.core.events import EventEmitter, SimpleEventEmitter, StepFinished
from choreoai.core.middleware import Middleware, MiddlewareStack, NextCall

if TYPE_CHECKING:
    # Avoid circular import: reliability.budget imports core.context, and
    # core.__init__ imports this module. Runtime imports are deferred below.
    from choreoai.reliability.budget import Budget


class OnionMiddlewareStack(MiddlewareStack):
    """Ordered onion of middleware around a terminal async node callable."""

    def __init__(
        self,
        layers: Sequence[Middleware] | None = None,
        node: Callable[[Any], Awaitable[Any]] | None = None,
    ) -> None:
        self._layers: list[Middleware] = list(layers or [])
        self._node = node

    def layers(self) -> Sequence[Middleware]:
        return list(self._layers)

    def wrap(self, node: Callable[[Any], Awaitable[Any]]) -> Callable[[Any], Awaitable[Any]]:
        layers = list(self._layers)

        async def wrapped(value: Any) -> Any:
            async def call_layer(index: int, v: Any) -> Any:
                if index >= len(layers):
                    return await node(v)

                async def call_next(inner_v: Any) -> Any:
                    return await call_layer(index + 1, inner_v)

                return await layers[index].ainvoke(v, call_next, context=None)

            return await call_layer(0, value)

        return wrapped

    def wrap_with_context(
        self,
        node: Callable[[Any], Awaitable[Any]],
        *,
        context: RunContext | None,
    ) -> Callable[[Any], Awaitable[Any]]:
        """Like ``wrap`` but threads a fixed ``RunContext`` through every layer."""
        layers = list(self._layers)

        async def wrapped(value: Any) -> Any:
            async def call_layer(index: int, v: Any) -> Any:
                if index >= len(layers):
                    return await node(v)

                async def call_next(inner_v: Any) -> Any:
                    return await call_layer(index + 1, inner_v)

                return await layers[index].ainvoke(v, call_next, context=context)

            return await call_layer(0, value)

        return wrapped

    async def ainvoke(self, value: Any, *, context: RunContext | None = None) -> Any:
        if self._node is None:
            raise RuntimeError("OnionMiddlewareStack has no terminal node; call wrap() first")
        wrapped = self.wrap_with_context(self._node, context=context)
        return await wrapped(value)


class BudgetMiddleware(Middleware):
    """Check/consume budget before the inner call; raise ``BudgetExhausted`` when denied."""

    name = "budget"

    def __init__(
        self,
        budget: Budget,
        *,
        amounts: dict[str, float] | None = None,
        name: str = "budget",
    ) -> None:
        # Lazy import: keep core importable before/without reliability load order.
        from choreoai.reliability.budget import BudgetDimensions

        self.budget = budget
        self.name = name
        # Default: one step per wrapped node invocation.
        self.amounts = (
            dict(amounts) if amounts is not None else {BudgetDimensions.STEPS.value: 1.0}
        )

    async def ainvoke(
        self,
        value: Any,
        call_next: NextCall,
        *,
        context: RunContext | None = None,
    ) -> Any:
        from choreoai.reliability.budget import BudgetExhausted

        # check then consume (consume re-checks); strict raises BudgetExhausted
        decision = self.budget.check(self.amounts, context=context)
        if not decision.allowed:
            raise BudgetExhausted(
                decision.reason or "budget exhausted",
                decision=decision,
            )
        self.budget.consume(self.amounts, context=context, strict=True)
        return await call_next(value)


class TraceMiddleware(Middleware):
    """Emit ``StepFinished`` (and optional start metadata) to event subscribers."""

    name = "trace"

    def __init__(
        self,
        emitter: EventEmitter | None = None,
        *,
        node_id: str | None = None,
        name: str = "trace",
    ) -> None:
        self.emitter = emitter if emitter is not None else SimpleEventEmitter()
        self.node_id = node_id
        self.name = name

    async def ainvoke(
        self,
        value: Any,
        call_next: NextCall,
        *,
        context: RunContext | None = None,
    ) -> Any:
        started = time.perf_counter()
        success = True
        error: str | None = None
        try:
            return await call_next(value)
        except Exception as exc:
            success = False
            error = str(exc)
            raise
        finally:
            duration_ms = (time.perf_counter() - started) * 1000.0
            run_id = context.run_id if context is not None else "unknown"
            seq = context.next_event_seq() if context is not None else 0
            event = StepFinished(
                run_id=run_id,
                seq=seq,
                ts=datetime.now(timezone.utc),
                node_id=self.node_id,
                step_name=self.node_id or self.name,
                success=success,
                duration_ms=duration_ms,
                error=error,
            )
            await self.emitter.emit(event)
