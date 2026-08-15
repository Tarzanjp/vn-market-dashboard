#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dòng tiền theo ngành (HOSE) — tháng & quý → public/data/sector-flows.json

Đây là công cụ ĐỘC LẬP với automation/daily_update.py (vốn cố tình chỉ dùng
thư viện chuẩn Python, xem automation/README.md). Script này cần `vnstock`
(và pandas đi kèm) để lấy 10 chỉ số ngành ICB cấp 1 do HOSE công bố chính
thức, qua nguồn VCI mà vnstock bọc lại.

Chạy tự động hàng ngày cùng automation/vn_cashout/fetch_cashout_data.py
trong .github/workflows/vn-vnstock-update.yml (một lần cài vnstock, chạy
nối tiếp 2 script, commit chung). Vẫn chạy tay được nếu cần:

Cài đặt: pip install -r automation/sector_flows/requirements.txt
Chạy:    py automation/sector_flows/fetch_sector_flows.py

Dữ liệu: giá đóng cửa (close) + khối lượng (volume) hàng ngày của từng chỉ
số ngành, từ nguồn VCI (Vietcap) qua vnstock — đây là chỉ số ngành ICB cấp 1
HOSE tự tính (không phải rổ tự chọn), lịch sử có từ ~09/2019.

Giới hạn cần nói rõ (không bịa số):
- HOSE gộp Ngân hàng + Chứng khoán + Bảo hiểm chung vào VNFIN (Tài chính) —
  không có chỉ số ngành Ngân hàng riêng công khai qua nguồn này.
- "GTGD" (tỷ VND) ở đây là ƯỚC TÍNH = Σ(volume × close) mỗi ngày, không phải
  giá trị khớp lệnh thật do HOSE công bố (không có field đó trong dữ liệu
  chỉ số free) — dùng để SO SÁNH TƯƠNG ĐỐI giữa ngành/kỳ, không dùng làm số
  liệu tuyệt đối chính thức.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pandas as pd
from vnstock import Vnstock

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "public" / "data" / "sector-flows.json"

# Mã chỉ số ngành ICB cấp 1 của HOSE (nguồn VCI qua vnstock) — đã kiểm chứng
# từng mã thật qua fetch trước khi đưa vào đây.
SECTORS = [
    ("VNREAL", "Bất động sản"),
    ("VNCONS", "Xây dựng"),
    ("VNMAT", "Vật liệu"),
    ("VNENE", "Năng lượng"),
    ("VNFIN", "Tài chính (NH+CK+BH)"),
    ("VNHEAL", "Y tế"),
    ("VNIND", "Công nghiệp"),
    ("VNIT", "Công nghệ thông tin"),
    ("VNUTI", "Tiện ích"),
    ("VNCOND", "Hàng tiêu dùng"),
]
BENCHMARK = ("VNINDEX", "VN-Index")

START = "2022-01-01"

# Tham số RRG đơn giản hoá (không phải công thức JdK RS-Ratio/RS-Momentum
# gốc — xấp xỉ minh bạch, xem hàm rs_ratio_momentum() bên dưới).
RS_WINDOW = 4  # số kỳ dùng làm nền so sánh (SMA) cho RS-Ratio


def log(msg: str) -> None:
    print(f"[sector_flows] {msg}", flush=True)


def fetch_history(symbol: str) -> pd.DataFrame:
    vs = Vnstock()
    df = vs.stock(symbol=symbol, source="VCI").quote.history(
        start=START, end=pd.Timestamp.today().strftime("%Y-%m-%d"), interval="1D"
    )
    df["time"] = pd.to_datetime(df["time"])
    return df.set_index("time").sort_index()


def resample_period(df: pd.DataFrame, freq: str) -> pd.DataFrame:
    """freq: 'ME' (tháng) hoặc 'QE' (quý). Trả về close cuối kỳ + turnover ước tính."""
    close = df["close"].resample(freq).last()
    turnover_bn = (df["close"] * df["volume"]).resample(freq).sum() / 1e9
    out = pd.DataFrame({"close": close, "turnover_bn": turnover_bn})
    out["return_pct"] = out["close"].pct_change() * 100
    return out


