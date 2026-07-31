# ADR 0006: RunContext lives inside the graph state

## Status

Accepted (locked).

## Context

Budgets and observability cursors must survive pause/resume and process restart when a
checkpointer is used. Thread-local or process-global run state is lost on resume and breaks
HITL and long-running agents.

## Decision

`RunContext` lives **inside the LangGraph graph state**. It holds at least:

- **Budget ledger** -- consumed vs caps (tokens, cost, steps, wall time, tool calls).
- **Event cursor** -- monotonic sequence identity for the typed event stream.

On checkpoint/resume, ledger and cursor restore with the thread. Nodes and middleware read
and update `RunContext` through the state channel (with a documented reducer if needed).

## Consequences

- Positive: budgets and progress are durable under LangGraph checkpointers.
- Positive: multi-thread isolation is natural (per `thread_id` state).
- Negative: state schema must include a `run_context` (or equivalent) channel; reducers must
  merge ledger updates correctly under parallel nodes.
- Follow-on: contract in `choreoai.core.context`; budget in `choreoai.reliability.budget`.
