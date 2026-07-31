# Substrate API verification

Verified against live LangChain / Anthropic docs (2026-07-31). Do not re-code from memory;
re-check before implementation if versions have moved.

## `langchain_core.tools.BaseTool`

- **Package / import:** `langchain_core.tools.BaseTool`
- **Identity:** Abstract base for all LangChain tools; itself a `RunnableSerializable`.
- **Key properties:** `name`, `description`, `args_schema`, `return_direct`, `verbose`,
  `callbacks`, `tags`, `metadata`, `handle_tool_error`, `handle_validation_error`,
  `response_format`, `extras`, `args`, `tool_call_schema`, `is_single_input`.
- **Call surface:** `invoke` / `ainvoke` (Runnable), plus `run` / `arun`.
- **Subclass pattern:** implement sync `_run` and optionally async `_arun` (historic
  convention still used by custom tools); public entry is via `invoke`/`ainvoke`.
- **Convenience:** `@tool` decorator and `StructuredTool` produce `BaseTool` instances.
- **ChoreoAI implication:** accept any `BaseTool`; `@choreoai.tool` is a thin convenience that
  yields a `BaseTool`. Do not invent a parallel tool type.

## `langchain_core.language_models.BaseChatModel`

- **Package / import:** `langchain_core.language_models.BaseChatModel`
- **Identity:** Base for chat models; extends `BaseLanguageModel[AIMessage]`.
- **Imperative methods:** `invoke` / `ainvoke` (input: str | messages | PromptValue ->
  `BaseMessage`), `stream` / `astream` (chunks), `batch` / `abatch`, `astream_events`.
- **Declarative methods:** `bind_tools`, `with_structured_output`, `with_retry`,
  `with_fallbacks`, `configurable_fields`, `configurable_alternatives`.
- **Custom model hooks:** required `_generate` + `_llm_type`; optional `_stream`,
  `_agenerate`, `_astream`.
- **ChoreoAI implication:** agents take a `BaseChatModel`; tool loop uses `bind_tools` and
  inspects `AIMessage.tool_calls`. Default client is Anthropic via `langchain-anthropic`.

## `langchain_core.runnables.Runnable`

- **Package / import:** `langchain_core.runnables.Runnable` (also `RunnableSerializable`,
  `RunnableSequence`, `RunnableParallel`, `RunnableLambda`, `RunnableConfig`).
- **Contract:** `invoke`/`ainvoke`, `batch`/`abatch`, `stream`/`astream`, plus
  `astream_events` / `stream_events`. Optional `config: RunnableConfig` on all calls.
- **Composition:** `|` builds `RunnableSequence`; dict literals build `RunnableParallel`.
- **Standard modifiers:** `with_retry`, `with_fallbacks`, `with_config`, `with_listeners`,
  `bind`, `pipe`, `as_tool`.
- **Schemas:** `input_schema` / `output_schema` / `config_schema`.
- **ChoreoAI implication:** a ChoreoAI agent/node **is** an LCEL `Runnable`. We re-export or
  alias; we do not define a competing node ABC. Middleware wraps a Runnable and returns a
  Runnable.

## LangGraph engine

- **Core graph API:** `langgraph.graph.StateGraph`, `START`, `END`.
  - `add_node(name, fn | Runnable)`, `add_edge`, `add_conditional_edges`.
  - Compile with `.compile(checkpointer=..., store=...)`.
- **State:** `TypedDict` / dataclass / Pydantic; per-key reducers via
  `Annotated[T, reducer]`. Messages channel typically uses `add_messages`.
- **Nodes:** sync or async callables `(state) -> partial update`, optionally taking
  `config: RunnableConfig` and/or `runtime`. Functions become `RunnableLambda` under the
  hood.
- **Checkpointers (short-term / thread memory):**
  - In-memory: `langgraph.checkpoint.memory.InMemorySaver` (docs also refer to
    `MemorySaver` in examples; prefer the documented in-memory saver for new code).
  - Persistent: `SqliteSaver`, `PostgresSaver` (separate packages for production).
- **HITL:** `langgraph.types.interrupt(value)` pauses; resume with
  `Command(resume=value)`. Requires a checkpointer + `thread_id` in config.
- **Streaming:** `graph.stream` / `stream_events(..., version="v3")`; interrupts surface
  via stream metadata / `__interrupt__`.
- **ChoreoAI implication:** engine compiles our plan to `StateGraph`; middleware wraps each
  node *before* it is added so budgets/guardrails/traces apply uniformly. `RunContext`
  (budget ledger + event cursor) lives in graph state so it survives checkpoint/resume.

## Default model: `langchain-anthropic.ChatAnthropic`

- **Import:** `from langchain_anthropic import ChatAnthropic`
- **Is a:** `BaseChatModel` (drop-in for ChoreoAI agent config).
- **Construction:** `ChatAnthropic(model="...", temperature=..., max_tokens=..., ...)`.
- **Tools:** `model.bind_tools([...], strict=True optional)`; responses expose
  `tool_calls` and content blocks.
- **Async / stream:** full `ainvoke`, `astream`, `astream_events` support.
- **Current model IDs (verified against the Claude platform, 2026):**
  - Flagship / most capable: `claude-opus-4-8` (Opus 4.8).
  - Balanced (**ChoreoAI default**): `claude-sonnet-5`.
  - Fast / cheap: `claude-haiku-4-5-20251001` (alias `claude-haiku-4-5`).
  - Also in the Claude 5 family: `claude-fable-5`.
  - NOTE: there is **no** `claude-opus-5`. The flagship Opus id is `claude-opus-4-8`.
- **Docs note:** ChoreoAI defaults to `claude-sonnet-5` (sane cost/latency for running many
  agents, consistent with the budgets pitch), with `claude-opus-4-8` documented for maximum
  capability. Always user-overridable.

## Packaging anchors

| Extra | Purpose |
|---|---|
| (core) | `langchain-core` + default Anthropic client (`langchain-anthropic`) |
| `choreoai[langgraph]` | LangGraph engine |
| `choreoai[langchain]` | heavier LangChain adapters |

Core modules must not import the heavy `langchain` meta-package; only `langchain-core`.
`engine/` and `integrations/` are the only places `langgraph` / heavier `langchain` appear.
