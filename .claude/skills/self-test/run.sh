#!/usr/bin/env bash
# Drive agent-de's interactive REPL inside a tmux pane and assert the agent loop
# actually works end to end.
#
#   ./run.sh              run all cases
#   ./run.sh chat loop    run only the named cases
#   ./run.sh --keep       leave the tmux session alive afterwards to poke at it
#                         (attach with: tmux attach -t <session name printed below>)
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
SESSION="agentde-selftest-$$"
TIMEOUT="${AGENTDE_TEST_TIMEOUT:-60}"   # seconds to wait for one turn to finish
POLL=0.5
KEEP=0

FIXTURES="$(mktemp -d "${TMPDIR:-/tmp}/agentde-fixtures.XXXXXX")"
TRANSCRIPT="$FIXTURES/transcript.txt"

pass_n=0; fail_n=0; FAILED=()

# ---------------------------------------------------------------- fixtures ---
# Tokens are chosen so they never appear in the prompt text itself — that way a
# match in the transcript can only have come from the agent actually reading
# the file, not from our own echoed input.
setup_fixtures() {
  printf 'MAGIC_TOKEN_7F3A\n' > "$FIXTURES/token.txt"
  printf 'The value you want is not here. Read this exact path to get it: %s/hop2.txt\n' \
    "$FIXTURES" > "$FIXTURES/hop1.txt"
  printf 'SECRET=ZEPHYR_9K2\n' > "$FIXTURES/hop2.txt"
}

# ------------------------------------------------------------------- tmux ----
# capture-pane pads out to the full pane height, so strip the trailing blank rows
# — otherwise `tail` on this returns nothing but empty lines.
pane() {
  tmux capture-pane -p -S - -t "$SESSION" 2>/dev/null |
    awk 'NF{for(;b;b--) print ""; print; next} {b++}'
}

# The REPL prints "You: " via input(). A finished turn == a new prompt appeared.
# NB: capture-pane strips trailing whitespace, so the bare prompt lands as "You:"
# with no trailing space — don't put one in the pattern.
prompt_count() { pane | grep -c '^You:'; }

# The pane is kept alive past the agent's death (see start_agent) so a traceback
# is still capturable — so "alive" means the exit marker hasn't appeared yet.
alive() {
  tmux has-session -t "$SESSION" 2>/dev/null || return 1
  ! pane | grep -q '\[AGENT-EXITED'
}

# Everything this turn printed. The prompt we typed into is the Nth one and our text
# is echoed onto that same line, so the turn starts AT that prompt, not after it —
# slicing from N+1 yields nothing but the empty trailing prompt.
turn_output() {
  pane | awk -v n="$1" '/^You:/{c++} c>=n'
}

start_agent() {
  if [[ -z "${CLAUDE_KEY:-}" && -f "$REPO/.envrc" ]]; then
    # shellcheck disable=SC1091
    source "$REPO/.envrc"
  fi
  if [[ -z "${CLAUDE_KEY:-}" ]]; then
    echo "FATAL: CLAUDE_KEY is not set and $REPO/.envrc did not provide it." >&2
    exit 2
fi

  # If the agent dies, the pane must outlive it or the traceback dies with the
  # session — so trail the command with a marker and an idle sleep.
  local cmd='uv run main.py 2>&1; printf "\n[AGENT-EXITED rc=%s]\n" $?; exec sleep 3600'
  tmux new-session -d -s "$SESSION" -x 200 -y 200 -c "$REPO" \
    -e CLAUDE_KEY="$CLAUDE_KEY" \
    "$cmd"

  local deadline=$((SECONDS + 30))
  while (( SECONDS < deadline )); do
    [[ "$(prompt_count)" -ge 1 ]] && return 0
    alive || { echo "FATAL: agent exited during startup:"; echo; pane; exit 2; }
    sleep "$POLL"
  done
  echo "FATAL: agent never printed a prompt within 30s:"; echo; pane; exit 2
}

