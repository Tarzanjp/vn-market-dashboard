"""
Step 2 - Extract src/lib/format.js shared helpers (nf, sgn, cls, dmy, dmyF, esc)
Run from repo root: python scripts/step2_shared_lib.py
"""
import re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC  = ROOT / "src"
LIB  = SRC / "lib"

def log(msg):
    print(f"[step2] {msg}", flush=True)

# ── STEP 2A: Audit what each engine defines locally ──────────────────────────
log("=== AUDIT ===")
ENGINE_FILES = [
    SRC / "dashboard" / "dashboardEngine.js",
    SRC / "history"   / "historyEngine.js",
    SRC / "world"     / "worldEngine.js",
    SRC / "cashout"   / "cashoutEngine.js",
    SRC / "sectorFlows" / "sectorFlowsEngine.js",
]
HELPERS = ["nf", "sgn", "cls", "dmy", "dmyF", "esc"]

for p in ENGINE_FILES:
    src = p.read_text(encoding="utf-8")
    found = [h for h in HELPERS if re.search(rf"\bconst {h}\s*=", src)]
    log(f"  {p.name}: defines locally -> {found}")

# ── STEP 2B: Create src/lib/format.js ────────────────────────────────────────
log("\n=== CREATE src/lib/format.js ===")
LIB.mkdir(exist_ok=True)

FORMAT_SRC = """\
/**
 * src/lib/format.js
 * Shared pure-function helpers used by all engine modules.
 * No imports, no side-effects.
 */

/** Format number vi-VN locale, null/NaN -> "—" */
export const nf = (v, d = 2) => {
  if (v == null || (typeof v === "number" && Number.isNaN(v))) return "\\u2014";
  const n = Number(v);
  if (Number.isNaN(n)) return "\\u2014";
  return n.toLocaleString("vi-VN", { minimumFractionDigits: d, maximumFractionDigits: d });
};

/** Signed format (+/-), null/NaN -> "—" */
export const sgn = (v, d = 2) => {
  if (v == null || (typeof v === "number" && Number.isNaN(v))) return "\\u2014";
  const n = Number(v);
  if (Number.isNaN(n)) return "\\u2014";
  return (n > 0 ? "+" : n < 0 ? "\\u2212" : "") + nf(Math.abs(n), d);
};

/** CSS direction class: "up" | "down" | "flat" */
export const cls = (v) => {
  if (v == null || (typeof v === "number" && Number.isNaN(v))) return "flat";
  return v > 0 ? "up" : v < 0 ? "down" : "flat";
};

/** "YYYY-MM-DD" -> "MM/DD" (short) */
export const dmy = (iso) => (!iso ? "\\u2014" : String(iso).slice(5).replace("-", "/"));

/** "YYYY-MM-DD" -> "YYYY/MM/DD" (full) */
export const dmyF = (iso) => (!iso ? "\\u2014" : String(iso).replace(/-/g, "/"));

/** HTML-escape for safe innerHTML insertion */
export const esc = (s) =>
  String(s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
"""

(LIB / "format.js").write_text(FORMAT_SRC, encoding="utf-8")
log("  created src/lib/format.js")

# ── STEP 2C: Patch each engine ────────────────────────────────────────────────
log("\n=== PATCH ENGINES ===")

# Regex patterns for local definitions to REMOVE from each engine.
# Each pattern targets the full line(s) of a local const definition.
REMOVE_PATTERNS = {
    "nf":   [
        # multiline block: const nf = (v, d = 2) => { ... };
        r"  const nf = \(v, d = 2\) => \{[^}]+\};\r?\n",
        # single line variant
        r"  const nf = \(v, d = 2\) =>[^\n]+\n",
        r"  const nf = \(v,[^\n]+\n",
    ],
    "sgn":  [
        r"  const sgn = \(v, d = 2\) => \{[^}]+\};\r?\n",
        r"  const sgn = \(v, d = 2\) =>[^\n]+\n",
        r"  const sgn = \(v,[^\n]+\n",
    ],
    "cls":  [
        r"  const cls = v => \{[^}]+\};\r?\n",
        r"  const cls = v =>[^\n]+\n",
        r"  const cls = \(v\)[^\n]+\n",
    ],
    "dmy":  [
        r"  const dmy = iso =>[^\n]+\n",
        r"  const dmy = \(iso\)[^\n]+\n",
    ],
    "dmyF": [
        r"  const dmyF = iso =>[^\n]+\n",
        r"  const dmyF = \(iso\)[^\n]+\n",
    ],
    "esc":  [
        r"  const esc = s =>[^\n]+\n",
        r"  const esc = \(s\)[^\n]+\n",
    ],
}

