"""Default and optional model factories (BaseChatModel-compatible)."""

from choreo.models.claude import DEFAULT_MODEL_ID, FLAGSHIP_MODEL_ID, get_default_model

__all__ = [
    "DEFAULT_MODEL_ID",
    "FLAGSHIP_MODEL_ID",
    "get_default_model",
]
