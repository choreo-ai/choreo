# ChoreoAI

<p align="center">
  <img src="assets/logo.svg" alt="ChoreoAI" width="88">
</p>

**Build production-grade multi-agent AI systems — compose, orchestrate, and observe
autonomous agents, reliably.**

Most agent frameworks make the happy path easy and leave you to discover the hard parts —
hallucinations, runaway loops, lost state, unbounded cost — in incident review. ChoreoAI
makes those the *default* things you control: retries, guardrails, budgets, evals, and
tracing are first-class, not add-ons.

!!! note "Status: pre-alpha, building in public"
    The APIs shown here are the target developer experience and are still landing.
    Follow the [roadmap](https://github.com/choreo-ai/choreoai#roadmap) — issues and PRs welcome.

## Install

```bash
pip install choreoai
```

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

## Where to next

<div class="grid cards" markdown>

-   :material-book-open-variant: **[Design](DESIGN.md)**

    The architecture and the principles behind it.

-   :material-api: **[API reference](reference/)**

    Auto-generated from the source — every module, class, and function.

-   :material-file-tree: **[Architecture decisions](adr/0001-composition-over-inheritance.md)**

    The ADRs recording why the framework is shaped the way it is.

</div>

---

*This reference is generated automatically from the code's docstrings on every push to
`main`. If a page looks thin, the fix is a better docstring in the source — not a doc edit.*