# Which helpers each engine uses (determines what to import)
def detect_usage(src: str, after_removal: bool = False) -> list:
    """Detect which helpers are called (not defined) in src."""
    used = []
    for h in HELPERS:
        # Match usage like nf( or sgn( but NOT const nf =
        if re.search(rf"(?<!const ){h}\s*\(", src):
            used.append(h)
    return used

def insert_import(src: str, import_line: str) -> str:
    """Insert import after opening block comment if present, else at top."""
    lines = src.splitlines(keepends=True)
    insert_at = 0
    in_block = False
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("/*"):
            in_block = True
        if in_block and "*/" in s:
            in_block = False
            insert_at = i + 1
            break
    lines.insert(insert_at, import_line)
    return "".join(lines)

IMPORT_PATH = {
    SRC / "dashboard"   / "dashboardEngine.js":   "../lib/format.js",
    SRC / "history"     / "historyEngine.js":      "../lib/format.js",
    SRC / "world"       / "worldEngine.js":        "../lib/format.js",
    SRC / "cashout"     / "cashoutEngine.js":      "../lib/format.js",
    SRC / "sectorFlows" / "sectorFlowsEngine.js":  "../lib/format.js",
}

for p in ENGINE_FILES:
    src = p.read_text(encoding="utf-8")
    original = src

    # Remove all local helper definitions
    for h, patterns in REMOVE_PATTERNS.items():
        for pat in patterns:
            src = re.sub(pat, "", src)

    # Detect which helpers are actually used
    used = detect_usage(src)

    # Add import if needed and not already present
    imp_path = IMPORT_PATH[p]
    already_imported = f'from "{imp_path}"' in src
    if used and not already_imported:
        import_line = f'import {{ {", ".join(used)} }} from "{imp_path}";\n'
        src = insert_import(src, import_line)

    p.write_text(src, encoding="utf-8")
    removed = len(original) - len(src)
    log(f"  {p.name}: -{removed} chars | import: {used}")

# ── STEP 2D: Verify ───────────────────────────────────────────────────────────
log("\n=== VERIFY ===")
all_pass = True

# 2D-1: format.js exports all helpers
fmt = (LIB / "format.js").read_text(encoding="utf-8")
for h in HELPERS:
    ok = f"export const {h}" in fmt
    log(f"  {'OK  ' if ok else 'FAIL'} format.js exports {h}")
    if not ok:
        all_pass = False

# 2D-2: no engine redefines helpers locally
for p in ENGINE_FILES:
    src = p.read_text(encoding="utf-8")
    # Strip import lines before checking
    src_no_import = re.sub(r"^import[^\n]+\n", "", src, flags=re.MULTILINE)
    remaining = [h for h in HELPERS if re.search(rf"\bconst {h}\s*=", src_no_import)]
    used = detect_usage(src)
    has_import = f'from "../lib/format.js"' in src

    if remaining:
        log(f"  FAIL {p.name}: still defines locally: {remaining}")
        all_pass = False
    elif used and not has_import:
        log(f"  FAIL {p.name}: uses {used} but missing import")
        all_pass = False
    else:
        log(f"  OK   {p.name}: no local defs | uses: {used} | import: {has_import}")

if not all_pass:
    log("\nVerify FAILED — fix before build")
    sys.exit(1)

# ── STEP 2E: Build test ───────────────────────────────────────────────────────
log("\n=== BUILD TEST ===")
result = subprocess.run(
    ["npm", "run", "build"],
    cwd=ROOT,
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
)
out = result.stdout + result.stderr
# Print last 3000 chars to avoid truncation
tail = out[-3000:] if len(out) > 3000 else out
print(tail, flush=True)

if result.returncode != 0:
    log("BUILD FAILED")
    sys.exit(1)

log("BUILD PASSED")
log("\n=== STEP 2 COMPLETE ===")
