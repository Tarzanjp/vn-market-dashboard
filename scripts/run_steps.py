"""
Step 1+2 combined runner:
  Step 1 - Security: escape all innerHTML fields from external JSON
  Step 2 - Shared lib: extract nf/sgn/cls/dmy/dmyF/esc to src/lib/format.js
  Final  - Build test
"""
import re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC  = ROOT / "src"
LIB  = SRC / "lib"

def log(msg):
    sys.stdout.buffer.write((msg + "\n").encode("utf-8", "replace"))
    sys.stdout.buffer.flush()

def read(p): return Path(p).read_text(encoding="utf-8")
def write(p, s): Path(p).write_text(s, encoding="utf-8")

# ════════════════════════════════════════════════════════════════════════════
# STEP 1 — Security: ensure all innerHTML template fields go through esc()
# ════════════════════════════════════════════════════════════════════════════
log("=" * 60)
log("STEP 1 — Security patches")
log("=" * 60)

# ── dashboardEngine.js ───────────────────────────────────────────────────────
p = SRC / "dashboard" / "dashboardEngine.js"
src = read(p)

replacements = [
    # srcHtml
    ("rel=\"noopener\">Nguồn: ${n.src}</a>`",
     "rel=\"noopener\">Nguồn: ${esc(n.src)}</a>`"),
    (": `Nguồn: ${n.src}`;",
     ": `Nguồn: ${esc(n.src)}`;"),
    # article class
    ('<article class="ncard ${n.cls}${n.hot',
     '<article class="ncard ${esc(n.cls)}${n.hot'),
    # badge
    ('"badge ${n.badgeCls}">${n.badge}</span>',
     '"badge ${esc(n.badgeCls)}">${esc(n.badge)}</span>'),
    # ntime
    ('" · " + n.time : ""}',
     '" · " + esc(n.time) : ""}'),
    # ntitle
    ('"ntitle">${n.title}</h3>',
     '"ntitle">${esc(n.title)}</h3>'),
    # bullets
    ('`<li>${b}</li>`',
     '`<li>${esc(b)}</li>`'),
    # chips
    ('`<span class="chipx ${c}">${t}</span>`',
     '`<span class="chipx ${esc(c)}">${esc(t)}</span>`'),
    # nvn
    ('`<div class="nvn">${n.vn}</div>`',
     '`<div class="nvn">${esc(n.vn)}</div>`'),
    # ndata key
    ('"lb">${k}</div>',
     '"lb">${esc(k)}</div>'),
    # ndata value — pattern: '' : c}" ...>${v}
    ("? '' : c}\" ",
     "? '' : esc(c)}\" "),
    ("}>${v}</div>",
     "}>${esc(v)}</div>"),
]

for old, new in replacements:
    if old in src:
        src = src.replace(old, new)
    # else: already patched or not present — skip silently

write(p, src)
log(f"[step1] dashboardEngine.js patched")

# ── cashoutEngine.js ─────────────────────────────────────────────────────────
p = SRC / "cashout" / "cashoutEngine.js"
src = read(p)

# Add esc() helper if not present
if "const esc = " not in src:
    src = src.replace(
        "export function initCashout(data, insight) {\n  const el = (id) => document.getElementById(id);",
        "export function initCashout(data, insight) {\n  const el = (id) => document.getElementById(id);\n  const esc = (s) => String(s).replace(/[&<>\"']/g, (c) => ({\"&\":\"&amp;\",\"<\":\"&lt;\",\">\":\"&gt;\",'\"':\"&quot;\",\"'\":\"&#39;\"}[c]));"
    )

cashout_replacements = [
    ('<span class="s-name">${s.code}</span>',
     '<span class="s-name">${esc(s.code)}</span>'),
    ('<span class="s-sector">${s.sector}</span>',
     '<span class="s-sector">${esc(s.sector)}</span>'),
    ('<span class="co-insider-code">${t.ticker}</span>',
     '<span class="co-insider-code">${esc(t.ticker)}</span>'),
    ('<span class="co-insider-title">${t.title_vi || t.title_en || "—"}</span>',
     '<span class="co-insider-title">${esc(t.title_vi || t.title_en || "—")}</span>'),
]
for old, new in cashout_replacements:
    if old in src:
        src = src.replace(old, new)

write(p, src)
log(f"[step1] cashoutEngine.js patched")

# ── worldEngine.js ───────────────────────────────────────────────────────────
p = SRC / "world" / "worldEngine.js"
src = read(p)

# Add esc() helper if not present
if "const esc = " not in src:
    src = src.replace(
        "  const el = id => document.getElementById(id);",
        "  const el = id => document.getElementById(id);\n  const esc = s => String(s).replace(/[&<>\"']/g, c => ({\"&\":\"&amp;\",\"<\":\"&lt;\",\">\":\"&gt;\",'\"':\"&quot;\",\"'\":\"&#39;\"}[c]));"
    )

