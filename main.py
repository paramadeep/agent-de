import os

from anthropic import Anthropic

client = Anthropic(
    api_key=os.environ.get("CLAUDE_KEY"),
)
MODEL = "claude-haiku-4-5"


def main():
    messages = []  # conversation history — this list grows every turn

    print("Chat with Claude. Type 'exit' to quit.\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("exit", "quit"):
            break
        message = {"role": "user", "content": user_input}
        messages.append(message)
        response = client.messages.create(model=MODEL, messages=messages,max_tokens=1024)
        for block in response.content:
            if block.type == "text" :
                print(f"agent-de: {block.text}")
                message = {"role": "assistant", "content": block.text}
                messages.append(message)
        # TODO (write this part):
        # 1. Append the user's message to `messages`:
        #    {"role": "user", "content": user_input}
        # 2. Call client.messages.create(...) with model=MODEL,
        #    max_tokens=1024, and messages=messages (the FULL history,
        #    not just this turn).
        # 3. Pull the text out of the response — loop over
        #    response.content and grab blocks where block.type == "text".
        # 4. Print it, e.g. print(f"Claude: {reply_text}")
        # 5. Append the assistant's reply to `messages` too:
        #    {"role": "assistant", "content": reply_text}
        #    Skip this and Claude will "forget" every previous turn.


if __name__ == "__main__":
    main()
