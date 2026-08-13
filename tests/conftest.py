"""Shared test setup.

Importing `main` constructs nothing that needs the network, but the module reads
CLAUDE_KEY at import time — the fake client stands in for the real one, so a
placeholder is enough to let the import succeed on a machine with no key set.
"""

import os

os.environ.setdefault("CLAUDE_KEY", "placeholder-not-used-by-tests")

import pytest  # noqa: E402  (must come after the env var is in place)


@pytest.fixture
def convo():
    """A conversation with the user's message already appended, ready for run_turn."""
    return [{"role": "user", "content": "hello"}]
