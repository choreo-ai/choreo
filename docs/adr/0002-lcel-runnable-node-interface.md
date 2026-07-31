# ADR 0002: Uniform node interface = LCEL Runnable

## Status

Accepted (locked).

## Context

We need a single node interface so Choreo agents drop into user LangGraph/LCEL pipelines and
user nodes drop into Choreo combinators (bidirectional interop). Inventing our own `Node`
ABC would fork the ecosystem and require adapters in both directions.

## Decision

**Reuse** `langchain_core.runnables.Runnable`. A Choreo agent **is** an LCEL Runnable.

- Call contract: `invoke` / `ainvoke` / `stream` / `batch` (+ async variants).
- Composition: `|`, `RunnableParallel`, combinators that return Runnables.
- We may re-export or alias for ergonomics; we do not redefine the protocol.

## Consequences

- Positive: zero-adapter interop with LangChain/LangGraph.
- Positive: free batching, streaming, config, and retry helpers from the Runnable surface.
- Negative: we inherit LCEL quirks and version churn; must verify APIs before coding
  (see `docs/api-verification.md`).
- Follow-on: middleware wraps a Runnable and returns a Runnable (ADR 0003).
