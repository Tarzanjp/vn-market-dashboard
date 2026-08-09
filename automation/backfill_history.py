#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
One-off (rerunnable) backfill of public/data/history/<year>.jsonl using free
sources: Yahoo Finance (VN-Index, DXY daily closes) and US Treasury (full
yield-curve CSV, one file per year). VN-only fields with no free historical
source — margin debt, HOSE breadth, VN bond yields, USD/VND, foreign flows,
VN Fear&Greed — are left null / quality="missing" for backfilled dates; they
start accumulating for real once daily_update.py's append_history() runs
going forward (see automation/README.md).

Run:      py automation/backfill_history.py [--years N]   (default N=2)
Safe to re-run: upserts by date like append_history() does, and never
clobbers VN-only fields a later daily run may have already filled in for a
date this script also touches.
"""
from __future__ import annotations

import csv
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from daily_update import (  # noqa: E402  (reuse the existing pipeline's HTTP helpers/paths)
    ROOT,
    DATA,
    HISTORY_DIR,
    HISTORY_INDEX,
    HISTORY_QUALITY_FIELDS,
    http_get,
    http_get_json,
    log,
    urllib_parse_quote,
)


def fetch_treasury_year_full(year: int) -> dict[str, dict[str, float]]:
    """{date: {'1': y, '3': y, ...}} for every published trading day in `year`."""
    url = (
        "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
        f"daily-treasury-rates.csv/{year}/all?"
        f"type=daily_treasury_yield_curve&field_tdr_date_value={year}&page&_format=csv"
    )
    tenor_keys = [
        (["1 Yr", "1 Year"], "1"),
        (["3 Yr", "3 Year"], "3"),
        (["5 Yr", "5 Year"], "5"),
        (["10 Yr", "10 Year"], "10"),
        (["30 Yr", "30 Year"], "30"),
    ]
    out: dict[str, dict[str, float]] = {}
    try:
        text = http_get(url, timeout=30).decode("utf-8", "replace")
        for row in csv.DictReader(io.StringIO(text)):
            raw_date = (row.get("Date") or row.get("date") or next(iter(row.values()), "") or "").strip().strip('"')
            d = None
            for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
                try:
                    d = datetime.strptime(raw_date, fmt).date()
                    break
                except ValueError:
                    pass
            if not d:
                continue
            tenors = {}
            for keys, tkey in tenor_keys:
                wanted = {k.lower() for k in keys}
                for hk, hv in row.items():
                    if hk and hk.strip().lower() in wanted and hv not in (None, "", "N/A"):
                        try:
                            tenors[tkey] = round(float(str(hv).replace("%", "").strip()), 2)
                        except ValueError:
                            pass
                        break
            if tenors:
                out[d.isoformat()] = tenors
        log(f"treasury {year}: {len(out)} days")
    except Exception as e:
        log(f"treasury {year} fail: {e}")
    return out


def fetch_yahoo_history(symbol: str, range_: str) -> dict[str, float]:
    """{date: close} daily closes for `symbol` over `range_` (e.g. '2y')."""
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib_parse_quote(symbol)}"
        f"?interval=1d&range={range_}"
    )
    out: dict[str, float] = {}
    try:
        data = http_get_json(url, timeout=30)
        res = data["chart"]["result"][0]
        ts = res.get("timestamp") or []
        closes = (res.get("indicators") or {}).get("quote", [{}])[0].get("close") or []
        for t, c in zip(ts, closes):
            if c is None:
                continue
            d = datetime.fromtimestamp(t, tz=timezone.utc).date().isoformat()
            out[d] = round(float(c), 2)
        log(f"yahoo {symbol}: {len(out)} days")
    except Exception as e:
        log(f"yahoo {symbol} fail: {e}")
    return out


def load_year_file(year: int) -> dict[str, dict]:
    path = HISTORY_DIR / f"{year}.jsonl"
    rows: dict[str, dict] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                if row.get("date"):
                    rows[row["date"]] = row
            except json.JSONDecodeError:
                continue
    return rows


def write_year_file(year: int, rows: dict[str, dict]) -> None:
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    path = HISTORY_DIR / f"{year}.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for d in sorted(rows):
            f.write(json.dumps(rows[d], ensure_ascii=False) + "\n")
    log(f"wrote {path.relative_to(ROOT)} n={len(rows)}")


def update_history_index(years: set[int]) -> None:
    existing = set()
    if HISTORY_INDEX.exists():
        try:
            existing = set(json.loads(HISTORY_INDEX.read_text(encoding="utf-8")).get("years") or [])
        except Exception:
            pass
    all_years = sorted(existing | years)
    HISTORY_INDEX.write_text(
        json.dumps({"years": all_years}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    log(f"wrote {HISTORY_INDEX.relative_to(ROOT)} years={all_years}")


def empty_row(date: str) -> dict:
    return {
        "date": date, "vnIndex": None, "vnIndexPct": None, "dxy": None,
        "usYields": None, "vnYields": None, "fgUs": None, "fgVn": None,
        "margin": None, "marginNet": None, "breadth": None,
        "usdVndCentral": None, "foreignNet": None,
        "quality": {k: "missing" for k in HISTORY_QUALITY_FIELDS},
    }


def main(years_back: int = 2) -> int:
    this_year = datetime.now(timezone.utc).year
    target_years = list(range(this_year - years_back + 1, this_year + 1))
    log(f"backfill years={target_years}")

    treasury: dict[str, dict[str, float]] = {}
    for y in target_years:
        treasury.update(fetch_treasury_year_full(y))

    vn_index: dict[str, float] = {}
    for sym in ("^VNINDEX.VN", "VNI.VN", "^VNINDEX"):
        vn_index = fetch_yahoo_history(sym, range_=f"{years_back}y")
        if vn_index:
            log(f"VN-Index history via {sym}")
            break
    dxy = fetch_yahoo_history("DX-Y.NYB", range_=f"{years_back}y")

    all_dates = {d for d in (set(treasury) | set(vn_index) | set(dxy)) if int(d[:4]) in target_years}
    by_year: dict[int, dict[str, dict]] = {}
    for date in all_dates:
        year = int(date[:4])
        rows = by_year.setdefault(year, load_year_file(year))
        row = rows.get(date) or empty_row(date)
        if date in treasury:
            row["usYields"] = treasury[date]
            row["quality"]["usYields"] = "live"
        if date in vn_index:
            row["vnIndex"] = vn_index[date]
            row["quality"]["vnIndex"] = "live"
        if date in dxy:
            row["dxy"] = dxy[date]
            row["quality"]["dxy"] = "live"
        rows[date] = row

    # derive day-over-day vnIndexPct now that each year's full series is assembled
    for year, rows in by_year.items():
        prev_price = None
        for d in sorted(rows):
            price = rows[d].get("vnIndex")
            if price is not None and prev_price:
                rows[d]["vnIndexPct"] = round((price - prev_price) / prev_price * 100, 2)
            if price is not None:
                prev_price = price
        write_year_file(year, rows)

    update_history_index(set(by_year))
    log(f"backfill done years={sorted(by_year)}")
    return 0


if __name__ == "__main__":
    years_arg = 2
    for i, a in enumerate(sys.argv):
        if a == "--years" and i + 1 < len(sys.argv):
            try:
                years_arg = int(sys.argv[i + 1])
            except ValueError:
                pass
    sys.exit(main(years_back=years_arg))
