# ADR 0003: Cross-cutting concerns = middleware (onion)

## Status

Accepted (locked).

## Context

Retry, budget enforcement, tracing, caching, and guardrails cut across every node. Putting
them on a base class (methods or overridable hooks) reintroduces inheritance coupling and
makes ordering implicit and hard to extend.

## Decision

Cross-cutting concerns are **composable middleware layers** wrapped around a node (onion
model):

- Each layer implements a small `Middleware` contract: wrap the next call.
- **Order is explicit** at composition time (outermost first).
- Users can add their own middleware without touching core.
- Built-in layers: budget, retry, trace, cache, guardrail (as needed).

Middleware is applied **before** a node is registered with the LangGraph engine so the
engine only sees already-wrapped Runnables.

## Consequences

- Positive: open for extension; clear stack traces of concern order.
- Positive: same stack can wrap first-party agents and third-party Runnables.
- Negative: misuse of order can surprise (e.g. budget outside vs inside retry); document
  recommended stacks.
- Follow-on: contracts in `choreoai.core.middleware` and `choreoai.core.guardrail`.
