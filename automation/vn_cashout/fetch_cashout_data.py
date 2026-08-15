#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dòng tiền & Cashout VN — dữ liệu thật cho public/dong-tien-cashout.html.

Độc lập với automation/daily_update.py (cố tình chỉ dùng thư viện chuẩn,
xem automation/README.md). Cần vnstock (+pandas).

Cài đặt: pip install -r automation/vn_cashout/requirements.txt
Chạy:    py automation/vn_cashout/fetch_cashout_data.py

Nguồn: VCI (qua vnstock) — bulk price_board cho TOÀN BỘ mã HOSE/HNX/UPCOM
trong một lần gọi (GTGD khớp lệnh tích luỹ + khối ngoại mua/bán từng mã),
cộng lịch sử 5 phiên của vài mã đại diện mỗi ngành để tính vol ratio.

Giới hạn cần nói rõ (không bịa số):
- "Tự doanh" (proprietary flow) KHÔNG có nguồn dữ liệu miễn phí qua API
  này — giữ nguyên là trường nhập tay trên trang, script này không điền.
- "5D Avg Vol Ratio" mỗi ngành là ước tính từ khối lượng của 1-3 mã đại
  diện lớn nhất ngành đó (theo GTGD hôm nay), KHÔNG phải toàn bộ ngành.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import timedelta
from pathlib import Path

import pandas as pd
from vnstock import Vnstock

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "public" / "data" / "cashout-vn.json"

# (tên ngành ICB thật, nhãn hiển thị EN) — khớp với listing.symbols_by_industries()
SECTOR_DEFS = [
    (("Ngân hàng",), "Banking", "Ngân hàng"),
    (("Bất động sản",), "Real Estate", "Bất động sản"),
    (("Vật liệu xây dựng",), "Steel & Materials", "Thép/VLXD"),
    (("Chứng khoán",), "Securities", "Chứng khoán"),
    (("Thực phẩm - Đồ uống", "Bán lẻ"), "F&B / Retail", "Bán lẻ/Thực phẩm"),
]

TICKERS = [
    ("HPG", "Thép / Steel"),
    ("TCB", "Ngân hàng / Banking"),
    ("VHM", "Bất động sản / Real Estate"),
    ("SSI", "Chứng khoán / Securities"),
]


def log(msg: str) -> None:
    print(f"[cashout_vn] {msg}", flush=True)


def num(series):
    return pd.to_numeric(series, errors="coerce").fillna(0)


