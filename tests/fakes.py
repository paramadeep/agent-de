"""A stand-in for the Anthropic client, so the agent loop can be tested without
the network, an API key, or the model's unpredictable prose.

The loop is pure logic: given a sequence of API responses, does it build the right
`messages` list and stop at the right time? None of that needs a real model — and
testing it against one would mean asserting on English instead of on structure.
"""

import copy
from types import SimpleNamespace


# ── response building blocks ────────────────────────────────────────────────
# The real SDK returns objects with attribute access (block.type, block.text),
# not dicts — SimpleNamespace mimics that shape closely enough for the loop.

def text(body):
    """A text block, i.e. Claude talking."""
    return SimpleNamespace(type="text", text=body)


def tool_use(id, name, **input):
    """A tool_use block, i.e. Claude asking the harness to run something."""
    return SimpleNamespace(type="tool_use", id=id, name=name, input=input)


def reply(*blocks):
    """A final response — Claude is done and wants no more tools."""
    return SimpleNamespace(content=list(blocks), stop_reason="end_turn")


def wants_tool(*blocks):
    """A response that asks for at least one tool. The loop must NOT stop here."""
    return SimpleNamespace(content=list(blocks), stop_reason="tool_use")


# ── the fake client ─────────────────────────────────────────────────────────

class FakeClient:
    """Drop-in for `anthropic.Anthropic` that replays a scripted list of responses.

    Records the exact `messages` list handed to it on every call, deep-copied, so a
    test can inspect what the loop sent on turn 2 without turn 3 having mutated it
    underneath.
    """

    def __init__(self, *responses):
        self._script = list(responses)
        self.sent = []          # one entry per API call: the messages list as sent
        self.kwargs = []        # the rest of the call kwargs, e.g. tools=

    # the SDK's shape is client.messages.create(...), so `messages` returns self
    # and `create` lives right here.
    @property
    def messages(self):
        return self

    def create(self, **kwargs):
        self.sent.append(copy.deepcopy(kwargs.get("messages")))
        self.kwargs.append(kwargs)
        if not self._script:
            raise AssertionError(
                f"The loop called the API {len(self.sent)} times but only "
                f"{len(self.sent) - 1} responses were scripted — it isn't terminating."
            )
        return self._script.pop(0)

    @property
    def call_count(self):
        return len(self.sent)


# ── assertion helpers ───────────────────────────────────────────────────────

def tool_results_in(message):
    """Every tool_result block inside one message, whatever container style."""
    content = message.get("content")
    if not isinstance(content, list):
        return []
    out = []
    for block in content:
        as_dict = block if isinstance(block, dict) else getattr(block, "__dict__", {})
        if as_dict.get("type") == "tool_result":
            out.append(as_dict)
    return out


def roles(messages):
    return [m["role"] for m in messages]
