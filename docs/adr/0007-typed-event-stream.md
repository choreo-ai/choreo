# ADR 0007: Typed event stream is the public observability contract

## Status

Accepted (locked).

## Context

Teams need traces, metrics, and evals without baking a single vendor or logger into core.
LangGraph and LangChain already stream events; Choreo needs a stable, typed public contract
that value-add features can emit and subscribers can consume.

## Decision

The **public observability contract** is a **typed event stream**. Core event kinds include:

- `RunStarted` / `RunFinished`
- `LLMCalled`
- `ToolCalled`
- `GuardrailTripped`
- `StepFinished`

Tracing, metrics, and evals are **subscribers** -- they do not own the run loop. Bridge
LangGraph streaming / `astream_events` into this model where useful, but Choreo features
emit Choreo events explicitly so the contract stays stable across engine versions.

## Consequences

- Positive: open subscription model; self-hostable observability.
- Positive: guardrails and budgets can emit the same stream as LLM/tool steps.
- Negative: must maintain a bridge to LangGraph stream modes; avoid leaking engine-only
  event shapes as public API.
- Follow-on: contract in `choreo.core.events` (`Event`, `Subscriber`, concrete event types).
