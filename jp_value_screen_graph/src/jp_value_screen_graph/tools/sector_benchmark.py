"""Sector median PER/PBR from the constituents, computed rather than looked up.

A relative-value screen needs a benchmark, and the benchmark has to come from
somewhere defensible. Kabutan lists every stock in an industry with its PER and
PBR on one page, so the median is computed here from the constituents and the
sample size is reported alongside it. Nothing is taken on faith from a summary
figure whose method is unknown.

Two things this deliberately does NOT do:

  - It does not use the mean. One 300x PER drags a mean far past anything a
    stock in that sector actually trades at.
  - It does not silently drop loss-makers. A negative or absent PER means the
    company has no earnings to price, which is information about the sector.
    Those names are excluded from the PER median (the ratio is meaningless) but
    counted and reported, so a sector that is half loss-making cannot look like
    a healthy one with a tidy median.

The industry id and market segment are read from the stock's own page rather
than guessed, because Kabutan's sector listing is per market segment: the same
industry has separate プライム / スタンダード / グロース pages and a Standard-listed
small cap should not be measured against the Prime median.

Note on 403s: Kabutan returns 403 without a User-Agent and 200 with one. A
fetcher that omits it will conclude the data is unavailable when it is not.

    uv run python -m jp_value_screen_graph.tools.sector_benchmark 3951 6504 4092
    uv run python -m jp_value_screen_graph.tools.sector_benchmark 3951 --members
"""

from __future__ import annotations

import argparse
import html
import re
import statistics
import sys
import time
import urllib.request

UA = {"User-Agent": "Mozilla/5.0"}
STOCK = "https://kabutan.jp/stock/?code={code}"
SECTOR = "https://kabutan.jp{path}"


def _get(url: str, timeout: int = 25) -> str:
    return urllib.request.urlopen(
        urllib.request.Request(url, headers=UA), timeout=timeout
    ).read().decode("utf-8", "replace")


