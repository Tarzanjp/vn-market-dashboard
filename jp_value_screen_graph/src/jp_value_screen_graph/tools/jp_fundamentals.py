"""Kiyohara screening inputs for any JP ticker — no API key, no LLM.

The expensive part of a Kiyohara screen is not judgement, it is finding
流動資産 / 投資有価証券 / 負債合計. Those three are not on any aggregator page
that will serve us (checked 2026-09-06: irbank 403, minkabu 403,
stockanalysis 403, Yahoo's 財務 page gives prose not line items, Kabutan's
財務 page has zero occurrences of 流動資産, EDINET's API wants a paid key).
They live in the 決算短信 PDF.

The route that does work, uniformly, for every listed ticker:

  finance.yahoo.co.jp/quote/<CODE>.T/disclosure   ← mirrors TDnet per ticker
      -> pick the newest 決算短信 entry -> download its PDF -> parse

So: 4 HTTP calls and one local PDF parse per ticker, all free.

  python -m jp_value_screen_graph.tools.jp_fundamentals 5367 3951 --json

Every figure carries where it came from. Anything that cannot be fetched is
returned as None with a reason — never inferred, because a Net Cash Ratio
built on a guessed balance sheet is worse than no ratio at all.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import urllib.request
from typing import Any

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
DISCLOSURE = "https://finance.yahoo.co.jp/quote/{code}.T/disclosure"
KABUTAN = "https://kabutan.jp/stock/finance?code={code}"
CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{code}.T?range=10y&interval=1mo"


def _get(url: str, timeout: int = 25) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _text(el: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", el))).strip()


# --------------------------------------------------------------- 決算短信 PDF
def find_tanshin(code: str) -> dict:
    """Newest 決算短信 PDF for this ticker, from Yahoo's TDnet mirror."""
    try:
        page = _get(DISCLOSURE.format(code=code)).decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return {"url": None, "error": f"disclosure page: {e}"}
    items = re.findall(r'<li class="[^"]*DisclosureList__item.*?</li>', page, re.S)
    # Titles containing 決算短信 also cover amendments and cover notices that carry
    # no financial statements at all (e.g. 9347's "公認会計士等による期中レビューの
    # 完了"), and the briefing deck. Those must not be picked.
    reject = ("訂正", "レビューの完了", "説明資料", "補足", "（差替", "英文", "English")
    for it in items:  # newest first
        title = _text(it)
        if "決算短信" not in title or any(w in title for w in reject):
            continue
        m = re.search(r'href="(https://[^"]+?\.pdf)"', it)
        if m:
            return {"url": m.group(1), "title": title}
    return {"url": None, "error": f"no usable 決算短信 among {len(items)} disclosures"}


def find_annual_tanshin(code: str, max_pages: int = 4) -> dict:
    """Newest FULL-YEAR 決算短信 PDF for this ticker.

    The quarterly 短信 that find_tanshin() returns carries a balance sheet but no
    notes, and the notes are where the answers live: segment information, the
    cash-flow statement and extraordinary items. 有価証券報告書 is on EDINET, not
    on Yahoo's TDnet mirror — but the ANNUAL 短信 is, and it has all three.

    Two things this has to get right. The disclosure page shows only ~34 items,
    so a December-year-end filer's annual report is already off page 1; ?page=N
    pages further back. And 四半期/中間 titles must be excluded, or the newest
    quarterly wins again.

    Caution for the caller, not enforced here: an annual 短信 contains BOTH the
    consolidated statements and, later in the document, the parent-only (個別)
    ones. 2914's parent-only page shows a 0.8% effective tax rate and a net
    income that does not match the published figure. Check which one a table
    belongs to before reading numbers off it.
    """
    reject = ("訂正", "説明資料", "補足", "（差替", "英文", "English",
              "[Summary]", "[Updated]", "[Delayed]", "Financial Results")
    base = DISCLOSURE.format(code=code)
    for page_no in range(1, max_pages + 1):
        url = base if page_no == 1 else f"{base}?page={page_no}"
        try:
            page = _get(url).decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001
            return {"url": None, "error": f"disclosure page {page_no}: {e}"}
        for it in re.findall(r'<li class="[^"]*DisclosureList__item.*?</li>', page, re.S):
            title = _text(it)
            if "決算短信" not in title:
                continue
            if "四半期" in title or "中間" in title:
                continue
            if any(w in title for w in reject):
                continue
            m = re.search(r'href="(https://[^"]+?\.pdf)"', it)
            if m:
                return {"url": m.group(1), "title": title, "found_on_page": page_no}
    return {"url": None, "error": f"no annual 決算短信 in {max_pages} pages"}


