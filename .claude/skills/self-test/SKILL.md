---
name: self-test
description: Run agent-de against itself in a tmux pane to verify the agent loop works end to end. Use when asked to test the agent, self-test, verify the loop, check whether a step in LEARNING.md actually works, or after any change to main.py, the tool loop, or tools/.
---

# Self-testing agent-de

`main.py` is an interactive REPL built on `input()`. Piped stdin doesn't exercise it
faithfully — the turns run together and you can't tell where one ends. So the harness
drives a **real PTY** via tmux: it types a message, waits for the `You: ` prompt to
come back, and asserts on what appeared in between.

## Running it

```bash
.claude/skills/self-test/run.sh              # all cases
.claude/skills/self-test/run.sh loop         # one case
.claude/skills/self-test/run.sh --keep       # leave the session up to poke at
```

Needs `CLAUDE_KEY`; the script sources `.envrc` itself if it isn't already exported.
Each run costs a handful of real Haiku calls.

## The cases, and what each one actually proves

| Case | Proves |
|---|---|
| `chat` | The basic request/response path works. No tools involved. |
| `loop` | **Step 4.** One user message triggers a tool call *and* gets a final answer back. If the loop is broken this is the case that catches it. |
| `memory` | History survives across turns — including tool results from an earlier turn. |
| `error` | A failed tool returns its error to the model as feedback instead of raising. |
| `multihop` | The loop iterates **more than once** per user turn: `hop1.txt` names `hop2.txt`, so the agent must read twice before it can answer. |

The fixtures use tokens (`MAGIC_TOKEN_7F3A`, `ZEPHYR_9K2`) that never appear in the
prompt text. So a token in the transcript can only have come from the agent genuinely
reading the file — it can't be an echo of our own input.

## Reading a failure

Turn completion is detected by the `You: ` prompt reappearing, so failures separate
cleanly into three shapes:

- **`never printed an Assistant line`** — the agent ran the tool and went straight back
  to the prompt without saying anything. The tool result is sitting in `messages` and
  was never sent back to the model. Classic broken loop.
- **`agent process died mid-turn`** — an exception. Usually malformed history: two
  consecutive assistant messages, or a `tool_result.content` that isn't a string. The
  transcript has the traceback.
- **`timed out`** — the loop is spinning without terminating. Check the
  `stop_reason != "tool_use"` exit condition.

On failure the whole transcript is printed. Use `--keep` and `tmux attach` to drive
the same session by hand.

## Extending it

Add a case with `run_case <name> <what it proves> <message> <regex>` and register it
with a matching `wants <name> &&` line. Prompts must not contain the string being
asserted on. As tools land in later phases (`edit_file`, `bash`), each one wants a
case here — that's what keeps earlier steps from silently regressing.
