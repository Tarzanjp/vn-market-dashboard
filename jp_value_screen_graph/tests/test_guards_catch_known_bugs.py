"""Reinstate the bugs that shipped wrong numbers, and prove the guards fire.

Run:  uv run python tests/test_guards_catch_known_bugs.py

A guard that has never failed is not evidence that it works. Both faults below
really happened on 2026-09-06 and both produced confident, plausible output:

  1. Units differ per filing (非連結 prints 千円, 連結 prints 百万円) and the code
     divided by 1000 unconditionally. 5367 came out as 538x instead of 0.532x.
     Every existing cross-check passed, because PER, PBR and market cap are all
     derived from price and Kabutan and never touch the balance sheet.
  2. The 負債合計 pattern was unanchored, so it matched inside 流動負債合計 and
     returned the subtotal. 0.588x instead of 0.539x — a difference small enough
     to look like a modelling choice rather than a defect.

They need different guards, and neither guard covers the other: the accounting
identity is scale- and column-invariant (read every line from the 増減 column
and Δassets still equals Δliabilities + Δequity), while the cross-source total
compares one figure and would miss a single wrong line that leaves totals
intact.
"""
import sys

from jp_value_screen_graph.tools import jp_fundamentals as jf

TICKER = "5367"
failures = []


def check(name, condition, detail=""):
    print(f"  {'PASS' if condition else 'FAIL'}  {name}  {detail}")
    if not condition:
        failures.append(name)


print(f"baseline ({TICKER})")
good = jf.screen(TICKER)
check("ratio computed", good["net_cash_ratio"]["value"] is not None,
      str(good["net_cash_ratio"]["value"]))
check("identity holds", good["balance_sheet"].get("balances") is True)
check("total assets agree with Kabutan", good["total_assets_check"]["ok"],
      f"{good['total_assets_check']['off_pct']}% off")

print("\nfault 1: unit read as 百万円 when the filing states 千円")
orig = jf.parse_bs
jf.parse_bs = lambda b: {**orig(b), "unit": "million"}
r = jf.screen(TICKER)
jf.parse_bs = orig
check("withheld", r["net_cash_ratio"]["value"] is None,
      (r["net_cash_ratio"].get("missing") or [""])[0][:60])

print("\nfault 2: 負債合計 unanchored, so it matches 流動負債合計")
saved = dict(jf.BS_KEYS)
jf.BS_KEYS["total_liabilities"] = r"負債合計"
r2 = jf.screen(TICKER)
jf.BS_KEYS.clear()
jf.BS_KEYS.update(saved)
check("subtotal was picked up", r2["balance_sheet"].get("total_liabilities") == 3_692_327)
check("identity broke", r2["balance_sheet"].get("balances") is False)
check("withheld", r2["net_cash_ratio"]["value"] is None,
      (r2["net_cash_ratio"].get("missing") or [""])[0][:60])

print("\n" + ("ALL GUARDS FIRE" if not failures else f"REGRESSED: {failures}"))
sys.exit(1 if failures else 0)
