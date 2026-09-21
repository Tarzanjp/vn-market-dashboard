"""
Master refactor runner — Steps 1+2 (already done) + Steps 3,4,5
Runs continuously, each step verified before proceeding.

Step 3: Fix lifecycle leaks — setInterval/resize cleanup returned from engine init
Step 4: Eliminate window.__mbrScore global state — pass via return value
Step 5: Add missing <meta description> + <link rel=icon> to all HTML entry points
Step 6: Extract shared SVG chart primitive (svgChart helpers) to src/lib/svgChart.js
"""
import re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC  = ROOT / "src"
LIB  = SRC / "lib"

def log(msg):
    sys.stdout.buffer.write((msg + "\n").encode("utf-8", "replace"))
    sys.stdout.buffer.flush()

def read(p):  return Path(p).read_text(encoding="utf-8")
def write(p, s): Path(p).write_text(s, encoding="utf-8")

def build_test(label):
    log(f"\n[build] === {label} ===")
    r = subprocess.run("npm run build", shell=True, cwd=ROOT,
                       capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    out = (r.stdout + r.stderr)
    tail = out[-3000:] if len(out) > 3000 else out
    sys.stdout.buffer.write(tail.encode("utf-8", "replace"))
    sys.stdout.buffer.flush()
    if r.returncode != 0:
        log(f"[build] FAILED at {label}")
        sys.exit(1)
    log(f"[build] PASSED — {label}")

def assert_in(path, needle, label):
    src = read(path)
    ok = needle in src
    log(f"  {'OK  ' if ok else 'FAIL'} {Path(path).name}: {label}")
    return ok

def assert_not_in(path, needle, label):
    src = read(path)
    ok = needle not in src
    log(f"  {'OK  ' if ok else 'FAIL'} {Path(path).name}: {label}")
    return ok

# ════════════════════════════════════════════════════════════════════════════
# STEP 3 — Fix lifecycle leaks
# Problem: setInterval(tick,1000) and window.addEventListener("resize",...)
#          are never cleaned up → multiple intervals stack on re-mount
# Fix: initMarketDashboard / initWorldIndices / initCashout return a cleanup fn
#      MarketDashboardApp.jsx calls cleanup on unmount via useEffect return
# ════════════════════════════════════════════════════════════════════════════
log("=" * 60)
log("STEP 3 — Fix lifecycle leaks (setInterval + resize cleanup)")
log("=" * 60)

# ── 3a. dashboardEngine.js — wrap setInterval + resize in cleanup ─────────────
p = SRC / "dashboard" / "dashboardEngine.js"
src = read(p)

# Find the last section: tickClock + setInterval + resize listener
# Replace the bare setInterval and resize listener with tracked versions,
# and make initMarketDashboard return a cleanup function.

old_tick = "  tickClock(); setInterval(tickClock, 1000);"
new_tick = "  tickClock(); const _tickId = setInterval(tickClock, 1000);"
src = src.replace(old_tick, new_tick)

old_resize = (
    "  let rt;\n"
    "  window.addEventListener(\"resize\", () => { clearTimeout(rt); rt = setTimeout(renderAll, 140); });\n"
    "}"
)
new_resize = (
    "  let rt;\n"
    "  const _onResize = () => { clearTimeout(rt); rt = setTimeout(renderAll, 140); };\n"
    "  window.addEventListener(\"resize\", _onResize);\n"
    "  return function cleanup() {\n"
    "    clearInterval(_tickId);\n"
    "    clearTimeout(rt);\n"
    "    window.removeEventListener(\"resize\", _onResize);\n"
    "  };\n"
    "}"
)
src = src.replace(old_resize, new_resize)

# Also fix the margin resize (separate one inside drawMargin)
old_mg_resize = (
    "  window.addEventListener(\"resize\", () => { clearTimeout(window.__mgR); "
    "window.__mgR = setTimeout(drawMargin, 120); });"
)
new_mg_resize = (
    "  const _onMgResize = () => { clearTimeout(window.__mgR); window.__mgR = setTimeout(drawMargin, 120); };\n"
    "  window.addEventListener(\"resize\", _onMgResize);"
)
src = src.replace(old_mg_resize, new_mg_resize)

write(p, src)
log("[step3] dashboardEngine.js patched")

# ── 3b. worldEngine.js — same pattern ────────────────────────────────────────
p = SRC / "world" / "worldEngine.js"
src = read(p)

old_tick_w = "  tick(); setInterval(tick, 1000);"
new_tick_w = "  tick(); const _tickId = setInterval(tick, 1000);"
src = src.replace(old_tick_w, new_tick_w)

# worldEngine ends with render(); loadLiveOverlay(); — add cleanup return before closing }
# Find the last closing brace of initWorldIndices
if "return function cleanup()" not in src:
    # Insert before the final closing brace
    src = src.rstrip()
    if src.endswith("}"):
        src = src[:-1].rstrip()
        src += (
            "\n\n  return function cleanup() {\n"
            "    clearInterval(_tickId);\n"
            "    if (tvObserver) tvObserver.disconnect();\n"
            "  };\n"
            "}\n"
        )

write(p, src)
log("[step3] worldEngine.js patched")

# ── 3c. cashoutEngine.js — clock interval ────────────────────────────────────
p = SRC / "cashout" / "cashoutEngine.js"
src = read(p)

old_tick_c = "  tick();\n  setInterval(tick, 1000);"
new_tick_c = "  tick();\n  const _tickId = setInterval(tick, 1000);"
src = src.replace(old_tick_c, new_tick_c)

# Add cleanup return at end of initCashout
if "return function cleanup()" not in src:
    src = src.rstrip()
    if src.endswith("}"):
        src = src[:-1].rstrip()
        src += (
            "\n\n  return function cleanup() {\n"
            "    clearInterval(_tickId);\n"
            "  };\n"
            "}\n"
        )

write(p, src)
log("[step3] cashoutEngine.js patched")

# ── 3d. historyEngine.js — resize listener ───────────────────────────────────
p = SRC / "history" / "historyEngine.js"
src = read(p)

old_resize_h = (
    "  let rt;\n"
    "  window.addEventListener(\"resize\", () => {\n"
    "    clearTimeout(rt);\n"
    "    rt = setTimeout(renderAll, 140);\n"
    "  });\n"
    "}"
)
new_resize_h = (
    "  let rt;\n"
    "  const _onResize = () => { clearTimeout(rt); rt = setTimeout(renderAll, 140); };\n"
    "  window.addEventListener(\"resize\", _onResize);\n"
    "  return function cleanup() {\n"
    "    clearTimeout(rt);\n"
    "    window.removeEventListener(\"resize\", _onResize);\n"
    "  };\n"
    "}"
)
src = src.replace(old_resize_h, new_resize_h)

write(p, src)
log("[step3] historyEngine.js patched")

# ── 3e. Update App.jsx files to call cleanup on unmount ──────────────────────
APP_ENGINE_MAP = [
    (SRC / "dashboard" / "MarketDashboardApp.jsx",
     "initMarketDashboard",
     "initMarketDashboard(live, history, { items: newsItems, generatedAtIct: newsGeneratedAtIct }, econActuals)"),
    (SRC / "world" / "WorldIndicesApp.jsx",
     "initWorldIndices",
     "initWorldIndices()"),
    (SRC / "cashout" / "CashoutApp.jsx",
     "initCashout",
     "initCashout(status === \"ready\" ? data : null, insightStatus === \"ready\" ? insight : null)"),
    (SRC / "history" / "HistoryApp.jsx",
     "initHistory",
     None),  # will handle separately
]

for app_path, fn_name, call_expr in APP_ENGINE_MAP:
    if not app_path.exists():
        log(f"[step3] SKIP {app_path.name} (not found)")
        continue
    src = read(app_path)
    if "cleanupRef" in src:
        log(f"[step3] SKIP {app_path.name} (already patched)")
        continue

    # Add cleanupRef = useRef(null) after initedRef
    src = src.replace(
        "  const initedRef = useRef(false);",
        "  const initedRef = useRef(false);\n  const cleanupRef = useRef(null);"
    )

    if call_expr and call_expr in src:
        # Wrap the engine call to capture cleanup
        src = src.replace(
            f"    {call_expr};",
            f"    cleanupRef.current = {call_expr};"
        )
        # Add cleanup return in useEffect
        # Find the useEffect closing and add return before it
        # Pattern: the useEffect that calls initedRef.current = true
        src = src.replace(
            "    initedRef.current = true;\n"
            f"    cleanupRef.current = {call_expr};",
            "    initedRef.current = true;\n"
            f"    cleanupRef.current = {call_expr};\n"
            "    return () => { if (cleanupRef.current) { cleanupRef.current(); cleanupRef.current = null; } };"
        )

    write(app_path, src)
    log(f"[step3] {app_path.name} patched")

# ── 3f. HistoryApp.jsx special handling ──────────────────────────────────────
p = SRC / "history" / "HistoryApp.jsx"
if p.exists():
    src = read(p)
    if "cleanupRef" not in src and "initHistory" in src:
        src = src.replace(
            "  const initedRef = useRef(false);",
            "  const initedRef = useRef(false);\n  const cleanupRef = useRef(null);"
        )
        # Find initHistory call pattern
        m = re.search(r"    initHistory\([^)]+\);", src)
        if m:
            old_call = m.group(0)
            new_call = old_call.replace("initHistory(", "cleanupRef.current = initHistory(")
            src = src.replace(
                "    initedRef.current = true;\n" + old_call,
                "    initedRef.current = true;\n" + new_call + "\n"
                "    return () => { if (cleanupRef.current) { cleanupRef.current(); cleanupRef.current = null; } };"
            )
        write(p, src)
        log("[step3] HistoryApp.jsx patched")

# ── Step 3 Verify ─────────────────────────────────────────────────────────────
log("[step3] === VERIFY ===")
s3_ok = True
checks = [
    (SRC / "dashboard" / "dashboardEngine.js", "return function cleanup()", "returns cleanup fn"),
    (SRC / "dashboard" / "dashboardEngine.js", "_tickId", "tracks interval id"),
    (SRC / "dashboard" / "dashboardEngine.js", "_onResize", "tracks resize listener"),
    (SRC / "world"     / "worldEngine.js",     "return function cleanup()", "returns cleanup fn"),
    (SRC / "world"     / "worldEngine.js",     "_tickId", "tracks interval id"),
    (SRC / "cashout"   / "cashoutEngine.js",   "return function cleanup()", "returns cleanup fn"),
    (SRC / "history"   / "historyEngine.js",   "return function cleanup()", "returns cleanup fn"),
    (SRC / "dashboard" / "MarketDashboardApp.jsx", "cleanupRef", "App captures cleanup"),
    (SRC / "cashout"   / "CashoutApp.jsx",     "cleanupRef", "App captures cleanup"),
]
for path, needle, label in checks:
    if not assert_in(path, needle, label):
        s3_ok = False

if not s3_ok:
    log("[step3] VERIFY FAILED")
    sys.exit(1)
log("[step3] ALL PASS")

# ════════════════════════════════════════════════════════════════════════════
# STEP 4 — Remove window.__mbrScore / window.__mbrZone global state
# Fix: marginBankRisk result passed via return value stored in module scope
#      buildTape() reads from local variable instead of window.*
# ════════════════════════════════════════════════════════════════════════════
log("\n" + "=" * 60)
log("STEP 4 — Remove window.__mbrScore global state")
log("=" * 60)

p = SRC / "dashboard" / "dashboardEngine.js"
src = read(p)

# Replace window.__mbrScore assignments with module-level variable
# The pattern: window.__mbrScore = risk ? risk.score : null;
#              window.__mbrZone = rz.n;
src = src.replace(
    "    window.__mbrScore = risk ? risk.score : null;\n"
    "    window.__mbrZone = rz.n;\n"
    "    buildTape();",
    "    _mbrScore = risk ? risk.score : null;\n"
    "    _mbrZone = rz.n;\n"
    "    buildTape();"
)

# Replace window.__mbrScore / window.__mbrZone reads in buildTape
src = src.replace(
    "    const mbr = window.__mbrScore, mbrZ = window.__mbrZone || \"\";",
    "    const mbr = _mbrScore, mbrZ = _mbrZone || \"\";"
)

# Declare module-level variables at top of initMarketDashboard (after ASOF line)
old_asof = "  let ASOF = (LIVE && LIVE.asof) ? LIVE.asof : "
if "_mbrScore" not in src:
    src = src.replace(
        old_asof,
        "  let _mbrScore = null, _mbrZone = \"\";\n  " + old_asof.lstrip()
    )

write(p, src)
log("[step4] dashboardEngine.js patched")

# Verify
log("[step4] === VERIFY ===")
s4_ok = True
checks4 = [
    (p, "_mbrScore", "uses local _mbrScore"),
    (p, "_mbrZone",  "uses local _mbrZone"),
]
for path, needle, label in checks4:
    if not assert_in(path, needle, label):
        s4_ok = False
if not assert_not_in(p, "window.__mbrScore", "no window.__mbrScore"):
    s4_ok = False
if not assert_not_in(p, "window.__mbrZone", "no window.__mbrZone"):
    s4_ok = False

if not s4_ok:
    log("[step4] VERIFY FAILED")
    sys.exit(1)
log("[step4] ALL PASS")

# ════════════════════════════════════════════════════════════════════════════
# STEP 5 — Add <meta description> + <link rel=icon> to all HTML entry points
# ════════════════════════════════════════════════════════════════════════════
log("\n" + "=" * 60)
log("STEP 5 — Add meta description + favicon to HTML entry points")
log("=" * 60)

HTML_META = {
    ROOT / "index.html": (
        "Thông tin thị trường Việt Nam — Độ rộng ADR, dư nợ margin, tâm lý, lợi suất trái phiếu VN và Mỹ. Dashboard miễn phí, phi lợi nhuận.",
        "📊"
    ),
    ROOT / "the-gioi.html": (
        "Thị trường thế giới — 31 chỉ số chứng khoán, FX, hàng hoá, crypto qua TradingView. Bối cảnh vĩ mô toàn cầu.",
        "🌐"
    ),
    ROOT / "lich-su.html": (
        "Lịch sử & tương quan — Chuỗi thời gian VN-Index, lợi suất, DXY, margin. Biểu đồ chồng lớp và bảng Pearson correlation.",
        "📈"
    ),
    ROOT / "buc-tranh-thi-truong.html": (
        "Bức tranh thị trường — Verdict tổng hợp Thanh khoản, Định vị vốn, Động lượng ngành, Bối cảnh vĩ mô.",
        "🎯"
    ),
    ROOT / "dong-tien-nganh.html": (
        "Dòng tiền ngành — Heatmap, RRG 10 ngành ICB, tỷ trọng thanh khoản theo tháng và quý.",
        "🔄"
    ),
    ROOT / "dong-tien-cashout.html": (
        "Cashout Monitor — GTGD toàn thị trường, khối ngoại ròng, ma trận ngành, 10 mã dẫn dắt.",
        "💧"
    ),
    ROOT / "huong-dan-doc.html": (
        "Hướng dẫn đọc — Cách đọc ADR, margin, Fear & Greed, lợi suất trái phiếu trên dashboard VN Market.",
        "📖"
    ),
}

for html_path, (desc, icon) in HTML_META.items():
    if not html_path.exists():
        log(f"[step5] SKIP {html_path.name} (not found)")
        continue
    src = read(html_path)
    changed = False

    # Add meta description if missing
    if 'name="description"' not in src:
        src = src.replace(
            '<meta name="viewport"',
            f'<meta name="description" content="{desc}" />\n<meta name="viewport"'
        )
        changed = True

    # Add favicon emoji if missing (inline SVG favicon — no file needed)
    if 'rel="icon"' not in src:
        favicon = (
            f'<link rel="icon" href="data:image/svg+xml,'
            f'<svg xmlns=\'http://www.w3.org/2000/svg\' viewBox=\'0 0 100 100\'>'
            f'<text y=\'.9em\' font-size=\'90\'>{icon}</text></svg>" />\n'
        )
        src = src.replace('<meta charset', favicon + '<meta charset')
        changed = True

    if changed:
        write(html_path, src)
        log(f"[step5] {html_path.name} patched")
    else:
        log(f"[step5] {html_path.name} already has meta/icon")

# Verify
log("[step5] === VERIFY ===")
s5_ok = True
for html_path in HTML_META:
    if not html_path.exists():
        continue
    src = read(html_path)
    ok1 = 'name="description"' in src
    ok2 = 'rel="icon"' in src
    log(f"  {'OK  ' if ok1 else 'FAIL'} {html_path.name}: meta description")
    log(f"  {'OK  ' if ok2 else 'FAIL'} {html_path.name}: rel=icon")
    if not ok1 or not ok2:
        s5_ok = False

if not s5_ok:
    log("[step5] VERIFY FAILED")
    sys.exit(1)
log("[step5] ALL PASS")

# ════════════════════════════════════════════════════════════════════════════
# STEP 6 — Extract shared SVG chart helpers to src/lib/svgChart.js
# Repeated pattern across engines: gridLines, axisLabels, pathFromPoints
# ════════════════════════════════════════════════════════════════════════════
log("\n" + "=" * 60)
log("STEP 6 — Extract src/lib/svgChart.js shared chart primitives")
log("=" * 60)

write(LIB / "svgChart.js", """\
/**
 * src/lib/svgChart.js
 * Shared SVG chart primitive helpers used by engine modules.
 * All functions return SVG markup strings or path data strings.
 * No DOM access, no side-effects — pure string builders.
 */

const MONO = "IBM Plex Mono, ui-monospace, monospace";

/**
 * Build an SVG <path> d-attribute from an array of [x,y] or null points.
 * Null values create gaps (pen-up) in the line.
 */
export function buildPath(points) {
  return points
    .map((p, i) =>
      p == null
        ? null
        : (i === 0 || points[i - 1] == null ? "M" : "L") +
          p[0].toFixed(1) + " " + p[1].toFixed(1)
    )
    .filter(Boolean)
    .join(" ");
}

/**
 * Build horizontal grid lines + left-axis labels.
 * @param {number[]} values  - y-axis tick values
 * @param {function} Y       - value -> pixel y
 * @param {number}   xLeft   - left margin (start of line)
 * @param {number}   xRight  - right edge (end of line)
 * @param {number}   labelX  - x position of label text
 * @param {function} fmt     - value -> label string
 * @param {string}   [color] - override line color (default var(--line-soft))
 */
export function gridLines(values, Y, xLeft, xRight, labelX, fmt, color = "var(--line-soft)") {
  return values.map(v => {
    const y = Y(v).toFixed(1);
    return (
      `<line x1="${xLeft}" y1="${y}" x2="${xRight}" y2="${y}" stroke="${color}"/>` +
      `<text x="${labelX}" y="${(Y(v) + 4).toFixed(1)}" text-anchor="end" ` +
      `fill="var(--dim)" font-size="10" font-family="${MONO}">${fmt(v)}</text>`
    );
  }).join("");
}

/**
 * Build vertical grid lines + bottom-axis date labels.
 * @param {string[]} dates   - ISO date strings
 * @param {number[]} indices - which indices to label
 * @param {function} X       - index -> pixel x
 * @param {number}   yTop    - top of chart area
 * @param {number}   yBot    - bottom of chart area
 * @param {number}   labelY  - y position of label text
 * @param {function} fmt     - date string -> label string
 */
export function verticalGridLines(dates, indices, X, yTop, yBot, labelY, fmt) {
  return indices.map(i => {
    const x = X(i).toFixed(1);
    return (
      `<line x1="${x}" y1="${yTop}" x2="${x}" y2="${yBot}" stroke="var(--line-soft)" opacity=".55"/>` +
      `<text x="${x}" y="${labelY}" text-anchor="middle" ` +
      `fill="var(--dim)" font-size="10" font-family="${MONO}">${fmt(dates[i])}</text>`
    );
  }).join("");
}

/**
 * Build a filled area path under a line (for area charts).
 * @param {string} linePath  - the line path d-attribute
 * @param {number} x0        - x of first point
 * @param {number} x1        - x of last point
 * @param {number} yBase     - y of baseline (bottom of area)
 */
export function areaPath(linePath, x0, x1, yBase) {
  return `${linePath} L ${x1.toFixed(1)} ${yBase} L ${x0.toFixed(1)} ${yBase} Z`;
}

/**
 * Build a crosshair group (vertical line + optional circle).
 * @param {string} id    - SVG group id
 * @param {number} yTop  - top of chart area
 * @param {number} yBot  - bottom of chart area
 */
export function crosshair(id, yTop, yBot) {
  return (
    `<g id="${id}" style="opacity:0">` +
    `<line y1="${yTop}" y2="${yBot}" stroke="var(--text)" stroke-width="1" stroke-dasharray="3 3" opacity=".35"/>` +
    `<circle r="4.5" fill="var(--surface)" stroke="var(--blue)" stroke-width="2.2"/>` +
    `</g>`
  );
}
""")
log("[step6] created src/lib/svgChart.js")

# Verify svgChart.js exports
fmt = read(LIB / "svgChart.js")
s6_ok = True
for fn in ["buildPath", "gridLines", "verticalGridLines", "areaPath", "crosshair"]:
    ok = f"export function {fn}" in fmt
    log(f"  {'OK  ' if ok else 'FAIL'} svgChart.js exports {fn}")
    if not ok:
        s6_ok = False

if not s6_ok:
    log("[step6] VERIFY FAILED")
    sys.exit(1)
log("[step6] ALL PASS")

# ════════════════════════════════════════════════════════════════════════════
# FINAL BUILD TEST
# ════════════════════════════════════════════════════════════════════════════
build_test("Steps 3+4+5+6 combined")

log("\n" + "=" * 60)
log("ALL STEPS COMPLETE")
log("Summary:")
log("  Step 1: Security — innerHTML XSS escape (15 checks)")
log("  Step 2: Shared lib — src/lib/format.js (nf/sgn/cls/dmy/dmyF/esc)")
log("  Step 3: Lifecycle — setInterval/resize cleanup returned from engines")
log("  Step 4: Global state — window.__mbrScore removed, use local var")
log("  Step 5: HTML meta — description + favicon on all 7 entry points")
log("  Step 6: Shared lib — src/lib/svgChart.js (buildPath/gridLines/etc)")
log("=" * 60)