def _text(el: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", el))).strip()


def sector_of(code: str) -> dict:
    """The stock's industry page path, industry name and market segment."""
    s = _get(STOCK.format(code=code))
    # the href arrives HTML-encoded as &amp;market=2; matching a bare & fails
    m = re.search(r'href="(/themes/\?industry=\d+(?:&(?:amp;)?market=\d+)?)"[^>]*>([^<]+)<', s)
    if not m:
        return {"error": f"{code}: no industry link on the stock page"}
    seg = re.search(r"(東証[ＰＳＧ])", _text(s))
    return {"code": code, "path": html.unescape(m.group(1)),
            "industry": m.group(2).strip(), "segment": seg.group(1) if seg else "?"}


def _page(path: str) -> tuple[list[dict], int]:
    """Every stock on the industry page with the PER and PBR Kabutan shows.

    The header and data rows do not align by index: the table carries empty
    spacer cells, 前日比 occupies two data cells against one header, and ニュース
    occupies none. Dropping empty cells and anchoring on the LAST THREE —
    ＰＥＲ, ＰＢＲ, 利回り — is stable, because a company with no earnings or no
    dividend still gets a "-" cell rather than a missing one.
    """
    s = _get(SECTOR.format(path=path))
    for t in re.findall(r"<table.*?</table>", s, re.S):
        rows = re.findall(r"<tr.*?</tr>", t, re.S)
        if not rows:
            continue
        head = [c for c in (_text(x) for x in
                re.findall(r"<t[hd].*?</t[hd]>", rows[0], re.S)) if c]
        if len(head) < 3 or head[-3:] != ["ＰＥＲ", "ＰＢＲ", "利回り"]:
            continue

        def num(v: str) -> float | None:
            v = v.replace(",", "").replace("−", "-").strip()
            try:
                return float(v)
            except ValueError:
                return None          # "-" = no earnings to price, or not disclosed

        out = []
        raw = 0
        for r in rows[1:]:
            cells = [c for c in (_text(x) for x in
                     re.findall(r"<t[hd].*?</t[hd]>", r, re.S)) if c]
            # Japanese codes are 4 characters and newer ones end in a letter
            # (285A キオクシア, 146A). Demanding 4 digits drops them silently.
            if len(cells) < 6 or not re.fullmatch(r"\d[\dA-Z]{3}", cells[0]):
                continue
            per, pbr, _yld = cells[-3], cells[-2], cells[-1]
            out.append({"code": cells[0], "name": cells[1], "segment": cells[2],
                        "per": num(per), "pbr": num(pbr)})
        for r in rows[1:]:
            if re.search(r"<t[hd]", r):
                raw += 1
        return out, raw
    return [], 0


_CACHE: dict[str, list[dict]] = {}


def constituents(path: str, pause: float = 1.2, max_pages: int = 40) -> list[dict]:
    """Every constituent, following pagination.

    The industry page serves 15 rows at a time and there is no page-size
    parameter that works (&disp/&num/&limit/&rows are all ignored) — only
    &page=N. Taking the first page alone would compute a "sector median" from
    the 15 lowest-numbered codes: 化学/東証P has 114 constituents, and page one
    stops at 4042, so 4092 is not even in its own sector sample. That number
    would look perfectly reasonable and be meaningless.
    """
    if path in _CACHE:
        return _CACHE[path]
    seen: dict[str, dict] = {}
    for n in range(1, max_pages + 1):
        url = path if n == 1 else f"{path}&page={n}"
        rows, raw = _page(url)
        fresh = [r for r in rows if r["code"] not in seen]
        for r in fresh:
            seen[r["code"]] = r
        # Stop on the PAGE's row count, not the parsed count. Counting parsed
        # rows means one unparseable row ends pagination early: 電気機器/東証P
        # has 123 constituents, and a single row (285A) failing the code
        # pattern stopped the walk at 14 of them.
        if raw < 15 or not fresh:
            break
        time.sleep(pause)
    _CACHE[path] = list(seen.values())
    return _CACHE[path]


def benchmark(code: str) -> dict:
    info = sector_of(code)
    if "error" in info:
        return info
    mem = constituents(info["path"])
    if not mem:
        return {**info, "error": "industry page carried no PER/PBR table"}

    # A non-positive PER is not a cheap stock, it is a company with no earnings
    # to price. Excluded from the median, counted in the open.
    pers = [m["per"] for m in mem if m["per"] and m["per"] > 0]
    pbrs = [m["pbr"] for m in mem if m["pbr"] and m["pbr"] > 0]
    return {
        **info, "members": len(mem),
        "per_median": round(statistics.median(pers), 1) if pers else None,
        "per_n": len(pers), "per_excluded": len(mem) - len(pers),
        "pbr_median": round(statistics.median(pbrs), 2) if pbrs else None,
        "pbr_n": len(pbrs), "pbr_excluded": len(mem) - len(pbrs),
        "_members": mem,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Sector median PER/PBR from constituents")
    ap.add_argument("codes", nargs="+")
    ap.add_argument("--members", action="store_true", help="list the constituents")
    a = ap.parse_args()

    hdr = (f"{'code':6}{'業種':14}{'市場':7}{'社数':>5}{'PER中央値':>10}{'(n)':>6}"
           f"{'PBR中央値':>10}{'(n)':>6}  自社PER  自社PBR")
    print(hdr); print("-" * (len(hdr) + 6))
    for i, code in enumerate(a.codes):
        if i:
            time.sleep(1.2)                       # unauthenticated pages
        b = benchmark(code)
        if "error" in b:
            print(f"{code:6}{b['error']}")
            continue
        me = next((m for m in b["_members"] if m["code"] == code), {})
        exc = f" ※PER算出不可 {b['per_excluded']}社" if b["per_excluded"] else ""
        print(f"{code:6}{b['industry']:14}{b['segment']:7}{b['members']:>5}"
              f"{b['per_median'] or 0:>10.1f}{b['per_n']:>6}"
              f"{b['pbr_median'] or 0:>10.2f}{b['pbr_n']:>6}"
              f"{me.get('per') or 0:>9.1f}{me.get('pbr') or 0:>9.2f}{exc}")
        if a.members:
            for m in sorted(b["_members"], key=lambda x: (x["pbr"] is None, x["pbr"])):
                mark = " <<<" if m["code"] == code else ""
                print(f"        {m['code']:6}{m['name'][:22]:24}"
                      f"PER {m['per'] or 0:>7.1f}  PBR {m['pbr'] or 0:>6.2f}{mark}")

    print("\n中央値は構成銘柄から本ツールが算出(平均ではない)。PERが0以下・欠損の銘柄は")
    print("中央値から除外し、その社数を併記している。市場区分ごとに別ページ = 別母集団。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
