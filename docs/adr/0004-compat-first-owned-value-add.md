# ADR 0004: Compatibility-first substrate; owned opt-in value-add

## Status

Accepted (locked).

## Context

Adoption dies if teams must rewrite tools and models to use a production layer. The product
promise is: drop ChoreoAI onto an existing LangChain/LangGraph app. The reason to install
ChoreoAI is production value-add, not a new substrate.

## Decision

Split the stack into two layers:

**Substrate (adopt their interfaces, from stable `langchain-core`):**

- Tools: `langchain_core.tools.BaseTool` (`@choreo.tool` only produces a `BaseTool`).
- Models: `langchain_core.language_models.BaseChatModel` (default Claude via
  `langchain-anthropic`).
- Node/agent: LCEL `Runnable` (ADR 0002).

**Value-add (ours, opt-in):**

- Budgets, retries, recovery policies (retry-with-feedback / replan / fallback / escalate /
  abort), guardrails, context engineering, evals, unified self-hostable observability.

Users never have to "abide by our principles" to use the substrate -- their assets just work.
Our principles live entirely in the opt-in value-add.

## Consequences

- Positive: honest differentiation; low migration cost.
- Positive: substrate churn is upstream's job; we pin and verify.
- Negative: we cannot "fix" upstream tool/model APIs; adapters stay thin.
- Follow-on: packaging keeps core free of heavy `langchain` (ADR 0008).
