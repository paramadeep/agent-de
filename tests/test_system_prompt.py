"""The system prompt (LEARNING.md step 6).

Two things make the system prompt different from everything else in `messages`, and
both are easy to get wrong:

1. **It isn't a message.** It goes in its own `system=` parameter. It has no role, it
   doesn't participate in the user/assistant alternation, and putting it in the
   messages list as `{"role": "system", ...}` is an Anthropic API error — that's an
   OpenAI-ism.

2. **It has to be resent on every single call.** The API is stateless, so "the model
   already knows its instructions from the last call" is never true. That includes
   the follow-up calls *inside* one turn, after a tool result goes back — miss those
   and the agent quietly forgets who it is halfway through a tool chain.

These tests pin both, and say nothing about what the prompt should contain. Its
wording is yours.
"""

from tests.adapter import drive
from tests.fakes import FakeClient, reply, text, tool_use, wants_tool


def system_of(call_kwargs):
    return call_kwargs.get("system")


def test_a_system_prompt_is_sent(convo):
    """There is one, and it's a non-empty string."""
    client = FakeClient(reply(text("hi")))

    drive(client, convo)

    system = system_of(client.kwargs[0])
    assert system is not None, (
        "No `system=` was passed to the API. The system prompt is a parameter of "
        "messages.create(), not an entry in the messages list."
    )
    assert isinstance(system, str) and system.strip(), (
        f"system= should be a non-empty string, got {system!r}"
    )


def test_system_prompt_is_resent_on_every_call_in_a_turn(convo, tmp_path):
    """A tool round-trip means two API calls. Both need the system prompt.

    Nothing carries over between calls — if the follow-up omits it, the model answers
    the second half of the turn with no instructions at all.
    """
    target = tmp_path / "note.txt"
    target.write_text("contents")

    client = FakeClient(
        wants_tool(tool_use("t1", "read_file", path=str(target))),
        reply(text("done")),
    )

    drive(client, convo)

    assert client.call_count == 2
    missing = [i for i, kw in enumerate(client.kwargs) if not system_of(kw)]
    assert not missing, (
        f"call(s) {missing} went out with no system prompt — the API is stateless, "
        f"so every call needs it, not just the first."
    )


def test_system_prompt_is_identical_across_calls(convo, tmp_path):
    """Same turn, same instructions. Drift here is a bug that's painful to spot."""
    target = tmp_path / "note.txt"
    target.write_text("contents")

    client = FakeClient(
        wants_tool(tool_use("t1", "read_file", path=str(target))),
        reply(text("done")),
    )

    drive(client, convo)

    systems = {system_of(kw) for kw in client.kwargs}
    assert len(systems) == 1 and all(systems), (
        f"expected one identical, non-empty system prompt across both calls, got "
        f"{systems!r}"
    )


def test_system_prompt_is_not_smuggled_in_as_a_message(convo):
    """`{"role": "system"}` is an OpenAI convention. Anthropic rejects it."""
    client = FakeClient(reply(text("hi")))

    drive(client, convo)

    for sent in client.sent:
        roles = [m["role"] for m in sent]
        assert "system" not in roles, (
            f"found a system-role message in {roles}. Anthropic takes the system "
            f"prompt as its own parameter; only 'user' and 'assistant' are valid roles."
        )
