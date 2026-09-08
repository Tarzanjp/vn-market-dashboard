"""PreToolUse/Bash hook on git commit: state which branch is being committed to.

An automated daily agent creates agent/data-YYYY-MM-DD branches in this repo and
has twice switched the checkout mid-session, stranding commits on a branch that
later work never saw. Naming the branch at commit time makes that visible.

Self-filters on the command rather than trusting the settings "if" clause: that
clause was configured as Bash(git commit *) and the hook fired on unrelated
commands anyway. A gate in the code is one that can be tested.
"""
import json
import re
import subprocess
import sys

try:
    _cmd = (json.load(sys.stdin).get("tool_input") or {}).get("command") or ""
except Exception:
    sys.exit(0)

if not re.search(r"git\s+commit", _cmd):
    sys.exit(0)


def git(*a: str) -> str:
    try:
        return subprocess.run(("git",) + a, capture_output=True, text=True,
                              timeout=10).stdout.strip()
    except Exception:
        return ""


branch = git("rev-parse", "--abbrev-ref", "HEAD")
if not branch:
    sys.exit(0)
upstream = git("rev-parse", "--abbrev-ref", "@{upstream}") or "no upstream"

json.dump({"hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "additionalContext": (
        f"Committing to branch: {branch} (upstream: {upstream}). If this is not "
        "the branch your earlier commits this session went to, check with: "
        "git branch -a --contains <sha>"
    )}}, sys.stdout)
