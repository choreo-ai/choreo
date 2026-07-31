# ADR 0005: Engine = LangGraph

## Status

Accepted (locked).

## Context

Production multi-agent systems need durable state, resumable runs, streaming, and
human-in-the-loop. Building a competing engine would split ecosystem effort and delay the
value-add that actually differentiates Choreo.

## Decision

**Engine = LangGraph.** Use `StateGraph` + a checkpointer for state, resume, streaming, and
HITL (`interrupt` / `Command(resume=...)`).

- We are LangGraph-native by choice.
- Middleware wraps each node **before** it goes into the graph.
- Choreo combinators compile down to LangGraph graphs (or Runnable graphs that LangGraph
  can host).

Do not build a competing runtime.

## Consequences

- Positive: inherit checkpointing, streaming, interrupt, and ecosystem tooling.
- Positive: users already on LangGraph add Choreo concerns without migration.
- Negative: optional dependency on `langgraph` (extra); engine code isolated under
  `choreo.engine`.
- Follow-on: `RunContext` in graph state (ADR 0006) so budgets survive resume.
