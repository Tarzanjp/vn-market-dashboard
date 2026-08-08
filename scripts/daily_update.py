#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cập nhật dữ liệu thị trường tự động (free sources) → data/live.js
Chạy local:  py scripts/daily_update.py
Chạy CI:     GitHub Actions schedule (sau phiên VN + sáng ICT)
"""
from __future__ import annotations

import json
import re
import ssl
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
LIVE_JS = DATA / "live.js"
LIVE_JSON = DATA / "snapshot-latest.json"
META_JSON = DATA / "last-run.json"
GROK_FILL = DATA / "grok-fill.json"

ICT = timezone(timedelta(hours=7))
UA = "vn-market-dashboard-bot/1.0 (non-profit research; +https://github.com/Tarzanjp/vn-market-dashboard)"
CTX = ssl.create_default_context()


def now_ict() -> datetime:
    return datetime.now(ICT)


def log(msg: str) -> None:
    print(f"[daily_update] {msg}", flush=True)


def http_get(url: str, timeout: int = 25) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return r.read()


def http_get_json(url: str, timeout: int = 25):
    return json.loads(http_get(url, timeout).decode("utf-8", "replace"))


def load_previous() -> dict:
    if LIVE_JSON.exists():
        try:
            return json.loads(LIVE_JSON.read_text(encoding="utf-8"))
        except Exception as e:
            log(f"previous snapshot read fail: {e}")
    return {}


def fetch_us_treasury_yields(prev: dict) -> tuple[list | None, str]:
    """Daily Treasury yield curve (public CSV)."""
    import csv
    import io

    year = now_ict().year

    def parse_date(s: str):
        s = (s or "").strip().strip('"')
        for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                pass
        return None

    for y in (year, year - 1):
        url = (
            "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
            f"daily-treasury-rates.csv/{y}/all?"
            f"type=daily_treasury_yield_curve&field_tdr_date_value={y}&page&_format=csv"
        )
        try:
            text = http_get(url, timeout=30).decode("utf-8", "replace")
            reader = csv.DictReader(io.StringIO(text))
            rows = [r for r in reader if r]
            if not rows:
                continue

            def row_date(r):
                return parse_date(r.get("Date") or r.get("date") or next(iter(r.values()), ""))

            rows = [r for r in rows if row_date(r)]
            rows.sort(key=lambda r: row_date(r))
            last, prev_row = rows[-1], rows[-2] if len(rows) > 1 else None

            def get_y(row, keys):
                if not row:
                    return None
                for k in keys:
                    for hk, hv in row.items():
                        if hk and hk.strip().lower() == k.lower() and hv not in (None, "", "N/A"):
                            try:
                                return float(str(hv).replace("%", "").strip())
                            except ValueError:
                                pass
                return None

            out = []
            for keys, label, x, est in [
                (["1 Yr", "1 Year"], "1 năm", 1, True),
                (["3 Yr", "3 Year"], "3 năm", 3, False),
                (["5 Yr", "5 Year"], "5 năm", 5, False),
                (["10 Yr", "10 Year"], "10 năm", 10, False),
                (["30 Yr", "30 Year"], "30 năm", 30, False),
            ]:
                yv = get_y(last, keys)
                if yv is None:
                    continue
                y_prev = get_y(prev_row, keys)
                d = round(yv - y_prev, 2) if y_prev is not None else 0.0
                out.append(
                    {"t": label, "y": round(yv, 2), "d": d, "m": 0.0, "yr": 0.0, "x": x, "est": est}
                )
            if len(out) >= 4:
                asof = row_date(last)
                asof_s = asof.isoformat() if asof else now_ict().date().isoformat()
                log(f"US yields OK asof={asof_s} n={len(out)}")
                return out, asof_s
        except Exception as e:
            log(f"US yields year={y} fail: {e}")
    return prev.get("usYields"), prev.get("usYieldsAsof") or ""


def fetch_fg_us(prev: dict) -> tuple[dict | None, str]:
    url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
    try:
        # CNN đôi khi chặn bot — thử header giống browser
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json,text/plain,*/*",
                "Referer": "https://edition.cnn.com/markets/fear-and-greed",
                "Origin": "https://edition.cnn.com",
            },
        )
        with urllib.request.urlopen(req, timeout=20, context=CTX) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
        # structure varies; try common paths
        score = None
        hist = {}
        if isinstance(data, dict):
            fg = data.get("fear_and_greed") or data.get("fearAndGreed") or data
            if isinstance(fg, dict):
                score = fg.get("score") or fg.get("rating")
                if isinstance(score, str):
                    score = None
                # previous close fields
                hist = {
                    "prev": fg.get("previous_close") or fg.get("previousClose"),
                    "week": fg.get("previous_1_week") or fg.get("previous1Week"),
                    "month": fg.get("previous_1_month") or fg.get("previous1Month"),
                    "year": fg.get("previous_1_year") or fg.get("previous1Year"),
                }
            # alternative: data["fear_and_greed_historical"]["data"][-1]
            if score is None and "fear_and_greed_historical" in data:
                series = data["fear_and_greed_historical"].get("data") or []
                if series:
                    score = series[-1].get("y") or series[-1].get("score")
        if score is not None:
            score = round(float(score), 1)
            out = {
                "score": score,
                "hist": {
                    "prev": _num(hist.get("prev"), score),
                    "week": _num(hist.get("week"), score),
                    "month": _num(hist.get("month"), score),
                    "year": _num(hist.get("year"), score),
                },
                "asofEt": now_ict().strftime("%Y-%m-%d"),
            }
            log(f"F&G US OK score={score}")
            return out, now_ict().isoformat()
    except Exception as e:
        log(f"F&G US fail: {e}")
    return prev.get("fgUs"), prev.get("fgUsFetchedAt") or ""


def _num(v, fallback):
    try:
        if v is None:
            return fallback
        return round(float(v), 1)
    except (TypeError, ValueError):
        return fallback


def fetch_yahoo_quote(symbol: str) -> dict | None:
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib_parse_quote(symbol)}"
        f"?interval=1d&range=5d"
    )
    try:
        data = http_get_json(url, timeout=20)
        res = data["chart"]["result"][0]
        meta = res.get("meta") or {}
        closes = (res.get("indicators") or {}).get("quote", [{}])[0].get("close") or []
        ts = res.get("timestamp") or []
        # last non-null close
        price = meta.get("regularMarketPrice")
        prev_close = meta.get("chartPreviousClose") or meta.get("previousClose")
        if price is None:
            for c in reversed(closes):
                if c is not None:
                    price = c
                    break
        if price is None:
            return None
        price = float(price)
        prev = float(prev_close) if prev_close is not None else None
        chg = price - prev if prev else 0.0
        pct = (chg / prev * 100) if prev else 0.0
        trade_date = None
        if ts:
            trade_date = datetime.fromtimestamp(ts[-1], tz=timezone.utc).date().isoformat()
        return {
            "symbol": symbol,
            "price": round(price, 2),
            "prev": round(prev, 2) if prev else None,
            "chg": round(chg, 2),
            "pct": round(pct, 2),
            "date": trade_date or now_ict().date().isoformat(),
        }
    except Exception as e:
        log(f"Yahoo {symbol} fail: {e}")
        return None


def urllib_parse_quote(s: str) -> str:
    from urllib.parse import quote

    return quote(s, safe="")


def fetch_vn_index(prev: dict) -> tuple[dict | None, str]:
    # try several symbols used by Yahoo for VN
    for sym in ("^VNINDEX.VN", "VNI.VN", "^VNINDEX"):
        q = fetch_yahoo_quote(sym)
        if q:
            log(f"VN-Index OK via {sym} = {q['price']}")
            return q, now_ict().isoformat()
    return prev.get("vnIndex"), prev.get("vnIndexFetchedAt") or ""


def fetch_dxy(prev: dict) -> tuple[float | None, str]:
    q = fetch_yahoo_quote("DX-Y.NYB")
    if q:
        log(f"DXY OK = {q['price']}")
        return q["price"], now_ict().isoformat()
    return prev.get("dxy"), prev.get("dxyFetchedAt") or ""


def load_grok_fill() -> dict:
    """JSON do Grok (hoặc người) ghi vào data/grok-fill.json."""
    if not GROK_FILL.exists():
        return {}
    try:
        raw = GROK_FILL.read_text(encoding="utf-8").strip()
        if not raw or raw.startswith("//") or raw == "{}":
            return {}
        # cho phép bọc ```json ... ```
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
        data = json.loads(raw)
        if not isinstance(data, dict):
            log("grok-fill.json: root must be object")
            return {}
        log(f"grok-fill loaded asof={data.get('asof')} keys={list(data.keys())}")
        return data
    except Exception as e:
        log(f"grok-fill read fail: {e}")
        return {}


def _q(d: dict, key: str, default: str = "missing") -> str:
    q = d.get("quality") if isinstance(d.get("quality"), dict) else {}
    return str(q.get(key) or default)


def merge_grok_fill(live: dict, grok: dict) -> dict:
    """
    Merge Grok research fill.
    - API quality == live  → không bị Grok ghi đè
    - Còn lại (stale/missing/proxy) → Grok được điền, quality = proxy (hoặc theo file)
    - margin / vnYields / breadth / usdVnd / foreign: Grok điền nếu có
    """
    if not grok:
        return live

    gq = grok.get("quality") if isinstance(grok.get("quality"), dict) else {}
    notes = list(live.get("notes") or [])
    src = grok.get("sourceNotes") or grok.get("notes") or []
    if isinstance(src, list):
        notes.extend([f"Grok: {s}" for s in src if s])
    notes.append(f"Merged data/grok-fill.json asof={grok.get('asof')}")

    def api_live(field: str) -> bool:
        return (live.get("quality") or {}).get(field) == "live"

    # --- fields Grok luôn được điền nếu có (không có free API ổn định) ---
    for field in ("margin", "vnYields", "breadth", "usdVnd", "foreign"):
        if grok.get(field) not in (None, {}, []):
            live[field] = grok[field]
            live.setdefault("quality", {})[field] = gq.get(field) or "proxy"
            log(f"grok fill → {field} ({live['quality'][field]})")

    # --- fields API free: chỉ lấy Grok khi API không live ---
    for field, key in (
        ("usYields", "usYields"),
        ("fgUs", "fgUs"),
        ("vnIndex", "vnIndex"),
        ("dxy", "dxy"),
    ):
        if api_live(field):
            continue
        if grok.get(key) not in (None, {}, []):
            live[key] = grok[key]
            live.setdefault("quality", {})[field] = gq.get(field) or "proxy"
            log(f"grok fill (API stale) → {field}")

    # asof: giữ API trade date; nếu chưa có thì lấy Grok
    if grok.get("asof") and not live.get("asof"):
        live["asof"] = grok["asof"]
    live["grokFillAsof"] = grok.get("asof")
    live["notes"] = notes
    return live


def build_live(prev: dict, grok: dict | None = None) -> dict:
    quality = {}
    us_yields, us_asof = fetch_us_treasury_yields(prev)
    quality["usYields"] = "live" if us_yields and us_asof else "stale"

    fg_us, fg_at = fetch_fg_us(prev)
    quality["fgUs"] = "live" if fg_us and fg_at else "stale"

    vn_idx, vn_at = fetch_vn_index(prev)
    quality["vnIndex"] = "live" if vn_idx and vn_at else "stale"

    dxy, dxy_at = fetch_dxy(prev)
    quality["dxy"] = "live" if dxy is not None and dxy_at else "stale"

    # trade date: prefer VN index session date else ICT today
    trade_date = (vn_idx or {}).get("date") or now_ict().date().isoformat()

    live = {
        "schemaVersion": "1.0",
        "generatedAtIct": now_ict().isoformat(timespec="seconds"),
        "asof": trade_date,
        "quality": quality,
        "usYields": us_yields or prev.get("usYields"),
        "usYieldsAsof": us_asof or prev.get("usYieldsAsof"),
        "fgUs": fg_us or prev.get("fgUs"),
        "fgUsFetchedAt": fg_at or prev.get("fgUsFetchedAt"),
        "vnIndex": vn_idx or prev.get("vnIndex"),
        "vnIndexFetchedAt": vn_at or prev.get("vnIndexFetchedAt"),
        "dxy": dxy if dxy is not None else prev.get("dxy"),
        "dxyFetchedAt": dxy_at or prev.get("dxyFetchedAt"),
        # margin / VN yields / breadth: free API yếu — prev hoặc Grok
        "vnYields": prev.get("vnYields"),
        "margin": prev.get("margin"),
        "breadth": prev.get("breadth"),
        "usdVnd": prev.get("usdVnd"),
        "foreign": prev.get("foreign"),
        "notes": [
            "Nguồn free: US Treasury CSV, Yahoo Finance (VN-Index/DXY), CNN Fear & Greed.",
            "Grok fill: data/grok-fill.json (proxy) — không ghi đè field quality=live.",
        ],
    }
    return merge_grok_fill(live, grok or {})


def write_outputs(live: dict) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    LIVE_JSON.write_text(json.dumps(live, ensure_ascii=False, indent=2), encoding="utf-8")
    # live.js for browser (no CORS issue on same origin)
    payload = json.dumps(live, ensure_ascii=False)
    LIVE_JS.write_text(
        "/* auto-generated by scripts/daily_update.py — do not edit by hand */\n"
        f"window.__MARKET_LIVE = {payload};\n",
        encoding="utf-8",
    )
    meta = {
        "ok": True,
        "generatedAtIct": live.get("generatedAtIct"),
        "asof": live.get("asof"),
        "quality": live.get("quality"),
    }
    META_JSON.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"wrote {LIVE_JS.relative_to(ROOT)} and {LIVE_JSON.relative_to(ROOT)}")


def main(skip_fetch: bool = False) -> int:
    log(f"start ICT={now_ict().isoformat(timespec='seconds')} skip_fetch={skip_fetch}")
    prev = load_previous()
    grok = load_grok_fill()
    if skip_fetch:
        # chỉ merge Grok lên snapshot trước (không gọi net)
        live = dict(prev) if prev else {
            "schemaVersion": "1.0",
            "asof": now_ict().date().isoformat(),
            "quality": {},
            "notes": [],
        }
        live["generatedAtIct"] = now_ict().isoformat(timespec="seconds")
        live = merge_grok_fill(live, grok)
    else:
        live = build_live(prev, grok)
    write_outputs(live)
    q = live.get("quality") or {}
    live_count = sum(1 for v in q.values() if v == "live")
    proxy_count = sum(1 for v in q.values() if v == "proxy")
    log(f"done live={live_count} proxy={proxy_count} quality={q}")
    if live_count == 0 and proxy_count == 0 and not prev:
        log("WARN: no live/proxy data and no previous snapshot")
    return 0


if __name__ == "__main__":
    skip = "--grok-only" in sys.argv or "--skip-fetch" in sys.argv
    sys.exit(main(skip_fetch=skip))
