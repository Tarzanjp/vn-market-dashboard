"""PreToolUse/Bash hook: warn before a bulk run over many tickers.

Three tools in this project shipped a number computed from a truncated or wrong
sample, each time because a fresh tool was pointed at 15-40 tickers before being
checked against one with a known answer. "Validate one sample first" was written
down and then not followed, so the harness enforces it instead of intention.

Written in Python, not jq + shell: jq is not installed on this machine, so a
jq-based hook exits 0 and produces nothing. A hook that silently does nothing is
worse than no hook, and it fails exactly like the bugs it is meant to catch.
"""
import json
import re
import sys

try:
    # Read stdin as bytes and decode UTF-8 explicitly. json.load(sys.stdin)
    # uses the console encoding, which is cp932 here, so any command
    # containing Japanese text either mangles or raises — and the except
    # below would turn that into silence.
    cmd = (json.loads(sys.stdin.buffer.read().decode("utf-8", "replace"))
            .get("tool_input") or {}).get("command") or ""
except Exception:
    sys.exit(0)

# \b, not a character-class guard: a guard consumes the separator between
# adjacent tokens, so "1762 5367 7244" matches only every other code.
codes = set(re.findall(r"\b[0-9][0-9A-Z]{3}\b", cmd))
if len(codes) < 5:
    sys.exit(0)

json.dump({"hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "additionalContext": (
        f"PREFLIGHT — this command spans {len(codes)} ticker-like tokens. "
        "Before trusting the output: (1) has this tool been run on ONE subject "
        "whose answer you can check against an independent path? (2) does it print "
        "a per-subject value you can eyeball for absurdity — a subject missing from "
        "its own sample, a 0.00 where a number belongs? (3) does every loop stop on "
        "a count the SOURCE declares, not one you derived? If the tool changed since "
        "its last verified run, validate one sample first. Three bugs here each "
        "produced a plausible-looking wrong number from a truncated sample."
    )}}, sys.stdout)
