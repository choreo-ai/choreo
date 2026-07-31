# Getting started

Install ChoreoAI, run your first agent, add a tool, and watch the typed event stream.

## Install

```bash
pip install choreoai
```

For durable multi-node plans on LangGraph (compile, checkpoint, resume), install the engine extra:

```bash
pip install "choreoai[langgraph]"
```

## Prerequisites

Live runs with the default Claude model need an Anthropic API key:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

On Windows (PowerShell):

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
```

The default model factory is `get_default_model()` → Claude Sonnet (`claude-sonnet-5`). Any LangChain `BaseChatModel` works if you pass it as `model=`. Offline tests in this repo use a fake model; you do not need a key for the test suite.

## Your first agent

`LLMAgent` is a LangChain `Runnable`. Give it instructions and a model, then `ainvoke`:

```python
import asyncio

from choreoai.agents import LLMAgent
from choreoai.models import get_default_model

agent = LLMAgent(
    instructions="You are concise.",
    model=get_default_model(),
)

async def main() -> None:
    result = await agent.ainvoke("Summarize LangGraph in one sentence.")
    print(result)

asyncio.run(main())
```

## Add a tool

Pass LangChain tools (including `@tool` functions) via `tools=`. The agent binds them and runs a tool loop up to `max_steps`:

```python
import asyncio

from langchain_core.tools import tool

from choreoai.agents import LLMAgent
from choreoai.models import get_default_model


@tool
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b


agent = LLMAgent(
    name="calculator",
    instructions="Use tools when helpful.",
    tools=[add],
    model=get_default_model(),
    max_steps=6,
)

async def main() -> None:
    print(await agent.ainvoke("What is 17 + 25?"))

asyncio.run(main())
```

## See what it's doing

Subscribe to the typed event stream with `SimpleEventEmitter` and `ListSubscriber`. Pass the same emitter into the agent:

```python
import asyncio

from langchain_core.tools import tool

from choreoai.agents import LLMAgent
from choreoai.core import ListSubscriber, SimpleEventEmitter
from choreoai.models import get_default_model


@tool
def note(text: str) -> str:
    """Record a short research note."""
    return f"noted: {text}"


emitter = SimpleEventEmitter()
subscriber = ListSubscriber(name="trace")
emitter.subscribe(subscriber)

agent = LLMAgent(
    name="researcher",
    instructions="Research briefly. Use the note tool if helpful.",
    tools=[note],
    model=get_default_model(),
    max_steps=4,
    emitter=emitter,
)

async def main() -> None:
    result = await agent.ainvoke("What is LangGraph in one paragraph?")
    print(result)
    print(f"{len(subscriber.events)} events traced")
    for event in subscriber.events:
        print(f"  [{event.seq}] {event.type} node={event.node_id}")

asyncio.run(main())
```

Typical events in a run: `RunStarted` → `LLMCalled` → `ToolCalled` → `StepFinished` → `RunFinished`.

## Next steps

- [Design](DESIGN.md) — principles, module layout, and how the production layer sits on LangGraph
- [API reference](reference/index.md) — auto-generated from source for every public module
- [Architecture ADRs](adr/0001-composition-over-inheritance.md) — composition, LCEL nodes, middleware, LangGraph
- Full demo: [`examples/research_pipeline.py`](https://github.com/choreo-ai/choreoai/blob/main/examples/research_pipeline.py) (two-agent sequence with budgets and traces)
