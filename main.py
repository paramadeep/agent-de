import os

from anthropic import Anthropic

from tools.index import TOOLS, availble_tools

client = Anthropic(
    api_key=os.environ.get("CLAUDE_KEY"),
)
MODEL = "claude-haiku-4-5"



def run_tool(tool_name, tool_input):
    try:
        return availble_tools[tool_name](**tool_input)
    except KeyError:
        return f"Error: Unknown tool '{tool_name}'."
    except TypeError as e:
        return f"Error calling {tool_name}: Invalid arguments provided. Details: {e}"


def process_response(response):
    messages = []
    for block in response.content:
        if block.type == "text":
            messages.append({"role": "assistant", "content": block.text})
            print(f"Assistant: {block.text}")
        elif block.type == "tool_use":
            is_last_call_tool = True
            tool_result = run_tool(block.name, block.input)
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": block.id, "content": tool_result}
            ]})
            # print(f"Tool result: {tool_result}")
    return messages, is_last_call_tool
    

def main():
    messages = []  # conversation history — this list grows every turn
    print("Chat with AgentDe. Type 'exit' to quit.\n")
    is_last_call_tool = False
    while True:
        if not is_last_call_tool:
            user_input = input("You: ").strip()
            if user_input.lower() in ("exit", "quit"):
                break
            message = {"role": "user", "content": user_input}
            messages.append(message)
        response = client.messages.create(
            model=MODEL, messages=messages, max_tokens=1024, tools=TOOLS
        )
        messages_from_response_processing, is_last_call_tool = process_response(response)
        messages.extend(messages_from_response_processing)

        # TODO (step 4 — the agent loop):
        # Right now one user message = exactly one API call. If Claude asks for a
        # tool, you run it, put the result in `messages`... and then fall straight
        # back to input(). Claude never gets called again, so it never sees what
        # read_file returned. That's a chatbot with tools, not an agent.
        #
        # Wrap the API call in an inner `while True` and repeat until Claude is done:
        #
        #   1. call the API with the full history + TOOLS
        #   2. append the assistant turn EXACTLY ONCE:
        #        {"role": "assistant", "content": response.content}
        #      (not one message per block — process_response today appends the text
        #       once on its own AND again inside response.content, so the same text
        #       goes back twice in two consecutive assistant messages)
        #   3. if response.stop_reason != "tool_use": print the text and break —
        #      Claude has nothing left to ask for
        #   4. otherwise run EVERY tool_use block in response.content and collect
        #      all the results into ONE user message:
        #        {"role": "user", "content": [
        #            {"type": "tool_result", "tool_use_id": <id>, "content": <str>},
        #            ... one per tool_use block ...
        #        ]}
        #      `content` has to be a string — json.dumps() the dict read_file returns
        #   5. append it, go back to 1
        #
        # process_response as written can't do this (it mixes running tools with
        # building history, and returns instead of looping) — rewrite or replace it.
        #
        # The jump from step 3 to step 4 is the whole difference between a chatbot
        # and an agent. See LEARNING.md.
       
if __name__ == "__main__":
    main()
