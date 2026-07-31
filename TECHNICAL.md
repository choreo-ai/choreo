# ChoreoAI — Technical Design Notes

> Working design doc for discussion. Captures the current implementation, the public API and
> usage, the defaults strategy, and the open design questions (cost/budget, retries, guardrails).
> Sections marked **PROPOSED** / **OPEN** are not yet built — they are for review.
>
> Companion to `docs/DESIGN.md` and the ADRs in `docs/adr/`. Last updated: 2026-08-01.

---

## 1. Purpose & current status

ChoreoAI is a framework for **production-grade multi-agent systems** on top of LangChain +
LangGraph: reliability (budgets, retries, recovery), guardrails, orchestration, and a typed
observability stream are first-class, not bolt-ons.

Today the repo is a **complete, tested vertical slice** (~2,000 LOC, 34 tests, no stubs):

| Area | Module | State |
|---|---|---|
| Single agent (tool loop + events) | `agents/llm_agent.py` — `LLMAgent` | ✅ implemented |
| Typed event stream | `core/events.py` | ✅ implemented |
| Middleware onion + Budget/Trace layers | `core/middleware.py`, `core/middleware_impl.py` | ✅ implemented |
| Budget ledger (in `RunContext`) | `reliability/budget.py` | ✅ implemented |
| Guardrails (interface) | `core/guardrail.py` | ⚠️ defined, **not wired into the agent loop** |
| Recovery policies (interface) | `reliability/recovery.py` | ⚠️ interface only, **no concrete impl, not wired** |
| Orchestration `sequence` / `parallel` | `orchestrate/combinators.py` | ✅ implemented |
| LangGraph engine (compile / checkpoint / resume) | `engine/langgraph_engine.py` | ✅ implemented |
| Claude model factory | `models/claude.py` | ✅ implemented (thin) |

**Known gaps (see §6–§7):** no token/cost accounting; no retry/recovery execution; guardrails
not enforced in the agent loop; no streaming on `LLMAgent`.

---

## 2. Architecture & design decisions (confirmed)

| Decision | What it means | ADR |
|---|---|---|
| **Composition over inheritance** | No `BaseAgent` template to subclass. Variation = configuration + injected policies + middleware; full custom behavior = implement a `Runnable`. | 0001 |
| **Node interface = LCEL `Runnable`** | A ChoreoAI agent **is** a `langchain_core.runnables.Runnable` (`invoke`/`ainvoke`/`stream`/`batch`). Zero-adapter interop both directions. | 0002 |
| **Middleware onion** | Cross-cutting concerns (budget, trace, later guardrails/recovery) wrap a node from the outside and return a node. | 0003 |
| **Owned value-add, compat-first** | We do not fork LangChain/LangGraph; we add reliability/observability around them. | 0004 |
| **Engine = LangGraph** | Multi-node execution uses `StateGraph` + checkpointer for durable state, resume, streaming, HITL. Optional extra `choreoai[langgraph]`. | 0005 |
| **`RunContext` in graph state** | The run ledger (incl. budget) lives in graph state so it survives checkpoint/resume. | 0006 |
| **Typed event stream** | Core emits typed events; tracing/metrics/evals are subscribers. Public event shapes owned by ChoreoAI. | 0007 |

### Why LangGraph and not "just LangChain"
LangChain (LCEL) gives the **Runnable** interface, chat models, tools, and composition (`|`,
`RunnableParallel`) — but **no durable state, resume, streaming, or human-in-the-loop**. Those are
required for production multi-agent runs, so the *engine* is LangGraph. Single agents run as plain
LCEL Runnables; multi-agent **plans** compile to LangGraph graphs where `RunContext`/budgets
survive resume.

---

## 3. Core components (quick reference)

