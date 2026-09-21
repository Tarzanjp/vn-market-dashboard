"""
Step 2 - Full auto: diagnose + fix + verify + build
Usage: python scripts/step2_run.py
"""
import re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC  = ROOT / "src"
LIB  = SRC / "lib"

def log(msg):
    sys.stdout.buffer.write((msg + "\n").encode("utf-8", "replace"))
    sys.stdout.buffer.flush()

def read(p):
    return Path(p).read_text(encoding="utf-8")

def write(p, s):
    Path(p).write_text(s, encoding="utf-8")

# ── 1. Create src/lib/format.js ──────────────────────────────────────────────
LIB.mkdir(exist_ok=True)
write(LIB / "format.js", """\
/**
 * src/lib/format.js - shared pure helpers for all engine modules.
 * No imports, no side-effects.
 */

/** Format number vi-VN, null/NaN -> em-dash */
export const nf = (v, d = 2) => {
  if (v == null || (typeof v === "number" && Number.isNaN(v))) return "\u2014";
  const n = Number(v);
  if (Number.isNaN(n)) return "\u2014";
  return n.toLocaleString("vi-VN", { minimumFractionDigits: d, maximumFractionDigits: d });
};

/** Signed format, null/NaN -> em-dash */
export const sgn = (v, d = 2) => {
  if (v == null || (typeof v === "number" && Number.isNaN(v))) return "\u2014";
  const n = Number(v);
  if (Number.isNaN(n)) return "\u2014";
  return (n > 0 ? "+" : n < 0 ? "\u2212" : "") + nf(Math.abs(n), d);
};

/** CSS direction class */
export const cls = (v) => {
  if (v == null || (typeof v === "number" && Number.isNaN(v))) return "flat";
  return v > 0 ? "up" : v < 0 ? "down" : "flat";
};

/** "YYYY-MM-DD" -> "MM/DD" */
export const dmy = (iso) => (!iso ? "\u2014" : String(iso).slice(5).replace("-", "/"));

/** "YYYY-MM-DD" -> "YYYY/MM/DD" */
export const dmyF = (iso) => (!iso ? "\u2014" : String(iso).replace(/-/g, "/"));

/** HTML-escape for safe innerHTML */
export const esc = (s) =>
  String(s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
""")
log("[step2] created src/lib/format.js")

# ── 2. Per-engine config: which helpers to remove + import path ──────────────
ENGINES = [
    {
        "path": SRC / "dashboard" / "dashboardEngine.js",
        "imp":  "../lib/format.js",
        "remove": ["nf", "sgn", "cls", "dmy", "dmyF", "esc"],
    },
    {
        "path": SRC / "history" / "historyEngine.js",
        "imp":  "../lib/format.js",
        "remove": ["nf", "sgn", "dmyF"],
    },
    {
        "path": SRC / "world" / "worldEngine.js",
        "imp":  "../lib/format.js",
        "remove": ["nf", "sgn", "cls"],
    },
    {
        "path": SRC / "cashout" / "cashoutEngine.js",
        "imp":  "../lib/format.js",
        "remove": ["esc"],
    },
]

# ── 3. Build precise removal patterns per helper ─────────────────────────────
def make_patterns(helper):
    """Return list of regex patterns that match the full local definition line(s)."""
    h = re.escape(helper)
    return [
        # multiline block: const X = (...) => {\n  ...\n};\n
        rf"[ \t]*const {h} = [^\n]*\n(?:[ \t][^\n]*\n)*?[ \t]*\}};\r?\n",
        # single-line arrow
        rf"[ \t]*const {h} = [^\n]+\n",
    ]

# ── 4. Detect which helpers are actually called (not defined) ─────────────────
HELPERS = ["nf", "sgn", "cls", "dmy", "dmyF", "esc"]

def used_in(src):
    # Remove import lines first so we don't count import { nf } as usage
    clean = re.sub(r"^import[^\n]+\n", "", src, flags=re.MULTILINE)
    return [h for h in HELPERS if re.search(rf"(?<!['\"\w]){h}\s*\(", clean)]

# ── 5. Insert import after opening block comment ──────────────────────────────
def insert_import(src, line):
    lines = src.splitlines(keepends=True)
    pos, in_block = 0, False
    for i, l in enumerate(lines):
        s = l.strip()
        if s.startswith("/*"):
            in_block = True
        if in_block and "*/" in s:
            in_block = False
            pos = i + 1
            break
    lines.insert(pos, line)
    return "".join(lines)

# ── 6. Patch each engine ──────────────────────────────────────────────────────
for eng in ENGINES:
    p = eng["path"]
    src = read(p)
    before = len(src)

    for h in eng["remove"]:
        for pat in make_patterns(h):
            new = re.sub(pat, "", src)
            if new != src:
                src = new
                break  # one pattern matched, move to next helper

    used = used_in(src)
    imp_path = eng["imp"]
    if used and f'from "{imp_path}"' not in src:
        src = insert_import(src, f'import {{ {", ".join(used)} }} from "{imp_path}";\n')

    write(p, src)
    log(f"[step2] {p.name}: -{before - len(src)} chars | imports: {used}")

# ── 7. Verify no local re-definitions remain ─────────────────────────────────
log("[step2] === VERIFY ===")
ok = True
for eng in ENGINES:
    src = read(eng["path"])
    clean = re.sub(r"^import[^\n]+\n", "", src, flags=re.MULTILINE)
    remaining = [h for h in eng["remove"] if re.search(rf"\bconst {h}\s*=", clean)]
    used = used_in(src)
    has_imp = f'from "{eng["imp"]}"' in src
    if remaining:
        log(f"[step2] FAIL {eng['path'].name}: still defines {remaining}")
        ok = False
    elif used and not has_imp:
        log(f"[step2] FAIL {eng['path'].name}: uses {used} but no import")
        ok = False
    else:
        log(f"[step2] OK   {eng['path'].name}: clean | uses={used} | import={has_imp}")

fmt = read(LIB / "format.js")
for h in HELPERS:
    if f"export const {h}" not in fmt:
        log(f"[step2] FAIL format.js missing export {h}")
        ok = False
    else:
        log(f"[step2] OK   format.js exports {h}")

if not ok:
    log("[step2] VERIFY FAILED - aborting")
    sys.exit(1)

# ── 8. Build ──────────────────────────────────────────────────────────────────
log("[step2] === BUILD ===")
r = subprocess.run("npm run build", shell=True, cwd=ROOT,
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
out = (r.stdout + r.stderr)
# print last 4000 chars
tail = out[-4000:] if len(out) > 4000 else out
sys.stdout.buffer.write(tail.encode("utf-8", "replace"))
sys.stdout.buffer.flush()

if r.returncode != 0:
    log("[step2] BUILD FAILED")
    sys.exit(1)

log("[step2] BUILD PASSED")
log("[step2] === STEP 2 COMPLETE ===")
