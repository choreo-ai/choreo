---
hide:
  - navigation
  - toc
---

# ChoreoAI

<div class="choreo-landing" markdown>

<div class="choreo-hero" markdown>

<img class="choreo-hero__mark" src="assets/logo.svg" alt="ChoreoAI mark" width="64" height="64">

<p class="choreo-hero__title">ChoreoAI</p>
<p class="choreo-hero__tagline">Multi-agent systems, in production.</p>
<p class="choreo-hero__lead">
The production layer for LangGraph — compose agents, cap cost and steps,
and stream typed events for traces and evals. Reliability is built in,
not bolted on.
</p>

<p class="choreo-hero__actions">
<a href="DESIGN.md" class="md-button md-button--primary">Get started</a>
<a href="https://github.com/choreo-ai/choreoai" class="md-button choreo-button--ghost">View on GitHub</a>
</p>

<div class="choreo-install" role="group" aria-label="Install command">
  <span class="choreo-install__prompt" aria-hidden="true">$</span>
  <code class="choreo-install__cmd" id="choreo-install-cmd">pip install choreoai</code>
  <button type="button" class="choreo-install__copy" data-clipboard-target="#choreo-install-cmd" title="Copy install command" aria-label="Copy install command">
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
  </button>
</div>

</div>

Most agent frameworks make the happy path easy and leave you to discover the hard
parts — hallucinations, runaway loops, lost state, unbounded cost — in incident
review. ChoreoAI treats those as **default controls**: budgets, middleware
guardrails, typed event streams, and composition combinators on top of LangChain
and LangGraph — without rewriting your tools or models.

## Why ChoreoAI

<div class="choreo-why" markdown>

<div class="choreo-why__item" markdown>
<p class="choreo-why__label">Production defaults</p>
<p class="choreo-why__text">Budgets, traces, and recovery are first-class — not a checklist you rebuild after the first outage.</p>
</div>

<div class="choreo-why__item" markdown>
<p class="choreo-why__label">Zero rewrite</p>
<p class="choreo-why__text">Keep LangChain tools, chat models, and LCEL runnables. Opt into ChoreoAI only where you need control.</p>
</div>

<div class="choreo-why__item" markdown>
<p class="choreo-why__label">LangGraph-native</p>
<p class="choreo-why__text">State, checkpoints, and streaming stay on LangGraph. ChoreoAI is the reliability and observability layer above it.</p>
</div>

</div>

## What you get

<div class="choreo-features" markdown>

<div class="choreo-feature" markdown>
<p class="choreo-feature__title">Reliability</p>
<p class="choreo-feature__body">Hard caps on steps, tokens, and cost via <code>InMemoryBudget</code> and <code>BudgetMiddleware</code>. Recovery policies decide what happens when a budget or guardrail trips — fail closed, retry, or hand off.</p>
</div>

<div class="choreo-feature" markdown>
<p class="choreo-feature__title">Guardrails</p>
<p class="choreo-feature__body">A middleware onion wraps every node. Validate inputs and outputs, enforce side-effect policy, and stack concerns without subclassing agents or forking the graph.</p>
</div>

<div class="choreo-feature" markdown>
<p class="choreo-feature__title">Orchestration</p>
<p class="choreo-feature__body">Compose agents with <code>sequence</code> and <code>parallel</code> combinators over LCEL runnables. Build plan → workers → reduce → review pipelines as plain composition, not a rigid base class.</p>
</div>

<div class="choreo-feature" markdown>
<p class="choreo-feature__title">Observability</p>
<p class="choreo-feature__body">Typed event stream (<code>RunStarted</code>, <code>LLMCalled</code>, <code>ToolCalled</code>, …) via <code>SimpleEventEmitter</code> and subscribers. Wire traces and metrics without instrumenting each tool by hand.</p>
</div>

<div class="choreo-feature" markdown>
<p class="choreo-feature__title">Evals-ready</p>
<p class="choreo-feature__body">The same event contract feeds offline scoring and regression. Capture runs with a <code>ListSubscriber</code>, replay later — no parallel logging format to invent.</p>
</div>