# Anchored at line start: 負債合計 is a substring of 流動負債合計 and 固定負債合計,
# and 資産合計 of 流動資産合計 — an unanchored match silently picks the subtotal
# instead of the total, which is how a Net Cash Ratio comes out wrong while
# still looking plausible.
BS_KEYS = {
    "current_assets": r"^\s*流動資産合計",
    "investment_securities": r"^\s*投資有価証券",
    "total_liabilities": r"^\s*負債合計",
    "total_assets": r"^\s*資産合計",
    "cash": r"^\s*現金及び預金",
    # needed for the balance identity below, not for the ratio itself
    "net_assets": r"^\s*(純資産合計|資本合計)",
    "fixed_assets": r"^\s*(固定資産合計|非流動資産合計)",
}


def _figure(nums: list[str]) -> int | None:
    """The current-period figure from a balance-sheet row.

    Rows normally read (prior, current). Some IFRS layouts add composition-%
    and 増減 columns, so the last number is the change, not the period end.
    That is detectable arithmetically — if last == secondlast - thirdlast the
    filing put a delta there — which is safer than guessing by column count.
    """
    if not nums:
        return None
    v = nums[-1]
    if len(nums) >= 3:
        try:
            a, b, c = (float(x.replace(",", "").lstrip("△▲-")) for x in nums[-3:])
            if abs((b - a) - c) <= max(1.0, abs(c) * 0.001):
                v = nums[-2]
        except ValueError:
            pass
    neg = v[0] in "△▲-"
    v = v.lstrip("△▲-").replace(",", "")
    if not v.isdigit():
        return None
    return -int(v) if neg else int(v)


def _page_unit(page_text: str) -> str | None:
    """The unit this page's tables are printed in, or None.

    Most filings say （単位：百万円）. IFRS ones often instead put a bare
    column-header line — "百万円 百万円" or "百万円 ％ 百万円 ％". The unit must
    be read from the page the balance sheet is actually on: a 千円 filing can
    still mention 百万円 on an earlier summary page, and taking the first match
    anywhere scales every figure by 1000.
    """
    if re.search(r"単位[:：]\s*百万円", page_text):
        return "million"
    if re.search(r"単位[:：]\s*千円", page_text):
        return "thousand"
    for ln in page_text.split("\n"):
        if ln.strip() and re.fullmatch(r"[\s百万千円％%]+", ln):
            if "百万円" in ln:
                return "million"
            if "千円" in ln:
                return "thousand"
    return None


def _figure(nums: list[str]) -> int | None:
    """The current-period figure from a balance-sheet row.

    Rows normally read (prior, current). Some IFRS layouts add composition-%
    and 増減 columns, so the last number is the change, not the period end —
    detectable arithmetically: if last == secondlast - thirdlast, that column
    is a delta.
    """
    if not nums:
        return None
    v = nums[-1]
    if len(nums) >= 3:
        try:
            a, b, c = (float(x.replace(",", "").lstrip("△▲-")) for x in nums[-3:])
            if abs((b - a) - c) <= max(1.0, abs(c) * 0.001):
                v = nums[-2]
        except ValueError:
            pass
    neg = v[0] in "△▲-"
    v = v.lstrip("△▲-").replace(",", "")
    if not v.isdigit():
        return None
    return -int(v) if neg else int(v)