def rs_ratio_momentum(sector_close: pd.Series, bench_close: pd.Series, window: int = RS_WINDOW):
    """Xấp xỉ minh bạch kiểu JdK RRG:
    RS = giá ngành / giá benchmark (sức mạnh tương đối).
    RS-Ratio = 100 + độ lệch % của RS hiện tại so với SMA(RS, window) — >100
      nghĩa là ngành đang mạnh hơn benchmark so với nền gần đây.
    RS-Momentum = 100 + tốc độ đổi chiều của RS-Ratio kỳ này so với kỳ trước
      — >100 nghĩa là sức mạnh tương đối đang tăng tốc (không chỉ đang mạnh).
    Đây KHÔNG phải công thức JdK RRG gốc (đã đăng ký bản quyền bởi RRG
    Research/OptunaGap) — là một xấp xỉ đơn giản, minh bạch cho mục đích
    hiển thị 4 góc phần tư Leading/Weakening/Lagging/Improving.
    """
    rs = sector_close / bench_close
    rs_sma = rs.rolling(window, min_periods=1).mean()
    rs_ratio = 100 + (rs / rs_sma - 1) * 100
    rs_momentum = 100 + rs_ratio.diff()
    return rs_ratio, rs_momentum


def build() -> dict:
    log(f"fetch benchmark {BENCHMARK[0]}")
    bench_daily = fetch_history(BENCHMARK[0])

    # Tài khoản khách (guest) của vnstock giới hạn 20 requests/phút — cách
    # quãng nhẹ giữa các mã để an toàn khi script này chạy nối tiếp cùng
    # automation/vn_cashout/fetch_cashout_data.py trong cùng một workflow.
    sector_daily = {}
    for sym, name in SECTORS:
        log(f"fetch {sym} ({name})")
        time.sleep(1.5)
        sector_daily[sym] = fetch_history(sym)

    result = {
        "schemaVersion": "1.0",
        "generatedAtIct": pd.Timestamp.now(tz="Asia/Bangkok").isoformat(timespec="seconds"),
        "source": "VCI (qua thư viện vnstock) — 10 chỉ số ngành ICB cấp 1 do HOSE tự tính, benchmark VN-Index",
        "method": {
            "turnover_bn": "Ước tính = Σ(volume × close) mỗi ngày trong kỳ / 1e9 — KHÔNG phải GTGD khớp lệnh thật do HOSE công bố, chỉ dùng so sánh tương đối giữa ngành/kỳ.",
            "return_pct": "% thay đổi giá đóng cửa cuối kỳ so với cuối kỳ trước.",
            "rrg": "Xấp xỉ đơn giản hoá kiểu JdK RS-Ratio/RS-Momentum, không phải công thức gốc — xem docstring rs_ratio_momentum() trong script.",
        },
        "sectors": [{"id": sym, "name": name} for sym, name in SECTORS],
        "benchmark": {"id": BENCHMARK[0], "name": BENCHMARK[1]},
        "monthly": [],
        "quarterly": [],
    }

    for freq_key, freq_code in (("monthly", "ME"), ("quarterly", "QE")):
        bench_p = resample_period(bench_daily, freq_code)
        sector_p = {sym: resample_period(sector_daily[sym], freq_code) for sym, _ in SECTORS}

        periods = sorted(bench_p.index)
        # Turnover share cần tổng tất cả ngành cùng kỳ
        for t in periods:
            total_turnover = sum(
                sector_p[sym]["turnover_bn"].get(t, 0.0) or 0.0 for sym, _ in SECTORS
            )
            for sym, name in SECTORS:
                row = sector_p[sym]
                if t not in row.index or pd.isna(row.loc[t, "close"]):
                    continue
                rs_ratio, rs_mom = rs_ratio_momentum(row["close"], bench_p["close"])
                period_label = t.strftime("%Y-%m") if freq_key == "monthly" else f"{t.year}-Q{(t.month - 1)//3 + 1}"
                turnover_bn = float(row.loc[t, "turnover_bn"] or 0.0)
                result[freq_key].append({
                    "period": period_label,
                    "date": t.strftime("%Y-%m-%d"),
                    "sector": sym,
                    "close": round(float(row.loc[t, "close"]), 2),
                    "return_pct": None if pd.isna(row.loc[t, "return_pct"]) else round(float(row.loc[t, "return_pct"]), 2),
                    "turnover_bn": round(turnover_bn, 1),
                    "turnover_share_pct": round(turnover_bn / total_turnover * 100, 2) if total_turnover else None,
                    "rs_ratio": None if t not in rs_ratio.index or pd.isna(rs_ratio.loc[t]) else round(float(rs_ratio.loc[t]), 2),
                    "rs_momentum": None if t not in rs_mom.index or pd.isna(rs_mom.loc[t]) else round(float(rs_mom.loc[t]), 2),
                })

    return result


def main() -> int:
    try:
        data = build()
    except Exception as e:
        log(f"FAIL: {e!r}")
        return 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"wrote {OUT.relative_to(ROOT)} monthly={len(data['monthly'])} quarterly={len(data['quarterly'])}")
    return 0


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
