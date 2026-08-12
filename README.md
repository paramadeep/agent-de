# agent-de


A minimal, hand-built version of a Claude-Code-like coding agent, built step by step to understand how these tools actually work under the hood.

## How it works

```mermaid
sequenceDiagram
    actor Human
    participant Harness as Harness (main.py)
    participant LLM as Claude (Anthropic API)

    Human->>Harness: types a message
    Harness->>Harness: append to messages[]
    Harness->>LLM: messages.create(messages, tools)

    alt Claude wants to use a tool
        LLM-->>Harness: tool_use block (name, input)
        Harness->>Harness: run_tool() locally
        Harness->>LLM: tool_result block
        LLM-->>Harness: final text
    else Claude just replies
        LLM-->>Harness: text block
    end

    Harness->>Harness: append reply to messages[]
    Harness-->>Human: prints reply
```

## What lives where

| Component | Lives in | Holds |
|---|---|---|
| **Human** | Terminal | Types input, reads output. No memory of its own — just eyes and a keyboard. |
| **Harness** (`main.py`) | Your machine, this Python process | The **conversation history** (`messages` list), the **tool implementations** (`read_file`, `run_tool`), the loop, the API key. This is the only place any state persists. |
| **LLM** (Claude) | Anthropic's servers | **Nothing.** Every API call is stateless — Claude has no memory between calls and only "knows" what's in the `messages` list you send that turn. It can *request* a tool call, but never executes anything itself; the harness always does. |

Key idea: the LLM is a pure function — `f(messages) -> next message`. All state (history, files, tool results) lives in the harness, not the model.
