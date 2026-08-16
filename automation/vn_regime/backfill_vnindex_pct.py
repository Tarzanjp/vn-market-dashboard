#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backfill MỘT LẦN cho vnIndex/vnIndexPct trong public/data/history/<year>.jsonl.

Vấn đề: automation/README.md đã ghi rõ VN-Index KHÔNG có nguồn backfill miễn
phí qua daily_update.py (Yahoo Finance chỉ trả 1d/5d cho ^VNINDEX.VN) — nên
phần lớn các dòng lịch sử trong history/<year>.jsonl có vnIndex=null,
vnIndexPct=null dù NGÀY đó đã có dòng (do usYields/dxy backfill trước đó).
Điều này làm compute_realized_vol() trong compute_regime.py chỉ tính được
trên rất ít phiên thật (n=6 thay vì hàng chục/trăm phiên).

Script này lấp field vnIndex/vnIndexPct bằng dữ liệu THẬT (không phải ước
tính — khác backfill_liquidity.py) qua vnstock (nguồn VCI có lịch sử VNINDEX
thật từ 2019-09-12, đã kiểm chứng). CHỈ điền khi field đang null, KHÔNG BAO
GIỜ ghi đè giá trị đã có (kể cả giá trị null-nhưng-đã-tính vnIndexPct từ
trước) — idempotent, chạy lại nhiều lần an toàn.

Cài đặt: pip install -r automation/vn_cashout/requirements.txt (vnstock+pandas)
Chạy:    py automation/vn_regime/backfill_vnindex_pct.py [--years 2025 2026]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
from vnstock import Vnstock

ROOT = Path(__file__).resolve().parents[2]
HISTORY_DIR = ROOT / "public" / "data" / "history"


def log(msg: str) -> None:
    print(f"[backfill_vnindex_pct] {msg}", flush=True)


def history_path(year: int) -> Path:
    return HISTORY_DIR / f"{year}.jsonl"


def load_history_year(year: int) -> dict:
    path = history_path(year)
    rows: dict[str, dict] = {}
    if not path.exists():
        return rows
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


def write_history_year(year: int, rows: dict) -> None:
    path = history_path(year)
    with path.open("w", encoding="utf-8") as f:
        for d in sorted(rows):
            f.write(json.dumps(rows[d], ensure_ascii=False) + "\n")
    log(f"wrote {path.relative_to(ROOT)} n={len(rows)}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=int, nargs="+", default=None, help="Năm cần backfill (mặc định: tất cả năm có sẵn history/<year>.jsonl)")
    args = ap.parse_args()

    years = args.years or sorted(int(p.stem) for p in HISTORY_DIR.glob("*.jsonl") if p.stem.isdigit())
    if not years:
        log("Không tìm thấy history/<year>.jsonl nào.")
        return 0

    earliest_date = min(f"{y}-01-01" for y in years)
    vs = Vnstock()
    log(f"fetch VNINDEX history thật từ {earliest_date}")
    df = vs.stock(symbol="VNINDEX", source="VCI").quote.history(
        start=earliest_date, end=pd.Timestamp.today().strftime("%Y-%m-%d"), interval="1D"
    )
    df["time"] = pd.to_datetime(df["time"])
    df = df.set_index("time").sort_index()
    df["pct"] = df["close"].pct_change() * 100

    total_filled = 0
    for year in years:
        rows = load_history_year(year)
        if not rows:
            log(f"{year}: không có history/{year}.jsonl, bỏ qua")
            continue
        filled = 0
        for date, row in rows.items():
            ts = pd.Timestamp(date)
            if ts not in df.index:
                continue  # không phải phiên giao dịch thật (T7/CN/nghỉ lễ) — bỏ qua, không đoán
            if row.get("vnIndex") is None:
                row["vnIndex"] = round(float(df.loc[ts, "close"]), 2)
                filled += 1
            if row.get("vnIndexPct") is None and pd.notna(df.loc[ts, "pct"]):
                row["vnIndexPct"] = round(float(df.loc[ts, "pct"]), 2)
        if filled:
            write_history_year(year, rows)
        else:
            log(f"{year}: không có dòng nào cần điền (đã đủ hoặc không phải phiên giao dịch)")
        total_filled += filled

    log(f"đã điền vnIndex/vnIndexPct thật cho {total_filled} dòng.")
    return 0


if __name__ == "__main__":
    for _s in (sys.stdout, sys.stderr):
        if hasattr(_s, "reconfigure"):
            _s.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