- **`LLMAgent`** (`Runnable[Any, Any]`): `instructions`, `tools`, `model`, `max_steps`, `name`,
  `emitter`, `context`. `bind_tools` → loop up to `max_steps`: call model → if `tool_calls`, run
  tools and append `ToolMessage`s → repeat; no tool calls ⇒ final answer. Emits
  `RunStarted → LLMCalled → ToolCalled → StepFinished → RunFinished`.
- **`EventEmitter` / `Subscriber`**: `SimpleEventEmitter` fans out to subscribers; a subscriber
  crash never tears down the run. `ListSubscriber` collects events (tests/traces). *This is the
  `emitter=` you pass to an agent — the observability seam.*
- **Middleware**: `Middleware.ainvoke(value, call_next, *, context)`. `OnionMiddlewareStack`
  wraps a terminal async node. `BudgetMiddleware` (check+consume a fixed `amounts`, default
  `{STEPS: 1}`), `TraceMiddleware` (emits `StepFinished`).
- **`Budget`** (`InMemoryBudget`): dimensions = `tokens`, `cost_usd`, `steps`, `wall_time_ms`,
  `tool_calls`, `llm_calls`. `check` / `consume` / `snapshot` / `is_exhausted`. Caps are a dict;
  **a missing dimension = unlimited**. Ledger can live in `RunContext` for resume.
- **`RunContext`** (`InMemoryRunContext`): `run_id`, `next_event_seq()`, `budget_ledger()` /
  `update_budget_ledger()`, `to_state_dict()` / `from_state_dict()`.
- **Orchestration**: `sequence(*steps)`, `parallel(steps=[...] | **named)` — both return Runnables
  and thread value + `RunContext`.
- **Engine**: `compile_plan(steps, middleware=…, parallel_groups=…)` → compiled LangGraph;
  `arun_plan(graph, value, run_context=…, thread_id=…)`.
- **Model**: `get_default_model(model=None)` → `ChatAnthropic` (default `claude-sonnet-5`,
  flagship `claude-opus-4-8`).

---

## 4. Usage examples (end-user)

### 4.1 Minimal single agent
```python
import asyncio
from choreoai.agents import LLMAgent
from choreoai.models import get_default_model  # needs ANTHROPIC_API_KEY

agent = LLMAgent(instructions="You are concise.", model=get_default_model())
print(asyncio.run(agent.ainvoke("Summarize LangGraph in one sentence.")))
```

### 4.2 Agent with tools
```python
from langchain_core.tools import tool

@tool
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b

agent = LLMAgent(instructions="Use tools when helpful.", tools=[add],
                 model=get_default_model(), max_steps=6)
```

### 4.3 Observability (subscribe to the event stream)
```python
from choreoai.core import SimpleEventEmitter, ListSubscriber

emitter = SimpleEventEmitter()
trace = ListSubscriber(name="trace")
emitter.subscribe(trace)

agent = LLMAgent(instructions="…", model=get_default_model(), emitter=emitter)
await agent.ainvoke("hello")
for e in trace.events:
    print(e.type, e.node_id, getattr(e, "duration_ms", None))
```

### 4.4 Budgets (opt-in caps)
```python
from choreoai.core import BudgetMiddleware, InMemoryRunContext
from choreoai.core.middleware_impl import OnionMiddlewareStack
from choreoai.reliability import InMemoryBudget, BudgetDimensions

budget = InMemoryBudget(caps={BudgetDimensions.STEPS.value: 20})
ctx = InMemoryRunContext()

async def node(value):                      # terminal node = the agent
    return await agent.ainvoke(value)

stack = OnionMiddlewareStack([BudgetMiddleware(budget)])   # default consumes {steps: 1}
run = stack.wrap_with_context(node, context=ctx)
result = await run("do the thing")          # raises BudgetExhausted when a cap is hit
```

### 4.5 Orchestration (compose agents)
```python
from choreoai.orchestrate import sequence, parallel

pipeline = sequence(researcher, synthesizer)          # left → right, threads context
result   = await pipeline.ainvoke("Compare vector DBs")

fanned   = parallel(a=researcher_a, b=researcher_b)    # concurrent branches → dict
```