world_replacements = [
    ('<span class="t-name">${m.name}</span>',
     '<span class="t-name">${esc(m.name)}</span>'),
    ('<span class="t-cty">${m.cty}</span>',
     '<span class="t-cty">${esc(m.cty)}</span>'),
    ('`<span class="t-note">${m.note}</span>`',
     '`<span class="t-note">${esc(m.note)}</span>`'),
    ('`<b style="font-weight:600">${m.name}</b>`',
     '`<b style="font-weight:600">${esc(m.name)}</b>`'),
    ('<span style="color:var(--dim);font-size:11.5px">${m.cty}</span>',
     '<span style="color:var(--dim);font-size:11.5px">${esc(m.cty)}</span>'),
    ('<span class="region">${sub}</span>',
     '<span class="region">${esc(sub)}</span>'),
]
for old, new in world_replacements:
    if old in src:
        src = src.replace(old, new)

write(p, src)
log(f"[step1] worldEngine.js patched")

# ── Step 1 Verify ────────────────────────────────────────────────────────────
step1_checks = [
    (SRC / "dashboard" / "dashboardEngine.js",
     ["esc(n.src)", "esc(n.cls)", "esc(n.badgeCls)", "esc(n.badge)",
      "esc(n.time)", "esc(n.title)", "esc(b)", "esc(n.vn)"]),
    (SRC / "cashout" / "cashoutEngine.js",
     ["const esc =", "esc(s.code)", "esc(s.sector)", "esc(t.ticker)"]),
    (SRC / "world" / "worldEngine.js",
     ["esc(m.name)", "esc(m.cty)", "esc(sub)"]),
]
step1_ok = True
for fpath, needles in step1_checks:
    src = read(fpath)
    for n in needles:
        ok = n in src
        log(f"[step1] {'OK  ' if ok else 'FAIL'} {fpath.name}: {n}")
        if not ok:
            step1_ok = False

if not step1_ok:
    log("[step1] FAILED — aborting")
    sys.exit(1)
log("[step1] ALL PASS")

# ════════════════════════════════════════════════════════════════════════════
# STEP 2 — Shared lib: extract helpers to src/lib/format.js
# ════════════════════════════════════════════════════════════════════════════
log("")
log("=" * 60)
log("STEP 2 — Extract src/lib/format.js")
log("=" * 60)

LIB.mkdir(exist_ok=True)
write(LIB / "format.js", """\
/**
 * src/lib/format.js
 * Shared pure-function helpers for all engine modules.
 * No imports, no side-effects.
 */

/** Format number vi-VN locale, null/NaN -> em-dash */
export const nf = (v, d = 2) => {
  if (v == null || (typeof v === "number" && Number.isNaN(v))) return "\u2014";
  const n = Number(v);
  if (Number.isNaN(n)) return "\u2014";
  return n.toLocaleString("vi-VN", { minimumFractionDigits: d, maximumFractionDigits: d });
};

/** Signed format (+/-), null/NaN -> em-dash */
export const sgn = (v, d = 2) => {
  if (v == null || (typeof v === "number" && Number.isNaN(v))) return "\u2014";
  const n = Number(v);
  if (Number.isNaN(n)) return "\u2014";
  return (n > 0 ? "+" : n < 0 ? "\u2212" : "") + nf(Math.abs(n), d);
};

/** CSS direction class: "up" | "down" | "flat" */
export const cls = (v) => {
  if (v == null || (typeof v === "number" && Number.isNaN(v))) return "flat";
  return v > 0 ? "up" : v < 0 ? "down" : "flat";
};

/** "YYYY-MM-DD" -> "MM/DD" (short) */
export const dmy = (iso) => (!iso ? "\u2014" : String(iso).slice(5).replace("-", "/"));

/** "YYYY-MM-DD" -> "YYYY/MM/DD" (full) */
export const dmyF = (iso) => (!iso ? "\u2014" : String(iso).replace(/-/g, "/"));

/** HTML-escape for safe innerHTML insertion */
export const esc = (s) =>
  String(s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
""")
log("[step2] created src/lib/format.js")

# ── Engine configs ────────────────────────────────────────────────────────────
HELPERS = ["nf", "sgn", "cls", "dmy", "dmyF", "esc"]

ENGINES = [
    {
        "path":   SRC / "dashboard" / "dashboardEngine.js",
        "imp":    "../lib/format.js",
        "remove": ["nf", "sgn", "cls", "dmy", "dmyF", "esc"],
    },
    {
        "path":   SRC / "history" / "historyEngine.js",
        "imp":    "../lib/format.js",
        "remove": ["nf", "sgn", "dmyF"],
    },
    {
        "path":   SRC / "world" / "worldEngine.js",
        "imp":    "../lib/format.js",
        "remove": ["nf", "sgn", "cls", "esc"],
    },
    {
        "path":   SRC / "cashout" / "cashoutEngine.js",
        "imp":    "../lib/format.js",
        "remove": ["esc"],
    },
]