# These are totals; a negative one means the wrong column was read (usually a
# 増減 column that happened to be negative), not a real balance sheet.
NON_NEGATIVE = {"current_assets", "total_liabilities", "total_assets"}


def parse_bs(pdf_bytes: bytes) -> dict:
    """Balance-sheet lines from a 決算短信, in the unit that page states.

    Handles the layouts that otherwise corrupt the result silently:
    連結 filings split the balance sheet across two pages (assets, then
    liabilities), so every page is scanned; units differ per filing and are
    read from the page the figures came from; and IFRS filings have no
    投資有価証券 — the nearest counterpart is the NON-CURRENT その他の金融資産,
    the current line of that name being already inside 流動資産合計.
    持分法投資 stays excluded, mirroring JGAAP's separate 関係会社株式.

    A line counts only if anchored on a BS label and carrying two figures,
    which is what separates a table row from MD&A prose that also says
    負債合計 but never at the start of a line.
    """
    try:
        import pdfplumber
    except ImportError:
        return {"error": "pdfplumber not installed"}
    import io

    out: dict[str, Any] = {}
    units_seen: dict[str, str] = {}      # key -> unit of the page it came from
    ifrs_other_fin = None
    ifrs_unit = None
    in_noncurrent = False
    last_unit = None

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            # A 連結 balance sheet spans two pages and only the first repeats the
            # unit header, so a page without one inherits the nearest preceding
            # page that had it. Inheriting forward is safe (a statement does not
            # switch units mid-way); taking the first unit found anywhere in the
            # document is not — a 千円 filing can mention 百万円 on an earlier
            # summary page, which scaled every figure by 1000.
            page_unit = _page_unit(page_text) or last_unit
            if page_unit:
                last_unit = page_unit

            for line in page_text.split("\n"):
                if re.match(r"\s*流動資産合計", line):
                    in_noncurrent = True

                nums = re.findall(r"[△▲-]?[\d,]{4,}", line)
                if len(nums) < 2:
                    continue

                if (in_noncurrent and ifrs_other_fin is None
                        and re.match(r"\s*その他の金融資産", line)):
                    val = _figure(nums)
                    if val is not None and val >= 0:
                        ifrs_other_fin, ifrs_unit = val, page_unit

                for key, pat in BS_KEYS.items():
                    if key in out or not re.search(pat, line):
                        continue
                    val = _figure(nums)
                    if val is None:
                        continue
                    if key in NON_NEGATIVE and val < 0:
                        continue          # wrong column; leave it unset
                    out[key] = val
                    units_seen[key] = page_unit

    if not out:
        return {"error": "no tabular balance sheet found in PDF"}
    # NO SUBSTITUTION. 投資有価証券 does not exist in an IFRS statement of
    # financial position, so for an IFRS filer this input is 取得不可 and the
    # Kiyohara ratio is not computable as defined. Earlier this code silently
    # swapped in 非流動その他の金融資産 and still emitted a "Net Cash Ratio" —
    # that number was an approximation invented here, not the metric, and
    # labelling it a proxy did not make it a fact. The figure is still reported
    # under its own name so a human can decide what, if anything, to do with
    # it; it is never folded into the ratio.
    if ifrs_other_fin is not None:
        out["ifrs_noncurrent_other_financial_assets"] = ifrs_other_fin
        out["ifrs_note"] = (
            "IFRS filing: 投資有価証券 does not exist. Net Cash Ratio not computable "
            "as defined. 非流動その他の金融資産 reported raw, NOT substituted."
        )
        units_seen["ifrs_noncurrent_other_financial_assets"] = ifrs_unit

    # Every figure used in the ratio must have come from pages stating the same
    # unit; a mix means one of them would be scaled wrong.
    used = [units_seen.get(k) for k in
            ("current_assets", "investment_securities", "total_liabilities")
            if k in out]
    out["unit"] = used[0] if used and len(set(used)) == 1 and used[0] else "unknown"

    # A balance sheet that does not balance was read wrong. This is the only
    # check that covers the figures the ratio is actually built from — PER,
    # PBR and market cap are all derived from price and Kabutan and never
    # touch these lines, which is how a 1000x unit error passed them earlier.
    checks = {}
    a, l, n = out.get("total_assets"), out.get("total_liabilities"), out.get("net_assets")
    if a and l and n:
        checks["assets_eq_liab_plus_equity"] = {
            "lhs": a, "rhs": l + n, "diff": a - (l + n),
            "ok": abs(a - (l + n)) <= max(2, abs(a) * 0.001),
        }
    ca, fa = out.get("current_assets"), out.get("fixed_assets")
    if a and ca and fa:
        checks["current_plus_fixed_eq_total"] = {
            "lhs": ca + fa, "rhs": a, "diff": (ca + fa) - a,
            "ok": abs((ca + fa) - a) <= max(2, abs(a) * 0.001),
        }
    out["balance_checks"] = checks
    out["balances"] = bool(checks) and all(c["ok"] for c in checks.values())
    return out