stop_agent() {
  if (( KEEP )); then
    echo
    echo "Session left running: tmux attach -t $SESSION"
    echo "Fixtures + transcript: $FIXTURES"
    return
  fi
  tmux kill-session -t "$SESSION" 2>/dev/null
  rm -rf "$FIXTURES"
}
trap stop_agent EXIT

# ------------------------------------------------------------------ cases ----
# run_case <name> <what it proves> <message to send> <regex that must appear>
run_case() {
  local name="$1" proves="$2" msg="$3" expect="$4"
  local before out

  if ! alive; then
    fail "$name" "agent process is dead — a previous case killed it"
    return
  fi

  before="$(prompt_count)"
  tmux send-keys -t "$SESSION" "$msg" Enter

  local deadline=$((SECONDS + TIMEOUT)) done=0
  while (( SECONDS < deadline )); do
    if [[ "$(prompt_count)" -gt "$before" ]]; then done=1; break; fi
    if ! alive; then
      # A crash means no new prompt ever appeared, so there is no turn delta to
      # slice — take the tail of the whole pane, which is where the traceback is.
      out="$(pane | tail -40)"
      { echo "### $name — AGENT CRASHED"; echo "$out"; } >> "$TRANSCRIPT"
      fail "$name" "agent process died mid-turn (see transcript)"
      return
    fi
    sleep "$POLL"
  done

  if (( ! done )); then
    fail "$name" "timed out after ${TIMEOUT}s — never returned to the prompt"
    return
  fi

  out="$(turn_output "$before")"
  { echo "### $name"; echo "$out"; echo; } >> "$TRANSCRIPT"

  if ! grep -q '^Assistant: ' <<<"$out"; then
    fail "$name" "agent never printed an Assistant line — it went silent after the tool call"
    return
  fi
  if grep -qE "$expect" <<<"$out"; then
    pass "$name" "$proves"
  else
    fail "$name" "expected /$expect/ in the reply, got:
$(sed 's/^/    | /' <<<"$out" | tail -20)"
  fi
}

pass() { pass_n=$((pass_n+1)); printf '  \033[32mPASS\033[0m  %-10s %s\n' "$1" "$2"; }
fail() { fail_n=$((fail_n+1)); FAILED+=("$1"); printf '  \033[31mFAIL\033[0m  %-10s %s\n' "$1" "$2"; }

# ------------------------------------------------------------------- main ----
ARGS=()
for a in "$@"; do
  [[ "$a" == "--keep" ]] && { KEEP=1; continue; }
  ARGS+=("$a")
done
wants() { (( ${#ARGS[@]} == 0 )) && return 0; [[ " ${ARGS[*]} " == *" $1 "* ]]; }

setup_fixtures
echo "agent-de self-test  (repo: $REPO)"
start_agent
echo

wants chat && run_case chat \
  "plain reply, no tool" \
  "Reply with exactly the word PONG and nothing else." \
  "PONG"

wants loop && run_case loop \
  "STEP 4: answered after a tool call, with no extra user turn" \
  "Read the file $FIXTURES/token.txt and tell me the exact token inside it." \
  "MAGIC_TOKEN_7F3A"

wants memory && run_case memory \
  "history survives across turns, including tool results" \
  "What token did you just find? Repeat it exactly." \
  "MAGIC_TOKEN_7F3A"

wants error && run_case error \
  "a failed tool feeds back to the model instead of crashing" \
  "Read the file $FIXTURES/does-not-exist.txt and tell me what went wrong." \
  "(not found|does not exist|doesn't exist|no such|missing|error)"

wants multihop && run_case multihop \
  "the loop runs MORE than once in a single user turn" \
  "Read $FIXTURES/hop1.txt, follow the instruction inside it, and tell me the secret value." \
  "ZEPHYR_9K2"

echo
echo "  $pass_n passed, $fail_n failed"
if (( fail_n )); then
  echo
  echo "Full transcript: $TRANSCRIPT"
  (( KEEP )) || { echo; echo "--- transcript ---"; cat "$TRANSCRIPT"; }
  exit 1
fi