def main() -> int:
    vs = Vnstock()

    log("fetch listing + industries")
    listing = vs.stock(symbol="ACB", source="VCI").listing
    industries = listing.symbols_by_industries()
    all_symbols = industries["symbol"].tolist()

    log(f"fetch bulk price_board n={len(all_symbols)}")
    board = vs.stock(symbol="ACB", source="VCI").trading.price_board(all_symbols)
    board.columns = ["_".join(c) for c in board.columns]
    board = board.merge(
        industries[["symbol", "industry_name"]],
        left_on="listing_symbol", right_on="symbol", how="left",
    )

    for col in (
        "match_accumulated_value", "match_foreign_buy_value", "match_foreign_sell_value",
        "match_match_price", "listing_ref_price",
    ):
        board[col] = num(board[col])

    total_turnover_bn = board["match_accumulated_value"].sum() / 1000  # triệu VND -> tỷ VND
    foreign_net_bn = (board["match_foreign_buy_value"].sum() - board["match_foreign_sell_value"].sum()) / 1e9
    log(f"total_turnover_bn={total_turnover_bn:.1f} foreign_net_bn={foreign_net_bn:.1f}")

    def sector_bucket(names):
        sub = board[board["industry_name"].isin(names)].copy()
        daily_value_bn = sub["match_accumulated_value"].sum() / 1000
        traded = sub[sub["match_accumulated_value"] > 0].copy()
        if len(traded) and traded["match_accumulated_value"].sum() > 0:
            traded["pct_chg"] = (traded["match_match_price"] / traded["listing_ref_price"].replace(0, pd.NA) - 1) * 100
            traded = traded.dropna(subset=["pct_chg"])
            pct_chg = (traded["pct_chg"] * traded["match_accumulated_value"]).sum() / traded["match_accumulated_value"].sum()
        else:
            pct_chg = 0.0
        top3 = sub.sort_values("match_accumulated_value", ascending=False).head(3)["listing_symbol"].tolist()
        return daily_value_bn, pct_chg, top3

    def vol_ratio_for(symbols):
        # Free/guest vnstock tier caps at 20 requests/phút — chỉ lấy lịch sử
        # của mã đại diện lớn nhất (top-1), cách quãng giữa các lần gọi để
        # không vượt hạn mức khi chạy tuần tự cho 5 ngành.
        ratios = []
        for sym in symbols[:1]:
            for attempt in range(2):
                try:
                    time.sleep(3.2)
                    df = vs.stock(symbol=sym, source="VCI").quote.history(
                        start=(pd.Timestamp.today() - timedelta(days=14)).strftime("%Y-%m-%d"),
                        end=pd.Timestamp.today().strftime("%Y-%m-%d"), interval="1D",
                    )
                    if len(df) < 6:
                        break
                    today_vol = df["volume"].iloc[-1]
                    avg5 = df["volume"].iloc[-6:-1].mean()
                    if avg5 > 0:
                        ratios.append(today_vol / avg5)
                    break
                except Exception as e:
                    log(f"vol_ratio fail {sym} (attempt {attempt}): {e!r}")
                    time.sleep(15)
        return sum(ratios) / len(ratios) if ratios else None

    sectors_out = []
    for names, label_en, label_vi in SECTOR_DEFS:
        daily_value_bn, pct_chg, top3 = sector_bucket(names)
        vr = vol_ratio_for(top3)
        log(f"sector {label_en}: value={daily_value_bn:.1f} chg={pct_chg:.2f} vol_ratio={vr} rep={top3}")
        sectors_out.append({
            "en": label_en,
            "vi": label_vi,
            "chg": round(pct_chg, 2),
            "value_bn": round(daily_value_bn, 1),
            "vol_ratio": round(vr, 2) if vr else None,
            "vol_ratio_proxy_symbols": top3,
        })

    tickers_out = []
    for sym, sector_label in TICKERS:
        row = board[board["listing_symbol"] == sym]
        if not len(row):
            log(f"ticker {sym} not found in board")
            continue
        r = row.iloc[0]
        tickers_out.append({
            "code": sym,
            "sector": sector_label,
            "foreign_buy_bn": round(r["match_foreign_buy_value"] / 1e9, 2),
            "foreign_sell_bn": round(r["match_foreign_sell_value"] / 1e9, 2),
        })

    payload = {
        "schemaVersion": "1.0",
        "generatedAtIct": pd.Timestamp.now(tz="Asia/Bangkok").isoformat(timespec="seconds"),
        "source": "VCI (qua thư viện mã nguồn mở vnstock) — bulk price_board toàn bộ mã HOSE/HNX/UPCOM",
        "method": {
            "totalTurnoverBn": "Σ GTGD khớp lệnh tích luỹ toàn bộ mã (accumulated_value), đơn vị tỷ VND — số thật từ snapshot.",
            "foreignNetBn": "Σ (foreign_buy_value − foreign_sell_value) toàn bộ mã — số thật từ snapshot, đơn vị tỷ VND.",
            "sectorValueChg": "GTGD & %thay đổi (bình quân theo GTGD) của các mã thuộc nhóm ngành ICB tương ứng — số thật.",
            "volRatio": "Ước tính từ khối lượng hôm nay / TB 5 phiên của 1-3 mã đại diện lớn nhất ngành (theo GTGD) — KHÔNG phải toàn ngành.",
            "proprietaryFlow": "Không có nguồn dữ liệu miễn phí qua API này — vẫn là trường nhập tay trên trang, script không điền.",
            "tickerForeignFlow": "foreign_buy_value / foreign_sell_value thật của từng mã, KHÔNG phải ước tính toàn bộ lệnh mua/bán (không tách được lệnh của NĐT trong nước).",
        },
        "totalTurnoverBn": round(total_turnover_bn, 1),
        "foreignNetBn": round(foreign_net_bn, 1),
        "sectors": sectors_out,
        "tickers": tickers_out,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    for _s in (sys.stdout, sys.stderr):
        if hasattr(_s, "reconfigure"):
            _s.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
