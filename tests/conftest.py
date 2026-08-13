"""Importing `main` constructs an Anthropic client at module scope, which needs a
key present. The tests never reach the network — the fake client stands in — so a
placeholder is enough to let the import succeed on a machine with no key set.
"""

import os

os.environ.setdefault("CLAUDE_KEY", "placeholder-not-used-by-tests")