### 4.6 Durable plan on LangGraph (resume-safe)  — needs `choreoai[langgraph]`
```python
from choreoai.core import TraceMiddleware
from choreoai.engine.langgraph_engine import compile_plan, arun_plan

graph = compile_plan(
    steps=[("research", researcher), ("write", writer)],
    middleware=[BudgetMiddleware(budget), TraceMiddleware(emitter)],  # wraps each node
)
state = await arun_plan(graph, "Write a brief on X", run_context=ctx, thread_id="run-1")
print(state["output"])
```

### 4.7 Custom node (full control) — implement the Runnable interface
```python
from langchain_core.runnables import Runnable

class Classifier(Runnable):
    async def ainvoke(self, input, config=None, **kw):
        return {"label": "urgent" if "now" in str(input) else "normal"}

pipeline = sequence(Classifier(), agent)   # drops straight into ChoreoAI combinators
```

### 4.8 Bring-your-own model / provider
```python
# Any langchain_core BaseChatModel works (OpenAI, local, etc.).
from langchain_openai import ChatOpenAI
agent = LLMAgent(instructions="…", model=ChatOpenAI(model="gpt-4o"))
```

---

## 5. Defaults & configuration

**Principle (ADR 0001):** sensible defaults out of the box; override via (a) constructor params,
(b) injected policy objects implementing an interface, or (c) your own `Runnable`.

### 5.1 Current defaults
| Setting | Default | Override |
|---|---|---|
| `LLMAgent.max_steps` | `10` | `max_steps=` param |
| `LLMAgent.emitter` | `SimpleEventEmitter()` | pass `emitter=` |
| `LLMAgent.context` | new `InMemoryRunContext` per run | pass `context=` / `run_context` in input |
| `LLMAgent.model` | **required** (raises if `None`) | pass any `BaseChatModel` |
| Default model | `claude-sonnet-5` | `get_default_model("…")` or BYO model |
| Budget | none ⇒ **unlimited** (opt-in) | attach `Budget` + `BudgetMiddleware` |
| `BudgetMiddleware.amounts` | `{steps: 1}` per node call | pass `amounts=` |

### 5.2 PROPOSED defaults (for discussion)
- **Retries:** *none today* — a single model call; on error the loop raises. **Propose a default
  `max_retries = 3`** (configurable, e.g. 3–5) with exponential backoff on **transient** LLM errors
  (429 / 5xx / timeout / connection). Override via:
  - simple: `LLMAgent(..., retries=5)` (or `retry_on=(...)`, `backoff=...`), **or**
  - policy: inject a `RecoveryPolicy` (the interface already exists — `RETRY_WITH_FEEDBACK` +
    `max_attempts`) for retry-with-feedback / replan / fallback / escalate / abort.
  Ship one concrete default policy (e.g. `SimpleRetryPolicy(max_attempts=3)`).
- **Timeouts:** default per-call timeout (e.g. 60s) → maps to `wall_time_ms` budget dimension.
- **Tool output cap:** default max tool-result size (truncate + note), configurable per tool.
- **Model params:** default `max_tokens` / `temperature` passthrough to the model factory.
- **Budget caps:** stay opt-in, but offer a `default_budget()` helper with sane caps for demos.

Override mechanisms across the framework are uniform: **params** (quick), **injected policy
classes** (`Budget`, `RecoveryPolicy`, `Guardrail`, `EventEmitter`), or a **custom `Runnable`**.

---

## 6. Cost & budget design (OPEN — main discussion topic)

**Question:** where does the cost value come from, and how do we handle "no budget"?

- **No budget = no enforcement.** A dimension with no cap is unlimited (`check` skips it); with no
  `Budget`/middleware attached, nothing is tracked. Budgets are opt-in by design (ADR 0004).
