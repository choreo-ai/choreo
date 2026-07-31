# ADR 0008: Packaging = optional extras

## Status

Accepted (locked).

## Context

Forcing every user to install LangGraph, the full LangChain meta-package, and every
integration makes installs heavy and blurs what "core" means. Honesty about dependencies
matches the pre-alpha product stance.

## Decision

Optional extras keep installs honest:

| Install | Provides |
|---|---|
| `pip install choreoai` | Core + Claude model client; depends on `langchain-core` (+ `langchain-anthropic`) |
| `choreoai[langgraph]` | LangGraph engine |
| `choreoai[langchain]` | Extra LangChain integrations/adapters |

Rules:

- Core must **not** import the heavy `langchain` package; anchor on `langchain-core`.
- Only `choreoai.engine` and `choreoai.integrations` may import `langgraph` / heavier
  `langchain`.
- Import errors for missing extras should be clear and actionable.

## Consequences

- Positive: small default install; extras match use case.
- Positive: enforces architectural boundaries in code review.
- Negative: more matrix testing (core vs extras); docs must show install paths.
- Follow-on: `pyproject.toml` extras wired when the vertical slice lands.
