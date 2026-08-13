import os
from typing import Any
from anthropic import Anthropic
from tools.index import TOOLS, availble_tools

MODEL = "claude-haiku-4-5"

# TODO (step 6 — the system prompt). Add a SYSTEM string here and pass it to the API
# as `system=SYSTEM`, alongside model/messages/tools.
#
# Two things to get right, both covered by tests/test_system_prompt.py:
#   * it is NOT a message. No role, no place in the user/assistant alternation.
#     `{"role": "system", ...}` is an OpenAI-ism and Anthropic rejects it.
#   * it must go out on EVERY call, including the follow-up calls inside one turn
#     after a tool result. The API is stateless — nothing carries over.
#
# What tends to belong in one (the wording is yours — this is the most editable,
# highest-leverage string in the whole agent):
#   * who the agent is and how terse it should be
#   * when to reach for a tool vs. just answer
#   * environment facts the model can't know: cwd, OS, today's date
#   * hard rules — what it must never do
#
# Try it empty first, then add one line at a time and watch `make selftest` change
# behaviour. That feedback loop is the real lesson of this step.

def run_tool(tool_name, tool_input):
    try:
        return availble_tools[tool_name](**tool_input)
    except KeyError:
        return f"Error: Unknown tool '{tool_name}'."
    except TypeError as e:
        return f"Error calling {tool_name}: Invalid arguments provided. Details: {e}"


def process_response(response):
    messages = [{"role": "assistant", "content": response.content}]
    tool_run_result = []
    for block in response.content:
        if block.type == "text":
            print(f"Assistant: {block.text}")
        elif block.type == "tool_use":
            tool_result = run_tool(block.name, block.input)
            tool_run_result.append({"type": "tool_result", "tool_use_id": block.id, "content": tool_result})
    if tool_run_result.__len__() > 0:
        messages.append({"role": "user", "content": tool_run_result})
    return messages


def run_turn(client,messages: list[Any],tools) :
    had_claude_asked_to_stop  = False
    while not had_claude_asked_to_stop :
        response = client.messages.create(
            model=MODEL, messages=messages, max_tokens=16384, tools=tools
        )
        had_claude_asked_to_stop = response.stop_reason != "tool_use"
        messages_from_response_processing = process_response(response)
        messages.extend(messages_from_response_processing)
    return messages


def main():
    client = Anthropic(
        api_key=os.environ.get("CLAUDE_KEY"),
    )
    messages = []
    print("Chat with AgentDe. Type 'exit' to quit.\n")
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("exit", "quit"):
            break
        message = {"role": "user", "content": user_input}
        messages.append(message)
        messages = run_turn(client, messages,TOOLS)


if __name__ == "__main__":
    main()
