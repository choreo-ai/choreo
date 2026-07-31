"""Middleware onion: cross-cutting wrappers around a node call.

Design (ADR 0003): retry, budget, trace, cache, and guardrail are composable
layers wrapped around a node *before* it is registered with the engine.
Order is explicit; user middleware is a first-class citizen.

Contracts only -- no production behavior yet (vertical slice implements stacks).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, Sequence
from typing import Any, TypeVar

from choreoai.core.context import RunContext

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")

# Async call into the next layer (or the underlying node).
# Signature is intentionally small so middleware stays easy to test.
NextCall = Callable[[Any], Awaitable[Any]]


class Middleware(ABC):
    """One layer in the onion around a node invocation.

    Implementations wrap ``call_next`` to run logic before/after the inner call,
    short-circuit, or translate errors. Prefer async-first; sync entry points
    are thin wrappers provided by the stack composer (not defined here yet).

    Recommended built-in order (outermost first), unless the user overrides::

        Trace -> Budget -> Guardrail(pre) -> Retry -> node -> Guardrail(post)

    Middleware must not assume a concrete engine; it only sees input, the next
    callable, and ``RunContext`` (when provided via the call convention below).
    """

    name: str
    """Stable short name for logs and events (e.g. ``\"budget\"``, ``\"trace\"``)."""

    @abstractmethod
    async def ainvoke(
        self,
        value: Any,
        call_next: NextCall,
        *,
        context: RunContext | None = None,
    ) -> Any:
        """Handle one invocation.

        Args:
            value: Input to this layer (usually the node input).
            call_next: Awaitable callable that invokes the inner layer/node
                with a (possibly modified) value and returns the inner output.
            context: Optional per-run context (budget ledger, event cursor).
                When the node runs inside a ChoreoAI/LangGraph state, this is the
                same object stored in graph state (ADR 0006).

        Returns:
            Output passed outward to the previous layer (or the caller).

        Raises:
            Exception: Propagated or translated. Budget/guardrail layers may
                raise typed errors that recovery policies interpret.
        """
        ...


def call_next(inner: NextCall, value: Any) -> Awaitable[Any]:
    """Invoke the next layer. Documented helper for middleware authors.

    Exists so examples and docs share one name; implementation is the identity
    call. Full stack machinery will live on ``MiddlewareStack``.
    """
    return inner(value)


class MiddlewareStack(ABC):
    """Ordered composition of middleware around a terminal node callable.

    The stack is itself presented to the engine as a single node-shaped async
    callable (and, in the implementation slice, as an LCEL ``Runnable``).
    """

    @abstractmethod
    def layers(self) -> Sequence[Middleware]:
        """Return middleware in application order (outermost first)."""
        ...

    @abstractmethod
    async def ainvoke(self, value: Any, *, context: RunContext | None = None) -> Any:
        """Run the full onion: outer layers wrap the terminal node.

        Args:
            value: Node input.
            context: Optional ``RunContext`` threaded through every layer.

        Returns:
            Terminal node output after all layers unwind.
        """
        ...

    @abstractmethod
    def wrap(self, node: Callable[[Any], Awaitable[Any]]) -> Callable[[Any], Awaitable[Any]]:
        """Bind a terminal async node and return a single async callable.

        Args:
            node: Underlying agent/tool/user Runnable entry (async).

        Returns:
            Async callable with the same input/output shape as ``node``, with
            all middleware applied. Implementation slice will also expose this
            as ``langchain_core.runnables.Runnable``.
        """
        ...
