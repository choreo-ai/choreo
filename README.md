<p align="center">
  <img src="assets/banner-choreoai.png?v=2" alt="ChoreoAI — Multi-agent systems, in production." width="840">
</p>

<p align="center">
  <img src="assets/logo.svg" alt="ChoreoAI" width="72">
</p>

<p align="center">
  <strong>Build production-grade multi-agent AI systems.</strong><br>
  Compose, orchestrate, and observe autonomous agents &mdash; reliably.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/status-pre--alpha-C06B4E?style=flat-square" alt="status: pre-alpha">
  <img src="https://img.shields.io/badge/python-3.10%2B-33302B?style=flat-square" alt="python 3.10+">
  <img src="https://img.shields.io/badge/license-MIT-A8583D?style=flat-square" alt="license: MIT">
  <img src="https://img.shields.io/badge/PRs-welcome-A8583D?style=flat-square" alt="PRs welcome">
  <a href="https://pypi.org/project/choreoai/"><img src="https://img.shields.io/pypi/v/choreoai?style=flat-square&color=A8583D" alt="PyPI"></a>
</p>

---

**ChoreoAI** is an open-source framework for building **multi-agent AI systems that survive
production**. Most agent frameworks make the happy path easy and leave you to discover the
hard parts &mdash; hallucinations, runaway loops, lost state, unbounded cost &mdash; in
incident review. ChoreoAI makes those the *default* things you control: retries, guardrails,
budgets, evals, and tracing are first-class, not add-ons.

Think of it as the layer between "a clever prompt" and "a system you can put on-call."

> **Status: pre-alpha, building in public.** The APIs shown below are the target developer
> experience and are still landing &mdash; follow the [roadmap](#roadmap). ⭐ Star the repo to
> track progress; issues and PRs are welcome.

## Why ChoreoAI

- **Reliability is the product.** Every run is bounded by step, token, time, and cost budgets.
  Nothing loops forever; nothing surprises your bill.
- **Guardrails against bad states.** Output/schema validation and grounding checks catch
  hallucinations before they propagate, with defined recovery paths (retry / replan / fall
  back / escalate).
- **One base agent, thin subclasses.** Cross-cutting concerns (LLM client, tool loop, retries,
  context assembly, tracing) live once in `BaseAgent`; your agents override only what's unique.
- **Orchestration built in.** Sequence, parallelize, or supervise workers &mdash; with shared
  state threaded cleanly through the run.
- **Evals as a gate, not an afterthought.** Per-agent, per-tool, and end-to-end checks so a
  prompt or model change can't silently regress.
- **Observable by default.** Full traces across agents and tool calls, plus metrics: latency,
  cost, retry rate, guardrail-trip rate, task success.

## Install

```bash
# From PyPI
pip install choreoai

# From source
pip install git+https://github.com/choreo-ai/choreoai
```

```bash
choreoai            # confirm the install
```

## Quickstart

> Illustrative &mdash; this is the API ChoreoAI is being designed around.

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

## Roadmap

- [ ] **Core** &mdash; `BaseAgent`, tool loop, retries, tracing.
- [ ] **Orchestration** &mdash; planner + workers + synthesizer on a real research-assistant task.
- [ ] **Reliability** &mdash; budgets, guardrails, grounding checks, recovery paths.
- [ ] **Evals & observability** &mdash; eval harness, a critic agent, full-run traces.
- [ ] **`choreoai` CLI** &mdash; `init`, `run`, `trace`.
- [x] **First releases on PyPI** &mdash; `choreoai` on pypi.org; snapshots on TestPyPI.

## Contributing

ChoreoAI is open source (MIT) and early &mdash; the best time to shape it. Bug reports, ideas,
and PRs are all welcome. Open an [issue](https://github.com/choreo-ai/choreoai/issues) to
discuss a change before large PRs. Dev setup:

```bash
git clone https://github.com/choreo-ai/choreoai
cd choreoai
pip install -e ".[dev]"
pytest
```

## License

[MIT](LICENSE) &copy; 2026 Karthik Reddy Basupally

<br>

<p align="center">
  <img src="assets/logo.svg" alt="ChoreoAI" width="36"><br>
  <sub><strong>ChoreoAI</strong> &middot; multi-agent systems, in production &middot;
  <a href="https://github.com/choreo-ai/choreoai">github.com/choreo-ai/choreoai</a></sub>
</p>
