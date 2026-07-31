<p align="center">
  <img src="assets/logo.svg" alt="Choreo" width="88" height="88">
</p>

<h1 align="center">Choreo</h1>

<p align="center">
  <strong>Multi-agent systems, in production.</strong><br>
  Compose, orchestrate, and observe autonomous AI agents &mdash; reliably.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/status-early--stage-C06B4E?style=flat-square" alt="status: early-stage">
  <img src="https://img.shields.io/badge/python-3.10%2B-33302B?style=flat-square" alt="python 3.10+">
  <img src="https://img.shields.io/badge/license-MIT-A8583D?style=flat-square" alt="license: MIT">
</p>

---

**Choreo** is an open-source framework for building **production-grade multi-agent AI
systems** &mdash; a peer of LangChain, LangGraph, and CrewAI, focused on the part they gloss
over: **reliability**. Retries, guardrails, budgets, evals, and observability are
first-class here, not bolted on afterward.

> **Status:** early-stage, building in public. The developer experience shown below is the
> **target API and is still being designed** &mdash; see the [Roadmap](#roadmap). Nothing is
> published to PyPI yet.

> Name note: *Choreo* nods to **orchestration vs. choreography** in distributed systems &mdash;
> agent coordination is a distributed-systems problem, not just prompting.

---

## Why Choreo

A single LLM call is easy. A *reliable* multi-agent system is hard, and most teams skip the
hard part. Agent demos that shine in a notebook fall over in production because they:

- **hallucinate** and act on made-up facts,
- **loop forever** or wander off task with no budget,
- **lose state** as work passes between steps,
- cost **unpredictably**, and
- can't be **debugged** &mdash; non-deterministic, untraced, no evals.

Choreo is the framework that makes those failure modes the *default* things you handle, not
the things you discover in incident review.

## Planned developer experience

> Illustrative &mdash; this is the API we're designing toward, not a shipped interface.

```bash
pip install choreo
choreo init my-fleet
```

```python
from choreo import BaseAgent, Orchestrator, budget

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

## What's in the box

- **`BaseAgent` template** &mdash; owns the cross-cutting concerns once (LLM client, tool loop,
  retry policy, context assembly, output validation, budgets, tracing). Concrete agents
  override only prompt, tools, and success criteria.
- **Orchestrator** &mdash; routes and delegates across agents; sequential, parallel, or
  supervisor-over-workers.
- **Shared state** &mdash; one state object threads through a run, instead of ad-hoc message passing.
- **Reliability layer** &mdash; retries with backoff, schema/grounding validation,
  step/token/time/cost budgets, and defined recovery paths (abort / replan / fall back / escalate).
- **Eval harness** &mdash; per-agent, per-tool, and end-to-end task success; changes are gated by evals.
- **Observability** &mdash; tracing across agents and tool calls (spans, correlation IDs) plus
  metrics: latency, cost, retry rate, guardrail-trip rate, success rate.

## Design principles

- **Base agent, thin subclasses.** Cross-cutting concerns live once.
- **Every agent has a budget.** Steps, tokens, time, cost &mdash; all capped.
- **Fail loud, recover deliberately.** No silent bad states; every failure has a defined path.
- **Evals gate changes.** Nothing ships without passing the eval set.
- **Observable by default.** If you can't trace it, you can't debug a non-deterministic system.

## Roadmap

1. **Base + one agent** &mdash; `BaseAgent`, a single working agent, tool loop, tracing.
2. **Orchestration** &mdash; planner + workers + synthesizer on a real research-assistant task.
3. **Reliability** &mdash; retries, guardrails, budgets, recovery paths.
4. **Evals & observability** &mdash; eval harness + a critic agent + full-run tracing.

Open decisions being worked through: orchestration engine (hand-rolled vs. LangGraph), where
smaller/faster models fit, in-memory vs. persistent state for resumable runs, and where
human-in-the-loop escalation happens.

## Brand

Design system lives in [`assets/`](assets/). Full board: [`assets/brand-system.png`](assets/brand-system.png).

| Token | Value | Use |
|-------|-------|-----|
| Terracotta | `#C06B4E` | primary / mark |
| Deep | `#A8583D` | accents |
| Ink | `#33302B` | text, dark surfaces |
| Sand | `#F1EBE0` | background |
| Space Grotesk | &mdash; | wordmark / display |
| JetBrains Mono | &mdash; | code |

Logo: `assets/logo.svg` (mark) &middot; `assets/icon.svg` (app icon). The mark is three agents
&mdash; two workers and an apex &mdash; joined by a single choreographed arc.

## License

[MIT](LICENSE) &copy; 2026 Karthik Reddy Basupally
