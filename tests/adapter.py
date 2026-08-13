"""The single point where the test suite binds to your implementation.

The tests pin BEHAVIOUR, not naming. The contract is:

    run_turn(client, messages, tools) -> messages

  * `messages` already ends with the new user message — run_turn never calls input()
  * it loops until Claude stops asking for tools
  * it returns the updated history (mutating in place and returning None is fine
    too; `drive` below accepts either)

Renamed it, or changed the signature? Change it here and nowhere else.
"""

from tools.index import TOOLS

try:
    from main import run_turn
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "These tests expect main.run_turn(client, messages, tools).\n"
        "It doesn't exist yet — that's step 4 in LEARNING.md, and it's yours to "
        "write.\nIf you named it differently, update tests/adapter.py."
    ) from exc


def drive(client, messages, tools=TOOLS):
    """Run one full turn and hand back the resulting conversation."""
    result = run_turn(client, messages, tools)
    return messages if result is None else result
