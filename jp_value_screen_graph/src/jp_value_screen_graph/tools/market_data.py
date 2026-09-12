"""Free live quotes for JP / VN / US — no API key, no LLM.

Yahoo Finance's chart endpoint is public and covers all three markets with a
suffix convention (JP `6758.T`, VN `VNM.VN`, US `AAPL`), so the plain "what is
this trading at right now" question never needs a paid model behind it. Only
judgement — is it cheap, is the earnings quality real — needs one.

A User-Agent is mandatory: without it the endpoint answers
"Edge: Too Many Requests" rather than JSON.

Usable three ways, all key-free:
  python -m jp_value_screen_graph.tools.market_data 6758 7203 --market jp
  from ...market_data import quote
  the MarketQuoteTool below, inside the CrewAI graph
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from typing import Type

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=5d&interval=1d"

# vault/market key -> Yahoo ticker suffix
SUFFIX = {"jp": ".T", "vn": ".VN", "us": ""}


def yahoo_symbol(ticker: str, market: str = "jp") -> str:
    t = ticker.strip().upper()
    suf = SUFFIX[market]
    return t if (not suf or t.endswith(suf)) else t + suf


def quote(ticker: str, market: str = "jp", *, timeout: int = 12) -> dict:
    """One quote. On failure returns {"ok": False, "error": ...} — never a guess.

    Callers must render a missing number as "—", not 0: a fabricated price is
    worse than a visibly absent one.
    """
    sym = yahoo_symbol(ticker, market)
    req = urllib.request.Request(CHART.format(sym=sym), headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            payload = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"ok": False, "ticker": ticker, "symbol": sym, "error": f"HTTP {e.code}"}
    except Exception as e:  # noqa: BLE001 — surface it, don't paper over it
        return {"ok": False, "ticker": ticker, "symbol": sym, "error": str(e)}

    res = (payload.get("chart") or {}).get("result") or []
    if not res:
        err = ((payload.get("chart") or {}).get("error") or {}).get("description", "no result")
        return {"ok": False, "ticker": ticker, "symbol": sym, "error": err}

    m = res[0].get("meta", {})
    price, prev = m.get("regularMarketPrice"), m.get("chartPreviousClose")
    pct = round((price - prev) / prev * 100, 2) if (price and prev) else None
    ts = m.get("regularMarketTime")
    return {
        "ok": True,
        "ticker": ticker,
        "symbol": sym,
        "market": market,
        "price": price,
        "prev_close": prev,
        "change_pct": pct,
        "currency": m.get("currency"),
        "exchange": m.get("fullExchangeName"),
        # as-of is not optional: a number without its timestamp is unusable
        "asof": time.strftime("%Y-%m-%d %H:%M:%S %Z", time.localtime(ts)) if ts else None,
        "source": "Yahoo Finance chart API (public, no key)",
    }


def quotes(tickers: list[str], market: str = "jp", *, pause: float = 0.3) -> list[dict]:
    out = []
    for i, t in enumerate(tickers):
        if i:
            time.sleep(pause)  # be a polite client; the endpoint is unauthenticated
        out.append(quote(t, market))
    return out


def format_table(rows: list[dict]) -> str:
    head = f"{'ticker':10} {'price':>12} {'chg%':>8} {'ccy':4} {'as of':22} exchange"
    lines = [head, "-" * len(head)]
    for r in rows:
        if not r.get("ok"):
            lines.append(f"{r['ticker']:10} {'—':>12} {'—':>8} {'—':4} {'—':22} FAILED: {r['error']}")
            continue
        lines.append(
            f"{r['ticker']:10} {r['price']!s:>12} {r['change_pct']!s:>8} "
            f"{r['currency'] or '—':4} {r['asof'] or '—':22} {r['exchange'] or '—'}"
        )
    return "\n".join(lines)


# ----------------------------------------------------------------- CrewAI tool
try:
    from crewai.tools import BaseTool
    from pydantic import BaseModel, Field

    class MarketQuoteInput(BaseModel):
        tickers: list[str] = Field(..., description="ティッカーのリスト(例 ['6758','7203'])")
        market: str = Field("jp", description="jp | vn | us")

    class MarketQuoteTool(BaseTool):
        name: str = "market_quote"
        description: str = (
            "JP/VN/US の最新株価・前日比・通貨・取得時刻を、APIキー無しの公開エンドポイント"
            "から一括取得する。株価そのものはこれで取ること — Web検索やスクレイピングで"
            "値段を探すより速く、確実で、無料。取得できなかった銘柄は FAILED と返るので、"
            "その銘柄は「取得不可」として扱い、数値を推測しないこと。"
        )
        args_schema: Type[BaseModel] = MarketQuoteInput

        def _run(self, tickers: list[str], market: str = "jp") -> str:
            return format_table(quotes(tickers, market))

except ImportError:  # stdlib-only use (CLI / Claude Code via Bash) stays available
    MarketQuoteTool = None  # type: ignore[assignment]


def main() -> int:
    ap = argparse.ArgumentParser(description="Free JP/VN/US quotes — no API key")
    ap.add_argument("tickers", nargs="+")
    ap.add_argument("--market", default="jp", choices=sorted(SUFFIX))
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    rows = quotes(a.tickers, a.market)
    print(json.dumps(rows, ensure_ascii=False, indent=1) if a.json else format_table(rows))
    return 0 if all(r.get("ok") for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
