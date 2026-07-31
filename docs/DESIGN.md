# ChoreoAI design

**Status:** pre-alpha foundation. Architecture decisions below are **locked** (see
`docs/adr/`). Implementation contracts for the owned value-add layer live under
`src/choreoai/` as signatures + docstrings only until the vertical slice lands.

**Tagline:** Multi-agent systems, in production.

**Positioning:** *"The production layer for LangGraph."* Drop ChoreoAI onto an existing
LangChain/LangGraph app and opt into budgets, retries, recovery, guardrails, context
engineering, evals, and observability -- without rewriting tools, models, or graphs.

## Goals

1. **Zero rewrite for substrate assets.** Existing `BaseTool`, `BaseChatModel`, and LCEL
   `Runnable` graphs work unchanged.
2. **Opt-in production concerns.** Value lives in budgets, middleware, guardrails,
   recovery, events -- not in forcing a ChoreoAI base class.
3. **LangGraph-native engine.** State, checkpoints, streaming, and HITL come from
   LangGraph; ChoreoAI does not build a competing runtime.
4. **Honest packaging.** Core stays light (`langchain-core` + Claude client); engine and
   heavier integrations are optional extras.

## Non-goals (for now)

- Competing with LangGraph as a graph engine.
- A `BaseAgent` template-method hierarchy.
- Requiring users to subclass ChoreoAI types to use tools or models.
- Shipping full evals / context-engineering implementations before the thin vertical slice.

## Architecture summary

```
User graph / combinators
        |
        v
  [ Middleware onion ]  <-- budget, retry, guardrail, trace (ChoreoAI value-add)
        |
        v
  LCEL Runnable nodes   <-- agents, tools, user Runnables (substrate)
        |
        v
  LangGraph StateGraph  <-- checkpointer, stream, interrupt (engine)
        |
        v
  RunContext in state   <-- budget ledger + event cursor (survives resume)
        |
        v
  Typed event stream    <-- subscribers: traces, metrics, evals
```

### Locked decisions (index)

| # | Decision | ADR |
|---|---|---|
| 1 | Composition over inheritance | [0001](adr/0001-composition-over-inheritance.md) |
| 2 | Uniform node interface = LCEL `Runnable` | [0002](adr/0002-lcel-runnable-node-interface.md) |
| 3 | Cross-cutting concerns = middleware onion | [0003](adr/0003-middleware-onion.md) |
| 4 | Compatibility-first substrate; owned opt-in value-add | [0004](adr/0004-compat-first-owned-value-add.md) |
| 5 | Engine = LangGraph | [0005](adr/0005-langgraph-engine.md) |
| 6 | `RunContext` lives in graph state | [0006](adr/0006-runcontext-in-graph-state.md) |
| 7 | Typed event stream as public observability contract | [0007](adr/0007-typed-event-stream.md) |
| 8 | Packaging = optional extras | [0008](adr/0008-packaging-optional-extras.md) |

### Seam table

| User wants to... | Implements | Core still owns |
|---|---|---|
| Add a capability | `BaseTool` (or `@choreoai.tool`) | dispatch, arg validation, budgeting |
| Swap the LLM/provider | `BaseChatModel` | the agent loop |
| Add a cross-cutting concern | `Middleware` | ordering and the run |
| Add a validation/safety check | `Guardrail` | when checks run, recovery |
| Observe (trace/metrics/eval) | `Subscriber` (event) | the event stream |
| Fully custom agent/node | LCEL `Runnable` | composition, budgets, tracing |
| Compose agents | combinators (`sequence`/`parallel`/`route`/`loop`/`supervise`) | -- |

## Module layout

```
src/choreoai/
  core/         runnable.py (re-export/alias LCEL)  tool.py  model.py
                middleware.py  guardrail.py  context.py  events.py
  reliability/  budget.py  retry.py  recovery.py  guardrails/
  contexteng/   assembly.py  trimming.py  routing.py
  agents/       llm_agent.py
  orchestrate/  combinators.py
  engine/       langgraph_engine.py
  models/       claude.py
  integrations/ langchain_tools.py
  evals/        harness.py
```

- `core/`, `reliability/`, `contexteng/`, `agents/` import only `langchain-core` + each other.
- `engine/` and `integrations/` are the only places `langgraph` / heavier `langchain` appear.

## Owned value-add contracts (locked signatures)

These are **ours**. Full behavior comes in later slices; the public shapes are fixed here so
implementation does not invent interfaces ad hoc.

| Concern | Module | Role |
|---|---|---|
| Budget | `choreoai.reliability.budget` | Caps and ledger for tokens/cost/steps/time/tools |
| Middleware | `choreoai.core.middleware` | Onion wrap around a node call |
| Guardrail | `choreoai.core.guardrail` | Pre/post validation that can trip recovery |
| Recovery | `choreoai.reliability.recovery` | retry-with-feedback / replan / fallback / escalate / abort |
| RunContext | `choreoai.core.context` | Per-run state: budget ledger + event cursor |
| Events | `choreoai.core.events` | Typed events + subscriber protocol |

See source docstrings for signatures. Implementations must stay async-first with thin sync
wrappers.

## Substrate (adopted, not re-defined)

Verified in [api-verification.md](api-verification.md):

- Tools: `langchain_core.tools.BaseTool`
- Models: `langchain_core.language_models.BaseChatModel` (default: `ChatAnthropic`)
- Nodes: `langchain_core.runnables.Runnable`
- Engine: LangGraph `StateGraph` + checkpointer + `interrupt`

## Implementation roadmap

1. ~~Verify substrate APIs~~ (this doc + `api-verification.md`)
2. ~~Design docs + ADRs for 8 locked decisions~~
3. ~~Lock value-add contracts (signatures + docstrings)~~
4. **Next:** thin vertical slice -- `LLMAgent` (Runnable) with tool loop over a
   `BaseChatModel`, one `Budget` + one `Trace` middleware, `sequence`/`parallel`, runnable
   on the LangGraph engine -- enough to demo budgets + traces on a 2-agent pipeline.

## Conventions

- Python 3.10+, `src/` layout, hatchling, type hints, `py.typed`
- Ruff, line length 100; pytest under `tests/`
- ASCII-safe stdout (Windows cp1252)
- Async-first; every change extends tests; pre-alpha honesty in README
