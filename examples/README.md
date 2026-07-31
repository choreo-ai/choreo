# Examples

## research_pipeline.py

Thin vertical-slice demo: researcher + synthesizer agents, budget middleware,
and a trace subscriber. Uses the real default model (`claude-sonnet-5`) and
requires `ANTHROPIC_API_KEY`. Not run under pytest.

```text
set ANTHROPIC_API_KEY=...
python examples/research_pipeline.py "What is LangGraph?"
```
