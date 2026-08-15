#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tín hiệu tổ chức (VN30) — dữ liệu thật cho public/dong-tien-cashout.html.

Độc lập với automation/daily_update.py (cố tình chỉ dùng thư viện chuẩn, xem
automation/README.md). Cần vnstock (+pandas), giống automation/vn_cashout/ và
automation/sector_flows/.

Cài đặt: pip install -r automation/vn_insight/requirements.txt
Chạy:    py automation/vn_insight/fetch_market_insight.py

Nguồn: VCI (qua vnstock).
1. VN30F1M (hợp đồng tương lai VN30 kỳ hạn gần nhất) so với VN30 giao ngay
   → basis (chênh lệch tương lai/giao ngay) — tín hiệu định vị/áp lực
   phòng hộ (hedging) kinh điển của NĐT tổ chức, chưa từng có trên trang.
2. Giao dịch cổ đông lớn/nội bộ (company.events(), category
   MAJOR_SHAREHOLDER_TRADING) của 30 mã cấu thành VN30 (lấy động qua
   listing.symbols_by_group("VN30"), KHÔNG hardcode) — 30 ngày gần nhất.

Giới hạn cần nói rõ (không bịa số):
- Chỉ 30 mã VN30, KHÔNG phải toàn thị trường — quét company.events() cho
  toàn bộ ~1.700 mã sẽ vượt xa hạn mức 20 request/phút của vnstock guest tier.
- Tiêu đề giao dịch (title_vi/title_en) lấy NGUYÊN VĂN từ công bố thông tin
  HOSE qua vnstock — KHÔNG regex-tách số lượng cổ phiếu ra khỏi câu, vì tách
  sai một câu có nhiều định dạng khác nhau sẽ tạo ra con số trông như thật
  nhưng có thể sai — đọc trực tiếp câu gốc an toàn hơn.
- VN30 giao ngay dùng symbol "VN30" qua VCI — nếu vnstock đổi/bỏ mã này,
  script log rõ và để basis/spot = null (quality=missing), không suy đoán.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pandas as pd
from vnstock import Vnstock

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "public" / "data" / "vn-insight.json"

EVENT_LOOKBACK_DAYS = 30
# vnstock guest tier: 20 request/phút — 30 mã VN30 + 1 (VN30 spot) + 1
# (VN30F1M) ≈ 32 request tuần tự; cách quãng 3.2s/lần giữ dưới ~19 request/phút,
# cùng mức cách quãng đã dùng cho vol_ratio_for() trong vn_cashout (an toàn hơn
# mức 1.5s của sector_flows.py vì ở đây có TỚI 32 lần gọi, không phải 10).
REQUEST_SLEEP_S = 3.2


def log(msg: str) -> None:
    print(f"[vn_insight] {msg}", flush=True)


def fetch_history_latest(vs: Vnstock, symbol: str, days: int = 14) -> dict | None:
    """Trả về {close, date} của phiên gần nhất, hoặc None nếu không fetch được."""
    try:
        df = vs.stock(symbol=symbol, source="VCI").quote.history(
            start=(pd.Timestamp.today() - pd.Timedelta(days=days)).strftime("%Y-%m-%d"),
            end=pd.Timestamp.today().strftime("%Y-%m-%d"), interval="1D",
        )
        if df is None or not len(df):
            return None
        last = df.iloc[-1]
        return {"close": float(last["close"]), "date": pd.Timestamp(last["time"]).strftime("%Y-%m-%d")}
    except Exception as e:
        log(f"fetch_history_latest({symbol}) fail: {e!r}")
        return None


