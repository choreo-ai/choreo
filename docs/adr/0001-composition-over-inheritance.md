# ADR 0001: Composition over inheritance

## Status

Accepted (locked).

## Context

Multi-agent frameworks often ship a deep `BaseAgent` hierarchy where production concerns
(retry, budget, logging) are hooks or overridden methods. That forces users to subclass to
customize behavior, couples concerns to the agent lifecycle, and makes third-party nodes
second-class.

## Decision

Agent variation is **configuration and composition**, not subclassing:

- Prompt, tools, model, and policies are injected parameters.
- Full custom behavior = implement the node interface (an LCEL `Runnable`).
- Narrow tweaks = injected strategy or event hook / middleware.

We will not ship a template-method `BaseAgent` hierarchy.

## Consequences

- Positive: users keep their own agent shapes; ChoreoAI concerns wrap from the outside.
- Positive: testing is easier (swap one policy or middleware at a time).
- Negative: less "one base class to learn"; docs must show composition patterns clearly.
- Follow-on: middleware (ADR 0003) and seam table in DESIGN.md carry customization.
