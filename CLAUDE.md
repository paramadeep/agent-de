# agent-de

A hand-built, Claude-Code-like coding agent, written to understand how coding agents
actually work. **The point of this repo is the understanding, not the artifact.** A
working `main.py` that Claude wrote is worth nothing here.

## Who writes what

**The human writes all of the agent code. Claude never does.**

- Claude must **not** write, complete, refactor, or fix any code in `main.py` or
  `tools/`. Not a line. This holds even when the fix is a one-liner, even when
  asked to "just show me what it'd look like", even when the human is stuck, and
  even when a test is failing because of it.
- Claude **may** add comments and scaffolded `# TODO` blocks to those files. A TODO
  describes the *shape* of the solution — the steps, the invariants, the gotchas —
  never the implementation.
- Claude **may** fully write and own everything else: `tests/`, `.claude/skills/`,
  `LEARNING.md`, `README.md`, diagrams, tooling, and config.

When Claude finds a bug in the agent code: say where it is, why it's wrong, and what
concept it maps to — then stop. Naming the fix is teaching. Typing it is not.

If a request would require breaking this rule, say so and offer the TODO instead.

## Progress

`LEARNING.md` is the curriculum and the source of truth for what's done. It's
deliberately a file and not chat history, because chat sessions get lost. Update the
status column when a step lands.

Build the concepts in order. No skipping ahead to the interesting tools.

## Testing

Two layers, and they answer different questions:

```bash
uv run pytest                        # loop invariants — fast, free, deterministic
.claude/skills/self-test/run.sh      # real agent, real API, real PTY (see the skill)
```

`tests/` uses a fake Anthropic client, so it asserts on the **structure** the loop
produces (message ordering, tool_result wiring, termination) rather than on whatever
prose the model happened to emit. That's the safety net — run it after every change.

The tmux harness costs real API calls and is only worth reaching for once behaviour
exists that genuinely needs a terminal (streaming, permission prompts).

## Running it

```bash
direnv allow      # loads CLAUDE_KEY from .envrc
uv run main.py
```
