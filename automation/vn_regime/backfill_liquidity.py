#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backfill MỘT LẦN cho Liquidity score — không phải script chạy hàng ngày.

Vấn đề: compute_regime.py cần ≥20 phiên turnoverBn tích luỹ trong
history/regime-<year>.jsonl để tính percentile Liquidity, nhưng file này chỉ
có 1 dòng/phiên thật mỗi ngày pipeline chạy — phải chờ ~1 tháng giao dịch thật
mới đủ. Script này backfill NGAY bằng ước tính, đánh dấu rõ ràng.

Cài đặt: pip install -r automation/vn_cashout/requirements.txt (vnstock+pandas)
Chạy:    py automation/vn_regime/backfill_liquidity.py [--days 120]

Phương pháp (ƯỚC TÍNH, không phải GTGD khớp lệnh thật):
1. Lấy volume khớp lệnh lịch sử THẬT của VNINDEX qua vnstock (có từ
   2019-09-12) — đây là số cổ phiếu khớp lệnh toàn HOSE mỗi phiên, số thật.
2. VNINDEX không có cột "GTGD tỷ VND" lịch sử (chỉ OHLC + volume), nên cần
   quy đổi volume -> tỷ VND. KHÔNG dùng volume × close (close là ĐIỂM chỉ
   số, không phải giá/cổ phiếu — nếu nhân trực tiếp sẽ lệch ~75 lần so với
   GTGD thật, đã kiểm chứng bằng phiên 2026-08-14 thật trước khi viết script
   này). Thay vào đó: hiệu chỉnh hệ số quy đổi (tỷ VND / cổ phiếu) từ CHÍNH
   phiên thật gần nhất đang có trong regime-<year>.jsonl:
       scale = turnoverBn_thật / volume_VNINDEX_cùng_phiên
   rồi ước tính turnoverBn(ngày cũ) = volume_VNINDEX(ngày cũ) × scale.
3. Giới hạn: hệ số quy đổi chỉ hiệu chỉnh từ MỘT điểm dữ liệu thật duy nhất,
   giả định giá trị bình quân mỗi cổ phiếu khớp lệnh ổn định suốt giai đoạn
   backfill — đây là XẤP XỈ THÔ để percentile có nền ngay, không phải số
   khớp lệnh chính thức. Mỗi dòng backfill được đánh dấu
   turnoverQuality="estimate_backfill" — compute_regime.py công khai tỷ lệ
   thật/ước tính trong scores.liquidity.basis, KHÔNG giấu.
4. KHÔNG bao giờ ghi đè dòng đã có trong file (chỉ điền các ngày còn thiếu)
   — idempotent, chạy lại nhiều lần an toàn.
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
    print(f"[backfill_liquidity] {msg}", flush=True)


def regime_history_path(year: int) -> Path:
    return HISTORY_DIR / f"regime-{year}.jsonl"


def load_regime_history(year: int) -> dict:
    path = regime_history_path(year)
    rows = {}
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


def write_regime_history(year: int, rows: dict) -> None:
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    path = regime_history_path(year)
    with path.open("w", encoding="utf-8") as f:
        for d in sorted(rows):
            f.write(json.dumps(rows[d], ensure_ascii=False) + "\n")
    log(f"wrote {path.relative_to(ROOT)} n={len(rows)}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=120, help="Số ngày lịch (không phải phiên) lùi lại để lấy lịch sử VNINDEX")
    args = ap.parse_args()

    # Gom tất cả các năm hiện có (regime-*.jsonl) để tìm phiên thật gần nhất
    # dùng làm mốc hiệu chỉnh — không giả định năm hiện tại luôn có sẵn dòng thật.
    all_rows: dict[str, dict] = {}
    for p in sorted(HISTORY_DIR.glob("regime-*.jsonl")):
        try:
            year = int(p.stem.split("-")[1])
        except (IndexError, ValueError):
            continue
        all_rows.update(load_regime_history(year))

    live_rows = {d: r for d, r in all_rows.items() if r.get("turnoverQuality") == "live" and r.get("turnoverBn")}
    if not live_rows:
        log("FAIL: chưa có phiên turnoverQuality=live nào trong regime-*.jsonl để hiệu chỉnh hệ số quy đổi — chạy compute_regime.py trước ít nhất 1 lần.")
        return 1
    anchor_date = max(live_rows)
    anchor_turnover_bn = live_rows[anchor_date]["turnoverBn"]
    log(f"mốc hiệu chỉnh: {anchor_date} turnoverBn thật = {anchor_turnover_bn}")

    vs = Vnstock()
    end = pd.Timestamp.today()
    start = end - pd.Timedelta(days=args.days)
    df = vs.stock(symbol="VNINDEX", source="VCI").quote.history(
        start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"), interval="1D"
    )
    df["time"] = pd.to_datetime(df["time"])
    df = df.set_index("time").sort_index()

    anchor_ts = pd.Timestamp(anchor_date)
    if anchor_ts not in df.index:
        log(f"FAIL: không tìm thấy phiên mốc {anchor_date} trong lịch sử VNINDEX vừa fetch — dừng, không đoán hệ số.")
        return 1
    anchor_volume = float(df.loc[anchor_ts, "volume"])
    if anchor_volume <= 0:
        log("FAIL: volume phiên mốc = 0 — không tính được hệ số quy đổi.")
        return 1
    scale = anchor_turnover_bn / anchor_volume
    log(f"hệ số quy đổi = {scale:.6f} tỷ VND / cổ phiếu (từ phiên mốc)")

    added = 0
    for ts, row in df.iterrows():
        date = ts.strftime("%Y-%m-%d")
        if date in all_rows:
            continue  # không ghi đè phiên đã có (thật hoặc backfill trước đó)
        vol = float(row["volume"]) if pd.notna(row["volume"]) else None
        if not vol or vol <= 0:
            continue
        # Dùng all_rows làm nguồn chân lý trong bộ nhớ, ghi lại theo năm ở cuối.
        all_rows[date] = {
            "date": date,
            "turnoverBn": round(vol * scale, 1),
            "turnoverQuality": "estimate_backfill",
        }
        added += 1

    if not added:
        log("Không có phiên mới để backfill (đã đủ hoặc trùng hết với dữ liệu có sẵn).")
        return 0

    # Ghi lại theo từng năm xuất hiện trong all_rows.
    by_year: dict[int, dict] = {}
    for date, row in all_rows.items():
        year = int(date[:4])
        by_year.setdefault(year, {})[date] = row
    for year, rows in by_year.items():
        write_regime_history(year, rows)

    log(f"đã backfill {added} phiên ước tính (turnoverQuality=estimate_backfill).")
    return 0


if __name__ == "__main__":
    for _s in (sys.stdout, sys.stderr):
        if hasattr(_s, "reconfigure"):
            _s.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
