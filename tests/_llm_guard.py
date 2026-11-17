"""Shared guard for live-LLM tests.

Unique module name on purpose: ``conftest`` collides across test subdirs under
pytest's prepend import mode, so a shared helper must not live there.
"""

import os

import pytest

# Live-LLM tests hit real provider APIs. In keyless CI (e.g. forks without
# secrets) they must skip explicitly instead of failing with 401/connection
# errors. Unit tests never carry this marker and always run.
requires_llm = pytest.mark.skipif(
    not (os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")),
    reason="live-LLM test: no OPENAI_API_KEY/ANTHROPIC_API_KEY in environment",
)
