"""Invariants of the agent loop (LEARNING.md step 4).

These assert on the *structure* the loop builds — how many API calls it makes, what
lands in `messages`, when it stops. Nothing here depends on the model's wording, so
the suite is deterministic, free, and runs in milliseconds.

If a test fails, the failure names the concept it's protecting. Fixing the code is
yours; see CLAUDE.md.
"""

import pytest

from tools.index import TOOLS
from tests.fakes import (
    FakeClient,
    reply,
    roles,
    text,
    tool_results_in,
    tool_use,
    wants_tool,
)

# ── binding to your implementation ──────────────────────────────────────────
# These tests pin BEHAVIOUR, not naming. The contract is:
#
#     run_turn(client, messages, tools) -> messages
#
#   * `messages` already ends with the new user message
#   * it loops until Claude stops asking for tools
#   * it returns the updated history (returning None and mutating in place is
#     fine too — the adapter below accepts either)
#
# Named it something else? Change these two things and nothing else in this file.

try:
    from main import run_turn
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "These tests expect main.run_turn(client, messages, tools).\n"
        "It doesn't exist yet — that's step 4 in LEARNING.md, and it's yours to "
        "write.\nIf you named it differently, update the adapter at the top of "
        "tests/test_agent_loop.py."
    ) from exc


def drive(client, messages, tools=TOOLS):
    result = run_turn(client, messages, tools)
    return messages if result is None else result


@pytest.fixture
def convo():
    return [{"role": "user", "content": "hello"}]


def assistant_messages(messages):
    return [m for m in messages if m["role"] == "assistant"]


# ── termination ─────────────────────────────────────────────────────────────

def test_plain_reply_calls_the_api_once(convo):
    """No tool requested -> one call, then stop. The loop must not spin."""
    client = FakeClient(reply(text("hi there")))

    drive(client, convo)

    assert client.call_count == 1


def test_loop_continues_while_stop_reason_is_tool_use(convo, tmp_path):
    """Two sequential tool calls in ONE user turn — the multi-hop case.

    This is what separates a real loop from an `if`: the agent reads a file, and
    what it finds sends it back for another read before it can answer.
    """
    a = tmp_path / "a.txt"
    a.write_text("read b.txt next")
    b = tmp_path / "b.txt"
    b.write_text("the answer")

    client = FakeClient(
        wants_tool(tool_use("t1", "read_file", path=str(a))),
        wants_tool(tool_use("t2", "read_file", path=str(b))),
        reply(text("done")),
    )

    drive(client, convo)

    assert client.call_count == 3, (
        "The loop stopped early. It must keep going while "
        "response.stop_reason == 'tool_use'."
    )


# ── the step 4 assertion ────────────────────────────────────────────────────

def test_tool_result_is_sent_back_to_the_model(convo, tmp_path):
    """THE step 4 test.

    Running the tool is not enough — the result has to go back in a follow-up API
    call, or the model never sees what it asked for. A broken loop passes every
    other test in this file and fails this one.
    """
    target = tmp_path / "note.txt"
    target.write_text("file contents here")

    client = FakeClient(
        wants_tool(tool_use("t1", "read_file", path=str(target))),
        reply(text("the file says: file contents here")),
    )

    drive(client, convo)

    assert client.call_count == 2, (
        "The tool ran but the model was never called again — the result is sitting "
        "in `messages` unread. That's a chatbot with tools, not an agent."
    )

    second_call = client.sent[1]
    results = [r for m in second_call for r in tool_results_in(m)]
    assert len(results) == 1, "The second API call carried no tool_result block."
    assert results[0]["tool_use_id"] == "t1"


def test_tool_result_content_is_a_string(convo, tmp_path):
    """The API rejects a dict here. Whatever the tool returns, serialise it."""
    target = tmp_path / "note.txt"
    target.write_text("hello")

    client = FakeClient(
        wants_tool(tool_use("t1", "read_file", path=str(target))),
        reply(text("ok")),
    )

    drive(client, convo)

    results = [r for m in client.sent[1] for r in tool_results_in(m)]
    assert results, "no tool_result was sent back"
    assert isinstance(results[0]["content"], str), (
        f"tool_result.content must be a str, got {type(results[0]['content']).__name__}"
    )


