"""Model factory tests (no live API calls)."""

from __future__ import annotations

from langchain_core.language_models import BaseChatModel

from choreoai.models.claude import DEFAULT_MODEL_ID, FLAGSHIP_MODEL_ID, get_default_model


def test_default_model_ids():
    assert DEFAULT_MODEL_ID == "claude-sonnet-5"
    assert FLAGSHIP_MODEL_ID == "claude-opus-4-8"


def test_get_default_model_returns_base_chat_model_type():
    # Construct without calling the network; ChatAnthropic init is local.
    model = get_default_model(api_key="sk-test-not-used")
    assert isinstance(model, BaseChatModel)
    # model field on ChatAnthropic
    assert getattr(model, "model", None) == DEFAULT_MODEL_ID


def test_get_default_model_override():
    model = get_default_model(model=FLAGSHIP_MODEL_ID, api_key="sk-test-not-used")
    assert getattr(model, "model", None) == FLAGSHIP_MODEL_ID