# ------------------------------------------------------------------- Kabutan
def parse_kabutan(code: str) -> dict:
    try:
        s = _get(KABUTAN.format(code=code)).decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return {"error": f"kabutan: {e}"}
    tables = re.findall(r"<table.*?</table>", s, re.S)
    rows_of = [
        [_text(r) for r in re.findall(r"<tr.*?</tr>", t, re.S) if _text(r)]
        for t in tables
    ]
    out: dict[str, Any] = {}

    for rows in rows_of:
        head = rows[0] if rows else ""
        # valuation block
        if "PER" in head and "PBR" in head and len(rows) > 1:
            m = re.findall(r"([\d.]+)\s*倍", rows[1])
            if len(m) >= 2:
                out.setdefault("per", float(m[0]))
                out.setdefault("pbr", float(m[1]))
            # Large caps read "14 兆 1,159 億円" — a compound, not a single
            # number with a different suffix. Missing it leaves market cap
            # absent, and a cross-check with nothing to compare against
            # counts as "no mismatch" rather than "not checked".
            joined = " ".join(rows)
            mc = re.search(r"時価総額\s*([\d,.]+)\s*兆\s*(?:([\d,.]+)\s*億)?円", joined)
            if mc:
                cho = float(mc.group(1).replace(",", "")) * 10000
                oku = float((mc.group(2) or "0").replace(",", ""))
                out.setdefault("market_cap_oku", cho + oku)
            else:
                mc = re.search(r"時価総額\s*([\d,.]+)\s*億円", joined)
                if mc:
                    out.setdefault("market_cap_oku", float(mc.group(1).replace(",", "")))
        # annual P&L
        if head.startswith("決算期") and "最終益" in head and "発表日" in head and "annual" not in out:
            ann = []
            for r in rows[1:]:
                m = re.match(
                    r"(?:単|連)?\s*(予)?\s*(\d{4}\.\d{2})\s+([\d,\-]+)\s+([\d,\-]+)\s+"
                    r"([\d,\-]+)\s+([\d,\-]+)\s+([\d.\-]+)\s+([\d.\-]+)",
                    r,
                )
                if m:
                    n = lambda x: None if x in ("-", "") else float(x.replace(",", ""))  # noqa: E731
                    ann.append({
                        "fy": m.group(2), "forecast": bool(m.group(1)),
                        "revenue": n(m.group(3)), "op": n(m.group(4)),
                        "ordinary": n(m.group(5)), "net": n(m.group(6)),
                        "eps": n(m.group(7)), "dps": n(m.group(8)),
                    })
            if ann:
                out["annual"] = ann
        # balance-sheet summary (BPS / equity ratio / equity)
        if "１株" in head and "自己資本" in head and "総資産" in head:
            bs = []
            for r in rows[1:]:
                m = re.match(
                    r"(?:単|連|I)?\s*([\d.]+|\d{2}\.\d{2}-\d{2})\s+([\d,.]+)\s+([\d.]+)\s+"
                    r"([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d.]+)",
                    r,
                )
                if m:
                    bs.append({
                        "period": m.group(1),
                        "bps": float(m.group(2).replace(",", "")),
                        "equity_ratio": float(m.group(3)),
                        "total_assets": float(m.group(4).replace(",", "")),
                        "equity": float(m.group(5).replace(",", "")),
                        "debt_ratio": float(m.group(7)),
                    })
            if bs:
                out["bs_summary"] = bs
        # quarterly detail
        if head.startswith("決算期") and "売上営業" in head and "損益率" in head:
            q = []
            for r in rows[1:]:
                m = re.match(
                    r"(\d{2}\.\d{2}-\d{2})\s+([\d,]+)\s+([\d,\-]+)\s+([\d,\-]+)\s+([\d,\-]+)\s+([\d.\-]+)",
                    r,
                )
                if m:
                    q.append({
                        "period": m.group(1),
                        "revenue": float(m.group(2).replace(",", "")),
                        "op": float(m.group(3).replace(",", "")),
                        "ordinary": float(m.group(4).replace(",", "")),
                        "net": float(m.group(5).replace(",", "")),
                        "eps": float(m.group(6)),
                    })
            if q:
                out["quarterly"] = q[-3:]  # v2 spec: latest 3
    return out


