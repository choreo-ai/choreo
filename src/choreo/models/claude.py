"""Default Claude model factory (langchain-anthropic ChatAnthropic).

Choreo default model id is ``claude-sonnet-5``; flagship option is
``claude-opus-4-8`` (there is no ``claude-opus-5``).
"""

from __future__ import annotations

from typing import Any

from langchain_core.language_models import BaseChatModel

DEFAULT_MODEL_ID = "claude-sonnet-5"
FLAGSHIP_MODEL_ID = "claude-opus-4-8"


def get_default_model(
    model: str | None = None,
    **kwargs: Any,
) -> BaseChatModel:
    """Return a ``ChatAnthropic`` instance typed as ``BaseChatModel``.

    Args:
        model: Anthropic model id. Defaults to ``claude-sonnet-5``.
        **kwargs: Forwarded to ``ChatAnthropic`` (temperature, max_tokens, etc.).

    Returns:
        A ``BaseChatModel`` suitable for ``LLMAgent`` and LCEL pipelines.

    Note:
        Requires ``ANTHROPIC_API_KEY`` in the environment (or credentials passed
        via kwargs) for live calls. Unit tests should inject a fake model instead.
    """
    from langchain_anthropic import ChatAnthropic

    model_id = model if model is not None else DEFAULT_MODEL_ID
    return ChatAnthropic(model=model_id, **kwargs)
