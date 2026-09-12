"""Rank screened tickers by fundamental quality and priced-in expectation.

There is no composite score here on purpose. A weighted score hides which fact
drove the ranking, and the weights would be invented. Instead: hard filters that
are each a single verifiable fact, then a sort on one number.

The sort key is the perpetual growth rate the current price implies. It is the
assumption-light way to express valuation: instead of asserting an intrinsic
value from a growth rate nobody knows, it inverts the model and reports what
the market is already paying for. A company priced for -2% needs less to go
right than one priced for +5.5%.

    g_implied = Ke - FCF / (market cap - net cash)

Filters come from what actually separated the nine analysed stocks:

  F1  net cash > 0          The Kiyohara ratio can be positive while the company
                            carries net debt — 6 of 23 were. Cash minus
                            borrowings minus leases is the fact.
  F2  free cash flow        A DCF cannot be built on a negative base, and two of
      positive 3/3          the nine had to have their valuation withheld.
  F3  equity ratio >= 50%   Balance-sheet room to survive a bad year.
  F4  operating margin      8 of the 9 analysed had a falling margin. Rising
      not deteriorating     revenue with flat profit is the trap this catches.

Everything the filters use is printed alongside, so a ticker that fails one can
still be judged on the rest.

IMPORTANT — this ranks; it does not conclude. The reported free cash flow can
misstate the business badly: 7244's investing outflow was mostly intercompany
lending, not capex, which made its FCF look a third of what the operations
produced. Finalists must go through the annual 決算短信 (find_annual_tanshin)
before any of this is believed. See the financial-analyst-review skill.

    uv run python -m jp_value_screen_graph.tools.rank screened.json
    uv run python -m jp_value_screen_graph.tools.rank screened.json --all
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

KE = 0.075          # 1.5% risk-free + 1.0 beta x 6.0% ERP — an assumption, see skill


def metrics(r: dict) -> dict[str, Any] | None:
    """The facts the filters and the sort are built from, or None if not computable."""
    ncr = (r.get("net_cash_ratio") or {}).get("value")
    if ncr is None:
        return None
    bs, kb = r["balance_sheet"], r["kabutan"]
    div = {"thousand": 1000, "million": 1}.get(bs.get("unit"))
    if not div or bs.get("cash") is None:
        return None

    mcap = r["net_cash_ratio"]["market_cap_mn"]
    cash = bs["cash"] / div
    debt = ((bs.get("interest_bearing_debt") or 0) + (bs.get("lease_liabilities") or 0)) / div
    net_cash = cash - debt

    cf = kb.get("cash_flow") or []
    fcfs = [c["fcf"] for c in cf]
    fcf_avg = sum(fcfs) / len(fcfs) if fcfs else None

    ann = [a for a in kb.get("annual", []) if not a["forecast"]]
    margins = [(a["fy"], a["op"] / a["revenue"] * 100)
               for a in ann if a.get("op") and a.get("revenue")]
    bss = kb.get("bs_summary") or []

    # What the price implies, given this FCF. Undefined if the enterprise is
    # valued below zero (net cash exceeds market cap) — rare and worth seeing.
    ev = mcap - net_cash
    g_implied = (KE - fcf_avg / ev) if (fcf_avg and ev > 0) else None

    return {
        "code": r["code"], "ncr": ncr, "mcap_oku": mcap / 100,
        "net_cash": net_cash, "nc_ratio": net_cash / mcap,
        "cash_pct": cash / (bs["current_assets"] / div) * 100,
        "fcf_avg": fcf_avg, "fcf_years": len(fcfs),
        "fcf_pos": sum(1 for f in fcfs if f > 0),
        "equity_ratio": bss[-1].get("equity_ratio") if bss else None,
        "margin_first": margins[0][1] if margins else None,
        "margin_last": margins[-1][1] if margins else None,
        "margin_n": len(margins),
        "per": kb.get("per"), "pbr": kb.get("pbr"),
        "g_implied": g_implied,
    }


def verdict(m: dict) -> tuple[list[str], list[str]]:
    """(passed, failed) filter names — never a number, so the reason stays visible."""
    passed, failed = [], []
    for name, ok in (
        ("F1 net cash>0", m["net_cash"] > 0),
        ("F2 FCF 3/3", m["fcf_years"] >= 3 and m["fcf_pos"] == m["fcf_years"]),
        ("F3 equity>=50%", (m["equity_ratio"] or 0) >= 50),
        ("F4 margin holding", m["margin_first"] is not None
                              and m["margin_last"] >= m["margin_first"]),
    ):
        (passed if ok else failed).append(name)
    return passed, failed


def main() -> int:
    ap = argparse.ArgumentParser(description="Rank screened tickers")
    ap.add_argument("json_file", help="output of jp_fundamentals --out")
    ap.add_argument("--all", action="store_true", help="show tickers failing filters too")
    a = ap.parse_args()

    rows = json.load(open(a.json_file, encoding="utf-8"))
    ms = [m for m in (metrics(r) for r in rows) if m]
    for m in ms:
        m["passed"], m["failed"] = verdict(m)

    clean = [m for m in ms if not m["failed"]]
    # lowest priced-in growth first: least that has to go right
    clean.sort(key=lambda m: (m["g_implied"] is None, m["g_implied"]))

    print(f"{len(rows)} tickers in file, {len(ms)} computable, "
          f"{len(clean)} pass all four filters\n")
    hdr = (f"{'code':6}{'NCR':>6}{'時価億':>8}{'正味現金/時価':>13}{'現金/流動':>10}"
           f"{'FCF黒字':>8}{'自己資本':>9}{'営業利益率':>18}{'PBR':>6}{'予PER':>7}{'織込g':>8}")
    print(hdr); print("-" * len(hdr))

    def line(m):
        g = f"{m['g_implied']*100:+.1f}%" if m["g_implied"] is not None else "—"
        fcf = f"{m['fcf_pos']}/{m['fcf_years']}"
        mg = (f"{m['margin_first']:.1f}→{m['margin_last']:.1f}%"
              if m["margin_first"] is not None else "—")
        print(f"{m['code']:6}{m['ncr']:>6.2f}{m['mcap_oku']:>8,.0f}"
              f"{m['nc_ratio']:>13.2f}{m['cash_pct']:>9.0f}%"
              f"{fcf:>8}{m['equity_ratio'] or 0:>8.0f}%"
              f"{mg:>18}{m['pbr'] or 0:>6.2f}{m['per'] or 0:>7.1f}{g:>8}")

    for m in clean:
        line(m)
    if not clean:
        print("  (none)")

    if a.all:
        print("\n--- failing at least one filter ---")
        for m in sorted(ms, key=lambda x: len(x["failed"])):
            if m["failed"]:
                line(m)
                print(f"        failed: {', '.join(m['failed'])}")

    print("\nSorted by the perpetual growth the price implies, lowest first —")
    print("the least that has to go right. NOT a buy list: reported free cash flow")
    print("can misstate the business (7244's investing outflow was intercompany")
    print("lending, not capex). Run find_annual_tanshin on finalists before believing")
    print("any of it, and apply the financial-analyst-review checklist.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