# --------------------------------------------------------------- price series
def price_history(code: str) -> dict:
    try:
        d = json.loads(_get(CHART.format(code=code)))["chart"]["result"][0]
    except Exception as e:  # noqa: BLE001
        return {"error": f"chart: {e}"}
    ts, cl = d["timestamp"], d["indicators"]["quote"][0]["close"]
    monthly = {
        time.strftime("%Y-%m", time.gmtime(t)): round(c, 1)
        for t, c in zip(ts, cl) if c
    }
    return {"last": d["meta"].get("regularMarketPrice"), "monthly": monthly}


# ------------------------------------------------------------------ assemble
def screen(code: str) -> dict:
    r: dict[str, Any] = {"code": code, "sources": {}}

    kb = parse_kabutan(code)
    r["kabutan"] = kb
    r["sources"]["kabutan"] = KABUTAN.format(code=code)

    ph = price_history(code)
    r["price"] = ph
    r["sources"]["chart"] = "Yahoo Finance chart API"

    t = find_tanshin(code)
    r["tanshin"] = t
    if t.get("url"):
        r["sources"]["tanshin"] = t["url"]
        try:
            r["balance_sheet"] = parse_bs(_get(t["url"], timeout=40))
        except Exception as e:  # noqa: BLE001
            r["balance_sheet"] = {"error": str(e)}
    else:
        r["balance_sheet"] = {"error": t.get("error", "no tanshin")}

    # ---- Net Cash Ratio, only when every input is real
    bs, px = r.get("balance_sheet", {}), ph.get("last")
    bss = (kb.get("bs_summary") or [])
    # IFRS filers leave 1株純資産 blank ("－") on quarterly rows, so take the
    # newest row that actually carries one; equity must come from that same row
    # or shares would be derived from mismatched periods.
    row = next((b for b in reversed(bss) if b.get("bps")), None)
    eq = row["equity"] if row else None            # 百万円
    bps = row["bps"] if row else None
    need = ("current_assets", "investment_securities", "total_liabilities")
    if all(bs.get(k) for k in need) and px and eq and bps:
        div = {"thousand": 1000, "million": 1}.get(bs.get("unit"))
        if div is None:
            r["net_cash_ratio"] = {"value": None, "missing": ["unit (単位 not stated in PDF)"]}
            return r
        ca, inv, li = (bs[k] / div for k in need)   # -> 百万円
        # Prefer the published market cap. Deriving it from equity/BPS uses an
        # older annual row (IFRS filers leave BPS blank quarterly), which put
        # 6981 7% below the real figure — and market cap is the denominator of
        # the whole ratio, so that error lands directly on the answer.
        if kb.get("market_cap_oku"):
            mcap = kb["market_cap_oku"] * 100          # 億円 -> 百万円
            shares = mcap * 1_000_000 / px
            mcap_basis = "published (kabutan)"
        else:
            shares = eq * 1_000_000 / bps
            mcap = shares * px / 1_000_000             # 百万円
            mcap_basis = "derived from equity/BPS"
        ncr = (ca + inv * 0.7 - li) / mcap
        # The accounting identity is scale- and column-invariant: read every
        # line from the 増減 column and it still balances, because
        # Δassets = Δliabilities + Δequity; read every line in 千円 instead of
        # 百万円 and it still balances too. So it cannot catch the two errors
        # that actually occurred. Only an INDEPENDENT source can: Kabutan
        # publishes 総資産, parsed from HTML by a different code path, so
        # comparing it against 資産合計 from the PDF catches a wrong scale or a
        # systematically wrong column.
        ta_pdf = bs.get("total_assets")
        ta_kb = (bss[-1]["total_assets"] if bss else None)
        if ta_pdf and ta_kb and div:
            lhs = ta_pdf / div                     # -> 百万円
            off = abs(lhs - ta_kb) / ta_kb
            r["total_assets_check"] = {
                "pdf_mn": round(lhs, 1), "kabutan_mn": ta_kb,
                "off_pct": round(off * 100, 2), "ok": off <= 0.05,
            }
            if off > 0.05:
                r["net_cash_ratio"] = {
                    "value": None,
                    "missing": [f"総資産 mismatch vs Kabutan: {lhs:,.0f} vs {ta_kb:,} "
                                f"({off*100:.1f}% off) — scale or column misread"],
                }
                return r
        if bs.get("balance_checks") and not bs.get("balances"):
            r["net_cash_ratio"] = {
                "value": None,
                "missing": ["balance sheet does not balance — figures misread"],
                "balance_checks": bs["balance_checks"],
            }
            return r
        r["net_cash_ratio"] = {
            "value": round(ncr, 3),
            "formula": "(流動資産 + 投資有価証券x0.7 - 負債合計) / 時価総額",
            "current_assets_mn": round(ca, 1),
            "investment_securities_mn": round(inv, 1),
            "total_liabilities_mn": round(li, 1),
            "market_cap_mn": round(mcap, 1),
            "shares": round(shares),
            "price_used": px,
            "market_cap_basis": mcap_basis,
            "passes_kiyohara_1x": ncr > 1,
        }
        # cross-checks against Kabutan's own published figures
        chk = {}
        if kb.get("per"):
            fwd = next((a for a in kb.get("annual", []) if a["forecast"]), None)
            if fwd and fwd.get("eps"):
                chk["per_computed"] = round(px / fwd["eps"], 1)
                chk["per_published"] = kb["per"]
        if kb.get("pbr"):
            chk["pbr_computed"] = round(px / bps, 2)
            chk["pbr_published"] = kb["pbr"]
        if kb.get("market_cap_oku"):
            chk["mcap_computed_oku"] = round(mcap / 100)
            chk["mcap_published_oku"] = kb["market_cap_oku"]
        r["cross_checks"] = chk
    else:
        missing = [k for k in need if not bs.get(k)]
        if "investment_securities" in missing and bs.get("ifrs_note"):
            missing = [m for m in missing if m != "investment_securities"]
            missing.append("investment_securities (IFRS: 該当科目なし・取得不可)")
        r["net_cash_ratio"] = {
            "value": None,
            "missing": missing or [k for k, v in (("price", px), ("equity", eq)) if not v],
        }

    # ---- PER history: month-end close / that FY's EPS (the v2 re-rating input)
    per_hist = []
    monthly = ph.get("monthly", {})
    for a in kb.get("annual", []):
        if not a.get("eps"):
            continue
        y, m = a["fy"].split(".")
        key = f"{y}-{m}"
        if key in monthly:
            per_hist.append({
                "at": key, "price": monthly[key], "eps": a["eps"],
                "per": round(monthly[key] / a["eps"], 1), "forecast_eps": a["forecast"],
            })
    if px and kb.get("annual"):
        fwd = next((a for a in kb["annual"] if a["forecast"]), None)
        if fwd and fwd.get("eps"):
            per_hist.append({
                "at": "now", "price": px, "eps": fwd["eps"],
                "per": round(px / fwd["eps"], 1), "forecast_eps": True,
            })
    r["per_history"] = per_hist
    return r


