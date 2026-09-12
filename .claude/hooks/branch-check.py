"""PreToolUse/Bash hook on git commit: state which branch is being committed to.

An automated daily agent creates agent/data-YYYY-MM-DD branches in this repo and
has twice switched the checkout mid-session, stranding commits on a branch that
later work never saw. Naming the branch at commit time makes that visible.

Self-filters on the command rather than trusting the settings "if" clause: that
clause was configured as Bash(git commit *) and the hook fired on unrelated
commands anyway. A gate in the code is one that can be tested.

Resolves the repo from a leading `cd` in the command. Without that it reported
the harness's own working directory, so committing into the Obsidian vault
printed this project's branch instead — a confident, wrong answer, which is
worse than none. When the directory cannot be determined the hook says which
one it inspected rather than implying it is the commit's target.
"""
import json
import re
import subprocess
import sys

try:
    # Read stdin as bytes and decode UTF-8 explicitly. json.load(sys.stdin)
    # uses the console encoding, which is cp932 here, so any command
    # containing Japanese text either mangles or raises — and the except
    # below would turn that into silence.
    _cmd = (json.loads(sys.stdin.buffer.read().decode("utf-8", "replace"))
            .get("tool_input") or {}).get("command") or ""
except Exception:
    sys.exit(0)

if not re.search(r"git\s+commit", _cmd):
    sys.exit(0)

# a leading `cd <path>` (quoted or bare) sets where the commit actually lands
m = re.search(r"""(?:^|[;&|]\s*)cd\s+(?:"([^"]+)"|'([^']+)'|(\S+))""", _cmd)
cwd = next((g for g in (m.groups() if m else ()) if g), None)

# The shell here is Git Bash, so a path arrives MSYS-style as /c/Users/...
# Python's subprocess on Windows cannot chdir to that and raises
# NotADirectoryError, which the except below would swallow into silence.
if cwd:
    d = re.match(r"^/([a-zA-Z])/(.*)$", cwd)
    if d:
        cwd = f"{d.group(1).upper()}:/{d.group(2)}"


def git(*a: str) -> str:
    try:
        # encoding must be explicit: text=True decodes with the locale encoding
        # (cp932 here) while git emits UTF-8, so --show-toplevel on a path
        # containing Japanese raised and the repo printed as "?" — the branch
        # itself is ASCII and came through, which is what hid the problem.
        return subprocess.run(("git",) + a, capture_output=True, text=True,
                              encoding="utf-8", errors="replace",
                              timeout=10, cwd=cwd).stdout.strip()
    except Exception:
        return ""


branch = git("rev-parse", "--abbrev-ref", "HEAD")
if not branch:
    # A cd was found but the repo could not be read: say so rather than going
    # quiet, since silence here is indistinguishable from "not a commit".
    if cwd:
        json.dump({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": (
                f"Could not read a git branch in {cwd} — this hook cannot tell "
                "you which branch this commit lands on. Check manually.")}},
            sys.stdout)
    sys.exit(0)
root = git("rev-parse", "--show-toplevel") or "?"
upstream = git("rev-parse", "--abbrev-ref", "@{upstream}") or "no upstream"

json.dump({"hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "additionalContext": (
        f"Committing to branch: {branch} (upstream: {upstream}) in repo {root}. "
        "If this is not the branch your earlier commits this session went to, "
        "check with: git branch -a --contains <sha>"
    )}}, sys.stdout)
