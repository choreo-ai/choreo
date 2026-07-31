# Choreo

A reference **multi-agent system built for production** — and the system-design guide that
explains it. The point isn't a flashy demo; it's demonstrating every reliability concern a
real agentic system has to solve, and being able to explain each one.

> Name note: "Choreo" nods to **orchestration vs. choreography** in distributed systems —
> agent coordination is a distributed-systems problem, not just prompting.

---

## Problem

A single LLM call is easy. A *reliable* multi-agent system is hard, and most teams skip the
hard part. Agent demos that look great in a notebook fall over in production because they:

- **hallucinate** and act on made-up facts,
- **loop forever** or wander off task with no budget,
- **lose state** as work passes between steps,
- cost **unpredictably**, and
- can't be **debugged** — non-deterministic, untraced, no evals.

There's no clean reference for how to structure a multi-agent app so these don't happen.

## Solution

Choreo is that reference: a small but *real* multi-agent application that embodies the
production concerns, plus the written design behind each decision. One concrete task grounds
it — a **research assistant**: a planner delegates to retrieval workers, a synthesizer merges
their findings, and a critic checks the result before it ships.

It answers, in code and in prose:
- how agents are **structured** (a shared base, thin specialized subclasses),
- how they're **orchestrated** and how data flows between them,
- how **context** is engineered per step,
- how **failure** is contained — retries, guardrails, bad-state recovery, budgets,
- how the system is **evaluated** and **observed**.

## How we'll build it (engineering overview)

High-level shape, not deep internals:

- **`BaseAgent` template** — owns the cross-cutting concerns once (LLM client, tool loop,
  retry policy, context assembly, output validation, budgets, tracing). Concrete agents
  override only prompt, tools, and success criteria.
- **Orchestrator** — routes and delegates across agents; decides sequence vs. parallel vs.
  supervisor-over-workers.
- **State** — a shared state object passed through the run (vs. ad-hoc message passing).
- **Reliability layer** — retries with backoff, output/schema validation, grounding checks,
  step/token/time/cost budgets, and defined recovery paths (abort / replan / fall back /
  escalate).
- **Eval harness** — per-agent, per-tool, and end-to-end task success; offline sets + online
  monitoring; changes are gated by evals.
- **Observability** — tracing across agents and tool calls (spans, correlation IDs), plus
  metrics (latency, cost, retry rate, guardrail-trip rate, success rate).

### Build phases
1. **Base + one agent** — `BaseAgent`, a single working agent, tool loop, tracing.
2. **Orchestration** — planner + workers + synthesizer on the research-assistant task.
3. **Reliability** — retries, guardrails, budgets, recovery paths.
4. **Evals & observability** — eval harness + a critic agent + full run tracing.

### Stack (initial)
Python · an orchestration approach (hand-rolled vs. LangGraph — decided and justified) ·
an LLM (default: latest Claude) · an eval harness · tracing. Details firm up as we build.

---

## Design principles (draft)
- **Base agent, thin subclasses.** Cross-cutting concerns live once.
- **Every agent has a budget.** Steps, tokens, time, cost — all capped.
- **Fail loud, recover deliberately.** No silent bad states; every failure has a defined path.
- **Evals gate changes.** Nothing ships without passing the eval set.
- **Observable by default.** If you can't trace it, you can't debug a non-deterministic system.

## Open decisions
- Orchestration framework: hand-rolled vs. LangGraph vs. other.
- Where smaller/faster models fit alongside the default.
- State store: in-memory vs. persistent (resumable runs).
- Human-in-the-loop: where and how escalation happens.

_This README is the living system-design doc. Each section becomes a `/docs` page + a commit._
