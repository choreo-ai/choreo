---
hide:
  - navigation
  - toc
---

# ChoreoAI

<div class="choreo-landing" markdown>

<div class="choreo-hero" markdown>

<img class="choreo-hero__mark" src="assets/logo.svg" alt="ChoreoAI mark" width="72" height="72">

<p class="choreo-hero__title">ChoreoAI</p>
<p class="choreo-hero__tagline">Multi-agent systems, in production.</p>
<p class="choreo-hero__lead">
Compose, orchestrate, and observe autonomous agents with budgets, guardrails,
retries, and tracing as defaults — not afterthoughts.
</p>

<div class="choreo-hero__install" markdown>
<span class="prompt">$</span> <code>pip install choreoai</code>
</div>

</div>

Most agent frameworks make the happy path easy and leave you to discover the hard parts —
hallucinations, runaway loops, lost state, unbounded cost — in incident review. ChoreoAI
makes those the *default* things you control.

## Explore

<div class="grid cards" markdown>

-   :material-book-open-variant: **[Design](DESIGN.md)**

    Architecture, principles, and how the production layer sits on LangGraph.

-   :material-api: **[API reference](reference/choreoai/index.md)**

    Auto-generated from source — every public module, class, and function.

-   :material-file-tree: **[Architecture decisions](adr/0001-composition-over-inheritance.md)**

    ADRs that record *why* the framework is shaped the way it is.

</div>

## What you get

<ul class="choreo-features">
  <li>
    <span class="feat-icon" aria-hidden="true">◎</span>
    <div>
      <strong>Reliability</strong>
      <span>Budgets, retries, and recovery as first-class controls on every run.</span>
    </div>
  </li>
  <li>
    <span class="feat-icon" aria-hidden="true">▣</span>
    <div>
      <strong>Guardrails</strong>
      <span>Middleware onion that validates inputs, outputs, and side effects.</span>
    </div>
  </li>
  <li>
    <span class="feat-icon" aria-hidden="true">⇄</span>
    <div>
      <strong>Orchestration</strong>
      <span>Compose agents with combinators — plan, parallel workers, reduce, review.</span>
    </div>
  </li>
  <li>
    <span class="feat-icon" aria-hidden="true">◇</span>
    <div>
      <strong>Evals</strong>
      <span>Typed event streams ready for scoring, regression, and offline analysis.</span>
    </div>
  </li>
  <li>
    <span class="feat-icon" aria-hidden="true">◉</span>
    <div>
      <strong>Observability</strong>
      <span>Traces and metrics without rewriting tools, models, or graphs.</span>
    </div>
  </li>
</ul>

## Quickstart

```python
from choreoai import BaseAgent, Orchestrator, budget

class Researcher(BaseAgent):
    system = "Find and summarize sources for the given topic."
    tools = [web_search]

fleet = Orchestrator(
    plan=Planner(),
    workers=[Researcher(), Researcher()],   # run in parallel
    reduce=Synthesizer(),
    review=Critic(),                         # gates the final answer
    budget=budget(steps=20, usd=0.50),       # hard cap on every run
)

result = fleet.run("Compare vector databases for RAG")
```

---

*API reference pages are generated from docstrings on every push to `main`.
If a page looks thin, improve the source docstring — not a hand-written doc page.*

</div>