def test_tool_result_carries_the_actual_output(convo, tmp_path):
    """The result must be the tool's real output, not a placeholder."""
    target = tmp_path / "note.txt"
    target.write_text("SENTINEL_VALUE_42")

    client = FakeClient(
        wants_tool(tool_use("t1", "read_file", path=str(target))),
        reply(text("ok")),
    )

    drive(client, convo)

    results = [r for m in client.sent[1] for r in tool_results_in(m)]
    assert "SENTINEL_VALUE_42" in results[0]["content"]


# ── history integrity ───────────────────────────────────────────────────────

def test_assistant_turn_is_appended_exactly_once(convo, tmp_path):
    """One API response == one assistant message.

    Appending the text block on its own AND the whole response.content is the
    classic bug: the same text goes back twice, in two consecutive assistant
    messages.
    """
    target = tmp_path / "note.txt"
    target.write_text("x")

    client = FakeClient(
        wants_tool(text("I'll read that for you"),
                   tool_use("t1", "read_file", path=str(target))),
        reply(text("all done")),
    )

    messages = drive(client, convo)

    assert len(assistant_messages(messages)) == 2, (
        f"2 API responses should produce 2 assistant messages, got "
        f"{len(assistant_messages(messages))}: {roles(messages)}"
    )


def test_roles_alternate(convo, tmp_path):
    """The API requires strict user/assistant alternation."""
    target = tmp_path / "note.txt"
    target.write_text("x")

    client = FakeClient(
        wants_tool(text("reading it now"),
                   tool_use("t1", "read_file", path=str(target))),
        reply(text("done")),
    )

    messages = drive(client, convo)

    seq = roles(messages)
    for i in range(1, len(seq)):
        assert seq[i] != seq[i - 1], f"two {seq[i]} messages in a row: {seq}"


def test_tool_use_block_stays_in_history(convo, tmp_path):
    """A tool_result is an orphan unless the tool_use it answers is in history."""
    target = tmp_path / "note.txt"
    target.write_text("x")

    client = FakeClient(
        wants_tool(tool_use("t1", "read_file", path=str(target))),
        reply(text("done")),
    )

    drive(client, convo)

    flat = str(client.sent[1])
    assert "t1" in flat and "tool_use" in flat, (
        "The assistant turn containing the tool_use block was not sent back, so the "
        "tool_result has nothing to attach to."
    )


# ── multiple tools in one response ──────────────────────────────────────────

def test_parallel_tool_calls_batch_into_one_message(convo, tmp_path):
    """Claude can ask for several tools at once.

    All their results belong in ONE user message. Appending one message per result
    breaks role alternation.
    """
    a = tmp_path / "a.txt"
    a.write_text("alpha")
    b = tmp_path / "b.txt"
    b.write_text("beta")

    client = FakeClient(
        wants_tool(tool_use("t1", "read_file", path=str(a)),
                   tool_use("t2", "read_file", path=str(b))),
        reply(text("read both")),
    )

    drive(client, convo)

    second_call = client.sent[1]
    carriers = [m for m in second_call if tool_results_in(m)]
    assert len(carriers) == 1, (
        f"expected 1 user message carrying both results, found {len(carriers)}"
    )
    assert {r["tool_use_id"] for r in tool_results_in(carriers[0])} == {"t1", "t2"}


# ── errors are feedback ─────────────────────────────────────────────────────

def test_missing_file_is_reported_back_not_raised(convo, tmp_path):
    """A failed tool teaches the model. It must not kill the process."""
    client = FakeClient(
        wants_tool(tool_use("t1", "read_file", path=str(tmp_path / "nope.txt"))),
        reply(text("that file doesn't exist")),
    )

    drive(client, convo)

    results = [r for m in client.sent[1] for r in tool_results_in(m)]
    assert results, "the error never made it back to the model"
    assert "not found" in results[0]["content"].lower()


def test_unknown_tool_name_is_reported_back_not_raised(convo):
    """Same for a tool the harness doesn't have."""
    client = FakeClient(
        wants_tool(tool_use("t1", "no_such_tool", path="x")),
        reply(text("I can't do that")),
    )

    drive(client, convo)

    results = [r for m in client.sent[1] for r in tool_results_in(m)]
    assert results, "the error never made it back to the model"
    assert "unknown tool" in results[0]["content"].lower()