def fetch_vn30_basis(vs: Vnstock) -> dict:
    time.sleep(REQUEST_SLEEP_S)
    spot = fetch_history_latest(vs, "VN30")
    time.sleep(REQUEST_SLEEP_S)
    fut = fetch_history_latest(vs, "VN30F1M")

    if not spot or not fut:
        log(f"vn30 basis: spot={spot} futures={fut} — thiếu 1 trong 2, quality=missing")
        return {
            "spot": spot["close"] if spot else None,
            "futures": fut["close"] if fut else None,
            "contract": "VN30F1M",
            "basis": None,
            "basis_pct": None,
            "asof": (fut or spot or {}).get("date"),
            "quality": "missing",
        }

    basis = round(fut["close"] - spot["close"], 2)
    basis_pct = round(basis / spot["close"] * 100, 2) if spot["close"] else None
    log(f"vn30 basis: spot={spot['close']} futures={fut['close']} basis={basis} ({basis_pct}%)")
    return {
        "spot": spot["close"],
        "futures": fut["close"],
        "contract": "VN30F1M",
        "basis": basis,
        "basis_pct": basis_pct,
        "asof": fut["date"],
        "quality": "live",
    }


def fetch_insider_trades(vs: Vnstock, tickers: list[str]) -> list[dict]:
    cutoff = pd.Timestamp.today() - pd.Timedelta(days=EVENT_LOOKBACK_DAYS)
    out = []
    for sym in tickers:
        events = None
        for attempt in range(2):
            try:
                time.sleep(REQUEST_SLEEP_S)
                events = vs.stock(symbol=sym, source="VCI").company.events()
                break
            except Exception as e:
                log(f"events fail {sym} (attempt {attempt}): {e!r}")
                time.sleep(15)
        if events is None or not len(events):
            continue

        ev = events[events["category"] == "MAJOR_SHAREHOLDER_TRADING"].copy()
        if not len(ev):
            continue
        ev["display_dt"] = pd.to_datetime(ev["display_date1"], errors="coerce")
        ev = ev[ev["display_dt"] >= cutoff]
        for _, r in ev.iterrows():
            out.append({
                "ticker": sym,
                "date": r["display_dt"].strftime("%Y-%m-%d") if pd.notna(r["display_dt"]) else None,
                "direction": r.get("action_type_en") or None,
                "title_vi": r.get("event_title_vi") or None,
                "title_en": r.get("event_title_en") or None,
            })
    out.sort(key=lambda x: x["date"] or "", reverse=True)
    log(f"insider trades: {len(out)} filings trong {EVENT_LOOKBACK_DAYS} ngày qua, {len(tickers)} mã VN30")
    return out


def main() -> int:
    vs = Vnstock()

    log("fetch VN30 constituents")
    vn30_symbols = vs.stock(symbol="ACB", source="VCI").listing.symbols_by_group("VN30").tolist()
    log(f"VN30 n={len(vn30_symbols)}: {vn30_symbols}")

    vn30_basis = fetch_vn30_basis(vs)
    insider_trades = fetch_insider_trades(vs, vn30_symbols)

    payload = {
        "schemaVersion": "1.0",
        "generatedAtIct": pd.Timestamp.now(tz="Asia/Bangkok").isoformat(timespec="seconds"),
        "source": "VCI (qua thư viện mã nguồn mở vnstock) — VN30F1M futures history + company events cho 30 mã cấu thành VN30",
        "method": {
            "vn30Basis": "VN30F1M (hợp đồng gần nhất, giá đóng cửa phiên gần nhất) trừ VN30 giao ngay — số thật. basis_pct = basis/spot×100. Có thể lệch ngày nếu 1 trong 2 chưa có phiên mới nhất.",
            "insiderTrades": f"company.events() lọc category=MAJOR_SHAREHOLDER_TRADING, {EVENT_LOOKBACK_DAYS} ngày gần nhất, CHỈ 30 mã VN30 (không phải toàn thị trường, xem giới hạn API). Tiêu đề lấy nguyên văn từ công bố HOSE, không tự tách số lượng.",
        },
        "vn30": vn30_basis,
        "insiderTrades": insider_trades,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"wrote {OUT.relative_to(ROOT)} vn30.quality={vn30_basis['quality']} insiderTrades={len(insider_trades)}")
    return 0


if __name__ == "__main__":
    for _s in (sys.stdout, sys.stderr):
        if hasattr(_s, "reconfigure"):
            _s.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