def summarize(r: dict) -> str:
    kb, n = r.get("kabutan", {}), r.get("net_cash_ratio", {})
    L = [f"=== {r['code']} ==="]
    if n.get("value") is not None:
        L.append(f"  Net Cash Ratio : {n['value']}x  "
                 f"({'PASS' if n['passes_kiyohara_1x'] else 'below'} Kiyohara >1x)")
        L.append(f"     = ({n['current_assets_mn']:,} + {n['investment_securities_mn']:,}x0.7 "
                 f"- {n['total_liabilities_mn']:,}) / {n['market_cap_mn']:,} 百万円")
    else:
        L.append(f"  Net Cash Ratio : 取得不可 (missing: {', '.join(n.get('missing', []))})")
    ta = r.get("total_assets_check")
    if ta:
        L.append(f"  総資産 vs Kabutan: {ta['pdf_mn']:,} vs {ta['kabutan_mn']:,} "
                 f"({ta['off_pct']}% off) {'OK' if ta['ok'] else 'FAIL'}")
    bs = r.get("balance_sheet", {})
    if bs.get("balance_checks"):
        for name, c0 in bs["balance_checks"].items():
            L.append(f"  identity       : {name} {'OK' if c0['ok'] else 'FAIL'} "
                     f"({c0['lhs']:,} vs {c0['rhs']:,}, diff {c0['diff']:,})")
    elif r.get("net_cash_ratio", {}).get("value") is not None:
        L.append("  identity       : NOT checked (純資産合計/固定資産合計 not found)")
    c = r.get("cross_checks", {})
    # Report checked-and-passed separately from not-checked. A comparison with
    # nothing to compare against is silence, not agreement — reading it as a
    # pass is how a wrong figure gets called verified.
    pairs = [("per", "per_computed", "per_published"),
             ("pbr", "pbr_computed", "pbr_published"),
             ("mcap", "mcap_computed_oku", "mcap_published_oku")]
    done, skipped = [], []
    for name, a, b in pairs:
        if c.get(a) is not None and c.get(b) is not None:
            off = abs(c[a] - c[b]) / c[b] if c[b] else 0
            done.append(f"{name}={c[a]}/{c[b]}{'' if off <= 0.05 else ' MISMATCH'}")
        else:
            skipped.append(name)
    if done:
        L.append("  cross-check    : " + "  ".join(done))
    if skipped:
        L.append("  NOT checked    : " + ", ".join(skipped) + " (no published value to compare)")
    L.append(f"  PER {kb.get('per')}  PBR {kb.get('pbr')}  時価総額 {kb.get('market_cap_oku')}億円")
    if r.get("per_history"):
        L.append("  PER history    : " + " -> ".join(
            f"{h['at']} {h['per']}x" for h in r["per_history"]))
    if r.get("tanshin", {}).get("title"):
        L.append(f"  短信            : {r['tanshin']['title'][:56]}")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description="Kiyohara screening inputs, keyless")
    ap.add_argument("codes", nargs="+")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()
    res = []
    for i, c in enumerate(a.codes):
        if i:
            time.sleep(1.0)  # unauthenticated endpoints; stay polite
        try:
            res.append(screen(c))
        except Exception as e:  # noqa: BLE001
            res.append({"code": c, "error": str(e)})
        if not a.json:
            print(summarize(res[-1]), flush=True)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=1)
        print(f"\nwrote {a.out}")
    elif a.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