def used_in(src):
    clean = re.sub(r"^import[^\n]+\n", "", src, flags=re.MULTILINE)
    return [h for h in HELPERS if re.search(rf"(?<!['\"\w]){h}\s*\(", clean)]

def remove_local_def(src, helper):
    """
    Remove the local const definition of `helper`.
    Handles both single-line and multiline (block) arrow functions.
    Strategy: find the line starting with optional whitespace + 'const helper =',
    then consume until the statement ends (semicolon on its own line or same line).
    """
    h = re.escape(helper)
    # Single-line: const h = ... ;  (no opening brace on same line that isn't closed)
    # Multiline block: const h = (...) => {\n  ...\n};\n
    # We use a simple approach: match from 'const h =' to the next '};' or ';' at line end
    pattern = rf"^[ \t]*const {h} = (?:[^\n]*\n(?:[ \t][^\n]*\n)*?[ \t]*\}};\r?\n|[^\n]+\n)"
    new = re.sub(pattern, "", src, flags=re.MULTILINE)
    return new

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

# ── Patch each engine ─────────────────────────────────────────────────────────
for eng in ENGINES:
    p = eng["path"]
    src = read(p)
    before = len(src)

    for h in eng["remove"]:
        src = remove_local_def(src, h)

    used = used_in(src)
    imp = eng["imp"]
    if used and f'from "{imp}"' not in src:
        src = insert_import(src, f'import {{ {", ".join(used)} }} from "{imp}";\n')

    write(p, src)
    log(f"[step2] {p.name}: -{before - len(src)} chars | imports: {used}")

# ── Step 2 Verify ─────────────────────────────────────────────────────────────
log("[step2] === VERIFY ===")
step2_ok = True

# format.js exports
fmt = read(LIB / "format.js")
for h in HELPERS:
    ok = f"export const {h}" in fmt
    log(f"[step2] {'OK  ' if ok else 'FAIL'} format.js exports {h}")
    if not ok:
        step2_ok = False

# engines clean
for eng in ENGINES:
    src = read(eng["path"])
    clean = re.sub(r"^import[^\n]+\n", "", src, flags=re.MULTILINE)
    remaining = [h for h in eng["remove"]
                 if re.search(rf"^[ \t]*const {h}\s*=", clean, re.MULTILINE)]
    used = used_in(src)
    has_imp = f'from "{eng["imp"]}"' in src
    if remaining:
        log(f"[step2] FAIL {eng['path'].name}: still defines {remaining}")
        step2_ok = False
    elif used and not has_imp:
        log(f"[step2] FAIL {eng['path'].name}: uses {used} but no import")
        step2_ok = False
    else:
        log(f"[step2] OK   {eng['path'].name}: clean | uses={used} | import={has_imp}")

# Step 1 patches still intact after step 2
# Note: 'const esc =' is intentionally removed by step2 (moved to lib/format.js)
# so we skip that specific check here
step1_checks_post = [
    (SRC / "dashboard" / "dashboardEngine.js",
     ["esc(n.src)", "esc(n.cls)", "esc(n.badgeCls)", "esc(n.badge)",
      "esc(n.time)", "esc(n.title)", "esc(b)", "esc(n.vn)"]),
    (SRC / "cashout" / "cashoutEngine.js",
     ["esc(s.code)", "esc(s.sector)", "esc(t.ticker)"]),
    (SRC / "world" / "worldEngine.js",
     ["esc(m.name)", "esc(m.cty)", "esc(sub)"]),
]
for fpath, needles in step1_checks_post:
    src = read(fpath)
    for n in needles:
        ok = n in src
        if not ok:
            log(f"[step2] FAIL step1 patch lost in {fpath.name}: {n}")
            step2_ok = False

if not step2_ok:
    log("[step2] VERIFY FAILED — aborting build")
    sys.exit(1)

log("[step2] ALL PASS")

# ════════════════════════════════════════════════════════════════════════════
# FINAL — Build test
# ════════════════════════════════════════════════════════════════════════════
log("")
log("=" * 60)
log("FINAL — npm run build")
log("=" * 60)

r = subprocess.run(
    "npm run build",
    shell=True, cwd=ROOT,
    capture_output=True, text=True,
    encoding="utf-8", errors="replace",
)
out = r.stdout + r.stderr
tail = out[-4000:] if len(out) > 4000 else out
sys.stdout.buffer.write(tail.encode("utf-8", "replace"))
sys.stdout.buffer.flush()

if r.returncode != 0:
    log("BUILD FAILED")
    sys.exit(1)

log("BUILD PASSED")
log("=== STEP 1 + STEP 2 COMPLETE ===")