- **Cost today = not computed.** `BudgetDimensions` defines `tokens` and `cost_usd`, and the
  `LLMCalled` event *has* `input_tokens` / `output_tokens` fields — but `LLMAgent` never fills them,
  `BudgetMiddleware` consumes a static `{steps: 1}`, and there is **no pricing table**. So
  `cost_usd` is a defined-but-unpopulated dimension.
- **Where cost SHOULD come from (proposal):**
  1. **Tokens** are provider-agnostic and already on the response — read LangChain's normalized
     `AIMessage.usage_metadata` (`input_tokens` / `output_tokens` / `total_tokens`). We do **not**
     parse Anthropic's raw JSON ourselves; `usage_metadata` works for any provider / BYO
     `BaseChatModel` that populates it (langchain-anthropic does).
  2. **Dollars** are *not* returned by the API (only token counts). Compute
     `cost_usd = input_tokens·price_in + output_tokens·price_out` from a **pricing table we
     maintain**, keyed by model id. Unknown / BYO model ⇒ we can't price ⇒ track **tokens only**,
     leave `cost_usd` uncapped.
  3. **Wiring:** in the agent loop, after each model call, extract usage → populate
     `LLMCalled.input_tokens/output_tokens` → `budget.consume({tokens, cost_usd, llm_calls})`.
- **Subtlety to decide:** `BudgetMiddleware` currently wraps the *whole agent as one node* (1 step).
  The agent's internal tool loop makes several model calls, so **token/cost enforcement must happen
  inside the loop** (or via a cost-aware middleware/emitter subscriber), not just around it.
- **Proposed shape:** a `PricingTable` (model_id → (in, out) $/1M tokens) + a `CostMeter`
  subscriber/middleware that turns `LLMCalled` token counts into `tokens`/`cost_usd` consumption on
  the active `Budget`. Keeps the agent loop clean and works for any provider.

---

## 7. Gaps & open questions (for tomorrow)

1. **Cost/token accounting** — implement usage extraction → events → budget + a pricing table
   (§6). Decide: in-loop vs subscriber; how to maintain prices; behavior for unpriced models.
2. **Retry/recovery** — no concrete `RecoveryPolicy`, not wired. Decide default `max_retries`
   (3?), which errors are retryable, backoff, and the override surface (§5.2).
3. **Guardrails** — `Guardrail` interface exists but `LLMAgent` never calls it. Where do
   input/output/grounding checks run in the loop, and how do they hand off to recovery?
4. **Budget granularity** — per-node (today) vs per-LLM-call vs per-tool. Tied to §6.
5. **Streaming** — `LLMAgent` implements `invoke`/`ainvoke` only; add `stream`/`astream` for
   token streaming (the CLI would use it).
6. **Public API ergonomics** — the current README/quickstart used a *fictional* `BaseAgent`/
   `Orchestrator`; confirm the real composition-first surface is the one we document/teach.
7. **Evals harness** — subscriber-based scoring/regression (roadmap).

---

## 8. Appendix — real public API surface
```
choreoai.agents        LLMAgent
choreoai.models        get_default_model, DEFAULT_MODEL_ID, FLAGSHIP_MODEL_ID
choreoai.core          SimpleEventEmitter, ListSubscriber, Subscriber, EventEmitter,
                       Event, RunStarted, RunFinished, LLMCalled, ToolCalled, StepFinished,
                       GuardrailTripped, Middleware, MiddlewareStack, OnionMiddlewareStack,
                       BudgetMiddleware, TraceMiddleware, Guardrail, GuardrailResult,
                       GuardrailStage, RunContext, InMemoryRunContext
choreoai.reliability   Budget, InMemoryBudget, BudgetDimensions, BudgetSnapshot,
                       BudgetDecision, BudgetExhausted, RecoveryPolicy, RecoveryAction,
                       RecoveryContext, RecoveryDecision
choreoai.orchestrate   sequence, parallel
choreoai.engine        compile_plan, arun_plan   (needs choreoai[langgraph])
```
