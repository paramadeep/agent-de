# agent-de
#   who writes what -> CLAUDE.md
#   where we are    -> LEARNING.md

.DEFAULT_GOAL := help

help: ## list available targets
	@grep -hE '^[a-z][a-z-]*:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

run: ## start the agent REPL
	uv run main.py

test: ## run the unit tests once
	uv run pytest

watch: ## re-run the unit tests on every save (Ctrl-C to stop)
	uv run ptw . --now --clear --patterns '*.py'

typecheck: ## type-check the project
	uv run ty check

selftest: ## drive the real agent through tmux — costs real API calls
	.claude/skills/self-test/run.sh

.PHONY: help run test watch typecheck selftest