<div class="choreo-feature" markdown>
<p class="choreo-feature__title">Run context</p>
<p class="choreo-feature__body"><code>InMemoryRunContext</code> carries budget ledgers and event sequence through the graph so resume and multi-node runs stay consistent with the same control plane.</p>
</div>

</div>

## Quickstart

Requires `ANTHROPIC_API_KEY` for live model calls (default model: `claude-sonnet-5`).

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
    model=get_default_model(),  # claude-sonnet-5
    max_steps=4,
    emitter=emitter,
)

async def main() -> None:
    result = await agent.ainvoke("What is LangGraph in one paragraph?")
    print(result)
    print(f"{len(subscriber.events)} events traced")

asyncio.run(main())
```

Compose agents and wrap a run with budget + trace middleware:

```python
from choreoai.core import (
    BudgetMiddleware,
    InMemoryRunContext,
    OnionMiddlewareStack,
    TraceMiddleware,
)
from choreoai.orchestrate import sequence
from choreoai.reliability import InMemoryBudget

model = get_default_model()
researcher = LLMAgent(
    name="researcher",
    instructions="Gather key facts briefly.",
    tools=[note],
    model=model,
    max_steps=4,
    emitter=emitter,
)
synthesizer = LLMAgent(
    name="synthesizer",
    instructions="Summarize the research in a short paragraph.",
    tools=[],
    model=model,
    max_steps=2,
    emitter=emitter,
)

pipeline = sequence(researcher, synthesizer, name="research_pipeline")
budget = InMemoryBudget(caps={"steps": 10})
context = InMemoryRunContext(
    budget_ledger={"caps": {"steps": 10}, "consumed": {}, "labels": {}}
)

async def run_pipeline(value: object) -> object:
    return await pipeline.ainvoke({"value": value, "run_context": context})

stack = OnionMiddlewareStack(
    [
        TraceMiddleware(emitter=emitter, node_id="pipeline"),
        BudgetMiddleware(budget, amounts={"steps": 1}),
    ],
    node=run_pipeline,
)
# result = await stack.ainvoke("Your question", context=context)
```

Full demo: [`examples/research_pipeline.py`](https://github.com/choreo-ai/choreoai/blob/main/examples/research_pipeline.py).

## Next steps

<div class="choreo-next" markdown>

<a class="choreo-next__card" href="DESIGN.md">
<span class="choreo-next__kicker">Architecture</span>
<span class="choreo-next__title">Design</span>
<span class="choreo-next__desc">Principles, module layout, and how the production layer sits on LangGraph.</span>
</a>

<a class="choreo-next__card" href="reference/choreoai/index.md">
<span class="choreo-next__kicker">Reference</span>
<span class="choreo-next__title">API reference</span>
<span class="choreo-next__desc">Auto-generated from source — every public module, class, and function.</span>
</a>

<a class="choreo-next__card" href="adr/0001-composition-over-inheritance.md">
<span class="choreo-next__kicker">Decisions</span>
<span class="choreo-next__title">Architecture ADRs</span>
<span class="choreo-next__desc">Why composition, LCEL nodes, middleware, and LangGraph were locked in.</span>
</a>

</div>

<p class="choreo-footnote">
API reference pages are generated from docstrings on every push to <code>main</code>.
If a page looks thin, improve the source docstring — not a hand-written doc page.
</p>

</div>

<script>
(function () {
  var btn = document.querySelector(".choreo-install__copy");
  if (!btn) return;
  btn.addEventListener("click", function () {
    var el = document.getElementById("choreo-install-cmd");
    var text = el ? el.textContent.trim() : "pip install choreoai";
    var done = function () {
      btn.classList.add("is-copied");
      btn.setAttribute("aria-label", "Copied");
      setTimeout(function () {
        btn.classList.remove("is-copied");
        btn.setAttribute("aria-label", "Copy install command");
      }, 1400);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done).catch(function () {});
    }
  });
})();
</script>
