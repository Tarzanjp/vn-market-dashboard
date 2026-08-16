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

"Market Leader Flow" (tickers[]): TOP_TICKERS_N (10) mã có GTGD khớp lệnh
lớn nhất phiên — chọn ĐỘNG từ board mỗi lần chạy, không hardcode danh sách,
nên luôn phản ánh đúng nhóm mã đang dẫn dắt dòng tiền hôm nay.

Cũng trích thêm (từ CHÍNH bulk price_board đã gọi — không tốn thêm request):
- Room ngoại còn lại (match_current_room/match_total_room, đơn vị cổ phiếu)
  cho 10 mã trên + danh sách "Sắp cạn room ngoại" (top 8 mã thanh khoản đủ
  lớn, room % thấp nhất, toàn thị trường).
- Top-of-book bid/ask (giá + khối lượng mức 1) cho 10 mã trên — độ sâu
  thanh khoản thô, dùng ước tính spread khi cần đặt lệnh khối lượng lớn.

Giới hạn cần nói rõ (không bịa số):
- "Tự doanh" (proprietary flow) KHÔNG có nguồn dữ liệu miễn phí qua API
  này. Thay vào đó, script đọc public/data/live.json (ghi bởi
  automation/daily_update.py) và lấy field "proprietary" NẾU nó của đúng
  phiên hôm nay (asof khớp ngày ICT hiện tại) — field đó do agent/Grok
  nghiên cứu công khai điền, quality=proxy, xem merge_grok_fill() trong
  daily_update.py. Vì báo chí VN rất hiếm khi công bố số tự doanh theo
  phiên, trường này sẽ THƯỜNG XUYÊN là None ("missing") — đó là hành vi
  đúng (thà "—" còn hơn bịa số), không phải lỗi.
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
LIVE_JSON = ROOT / "public" / "data" / "live.json"

# (tên ngành ICB thật, nhãn hiển thị EN) — khớp với listing.symbols_by_industries()
SECTOR_DEFS = [
    (("Ngân hàng",), "Banking", "Ngân hàng"),
    (("Bất động sản",), "Real Estate", "Bất động sản"),
    (("Vật liệu xây dựng",), "Steel & Materials", "Thép/VLXD"),
    (("Chứng khoán",), "Securities", "Chứng khoán"),
    (("Thực phẩm - Đồ uống", "Bán lẻ"), "F&B / Retail", "Bán lẻ/Thực phẩm"),
]

# "Market Leader Flow" — top N mã theo GTGD khớp lệnh toàn thị trường hôm nay,
# chọn ĐỘNG từ board đã fetch sẵn (không hardcode danh sách cố định) để luôn
# phản ánh đúng dòng tiền dẫn dắt phiên hiện tại thay vì lệch theo 1 rổ cũ.
TOP_TICKERS_N = 10

# "Năng lực hấp thụ vốn" (capacity) — quy ước participation-rate ≤15% GTGD/phiên
# (phổ biến ở bàn giao dịch tổ chức để giảm market impact) và các mốc vốn MINH
# HOẠ (không phải khuyến nghị quy mô vị thế — người đọc tự quy đổi theo vốn
# thật). Xem capacity_days() trong main() cho công thức.
CAPACITY_PARTICIPATION_PCT = 0.15
CAPACITY_TIERS_BN = [500, 2000, 5000]
CAPACITY_TICKER_TIER_BN = 500

# Field dùng để tính leadersRollup — trung bình theo tỷ trọng GTGD của 10 mã
# dẫn dắt, KHÔNG phải toàn thị trường (xem method["leadersRollup"] ở payload).
LEADERS_ROLLUP_FIELDS = ["pe", "pb", "roe", "foreigner_pct", "state_pct", "free_float_pct"]


def log(msg: str) -> None:
    print(f"[cashout_vn] {msg}", flush=True)


def num(series):
    return pd.to_numeric(series, errors="coerce").fillna(0)


def load_proprietary_from_live(today_ict: str) -> tuple[float | None, str]:
    """
    Đọc public/data/live.json (ghi bởi daily_update.py) để lấy field
    "proprietary" (tự doanh, agent-sourced qua grok-fill.json merge) NẾU nó
    của đúng phiên hôm nay. Không carry-forward từ ngày khác — tránh lặp lại
    vô hạn một số cũ dưới nhãn "proxy" mỗi ngày (cùng lý do với
    merge_grok_fill() trong daily_update.py).
    Trả về (net_tỷ_VND | None, quality: "proxy" | "missing").
    """
    if not LIVE_JSON.exists():
        log("live.json không tồn tại — proprietaryNetBn = missing")
        return None, "missing"
    try:
        live = json.loads(LIVE_JSON.read_text(encoding="utf-8"))
    except Exception as e:
        log(f"live.json đọc lỗi: {e!r} — proprietaryNetBn = missing")
        return None, "missing"

    if live.get("asof") != today_ict:
        log(f"live.json asof={live.get('asof')} khác hôm nay ({today_ict}) — proprietaryNetBn = missing")
        return None, "missing"

    quality = (live.get("quality") or {}).get("proprietary")
    if quality not in ("proxy", "live"):
        log(f"live.json proprietary quality={quality!r} — proprietaryNetBn = missing")
        return None, "missing"

    net = (live.get("proprietary") or {}).get("net")
    if not isinstance(net, (int, float)):
        log("live.json proprietary.net không phải số — proprietaryNetBn = missing")
        return None, "missing"

    log(f"proprietaryNetBn={net} (proxy, từ live.json asof={today_ict})")
    return float(net), "proxy"


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
        "match_current_room", "match_total_room",
        "bid_ask_bid_1_price", "bid_ask_bid_1_volume",
        "bid_ask_ask_1_price", "bid_ask_ask_1_volume",
        "listing_listed_share",
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

    # Nhãn ngành cho 10 mã dẫn dắt: dùng đúng nhãn EN/VI đã định nghĩa ở
    # SECTOR_DEFS nếu mã thuộc 1 trong 5 ngành đó; ngoài ra hiển thị NGUYÊN
    # VĂN tên ngành ICB thật từ industries (không tự dịch/bịa nhãn EN).
    sector_label_by_industry = {}
    for names, label_en, label_vi in SECTOR_DEFS:
        for n in names:
            sector_label_by_industry[n] = f"{label_vi} / {label_en}"

    def sector_label_for(industry_name):
        return sector_label_by_industry.get(industry_name, industry_name or "—")

    def room_pct(current, total):
        return round(float(current) / float(total) * 100, 1) if total and total > 0 else None

    def spread_pct(bid1, ask1):
        return round((float(ask1) - float(bid1)) / float(bid1) * 100, 2) if bid1 and bid1 > 0 else None

    def pct_field(row, col):
        v = row.get(col)
        return round(float(v) * 100, 1) if v is not None and pd.notna(v) else None

    def capacity_days(capital_bn: float, turnover_bn, participation_pct: float):
        """Số phiên cần để giải ngân/rút `capital_bn` tỷ VND nếu tự giới hạn ở
        `participation_pct` GTGD/phiên (participation-rate heuristic — quy ước
        bàn giao dịch tổ chức phổ biến là giới hạn ≤10-20%/phiên để giảm market
        impact). Dùng GTGD CỦA ĐÚNG PHIÊN HÔM NAY (snapshot 1 phiên/lần chạy,
        KHÔNG phải ADTV nhiều phiên). Đây là cơ học thực thi lệnh, KHÔNG phải
        khuyến nghị quy mô vị thế.
        Golden case tính tay: capacity_days(500, 200, 0.15) = 500/(200*0.15) = 16.7."""
        if not turnover_bn or turnover_bn <= 0:
            return None
        return round(capital_bn / (turnover_bn * participation_pct), 1)

    def fetch_fundamentals(sym: str) -> dict:
        """P/E, P/B, ROE (company.ratio_summary, dòng TTM mới nhất — báo cáo
        theo quý, có độ trễ so với ngày công bố thật) + % sở hữu nước ngoài/
        nhà nước/free-float (company.trading_stats) — 2 request MỚI/mã (không
        có trong bulk price_board). Retry 1 lần rồi bỏ qua nếu lỗi, không làm
        hỏng cả lượt chạy vì 1 mã lỗi tạm thời."""
        out = {"pe": None, "pb": None, "roe": None,
               "foreigner_pct": None, "state_pct": None, "free_float_pct": None}
        for attempt in range(2):
            try:
                time.sleep(3.2)
                ratio = vs.stock(symbol=sym, source="VCI").company.ratio_summary()
                if ratio is not None and len(ratio):
                    last = ratio.iloc[-1]
                    out["pe"] = round(float(last["pe"]), 2) if pd.notna(last.get("pe")) else None
                    out["pb"] = round(float(last["pb"]), 2) if pd.notna(last.get("pb")) else None
                    out["roe"] = pct_field(last, "roe")
                break
            except Exception as e:
                log(f"ratio_summary fail {sym} (attempt {attempt}): {e!r}")
                time.sleep(15)
        for attempt in range(2):
            try:
                time.sleep(3.2)
                stats = vs.stock(symbol=sym, source="VCI").company.trading_stats()
                if stats is not None and len(stats):
                    r0 = stats.iloc[0]
                    out["foreigner_pct"] = pct_field(r0, "foreigner_percentage")
                    out["state_pct"] = pct_field(r0, "state_percentage")
                    out["free_float_pct"] = pct_field(r0, "free_float_percentage")
                break
            except Exception as e:
                log(f"trading_stats fail {sym} (attempt {attempt}): {e!r}")
                time.sleep(15)
        return out

    top_tickers_board = board.sort_values("match_accumulated_value", ascending=False).head(TOP_TICKERS_N)
    tickers_out = []
    ticker_turnovers_bn = []  # song song với tickers_out — dùng làm trọng số cho leadersRollup
    for _, r in top_tickers_board.iterrows():
        bid1, ask1 = r["bid_ask_bid_1_price"], r["bid_ask_ask_1_price"]
        sym = r["listing_symbol"]
        log(f"fetch fundamentals {sym}")
        fundamentals = fetch_fundamentals(sym)
        ticker_turnover_bn = r["match_accumulated_value"] / 1000
        tickers_out.append({
            "code": sym,
            "sector": sector_label_for(r["industry_name"]),
            "foreign_buy_bn": round(r["match_foreign_buy_value"] / 1e9, 2),
            "foreign_sell_bn": round(r["match_foreign_sell_value"] / 1e9, 2),
            "foreign_room_pct": room_pct(r["match_current_room"], r["match_total_room"]),
            "bid1_price": float(bid1) if bid1 else None,
            "bid1_vol": float(r["bid_ask_bid_1_volume"]) if bid1 else None,
            "ask1_price": float(ask1) if ask1 else None,
            "ask1_vol": float(r["bid_ask_ask_1_volume"]) if ask1 else None,
            "spread_pct": spread_pct(bid1, ask1),
            **fundamentals,
            "capacity_days_500bn": capacity_days(CAPACITY_TICKER_TIER_BN, ticker_turnover_bn, CAPACITY_PARTICIPATION_PCT),
        })
        ticker_turnovers_bn.append(ticker_turnover_bn)
    log(f"top {TOP_TICKERS_N} tickers theo GTGD: {[t['code'] for t in tickers_out]}")

    # leadersRollup — trung bình theo tỷ trọng GTGD phiên hôm nay (turnover-
    # weighted) của các field fundamentals/ownership trên 10 mã dẫn dắt, chỉ
    # trên giá trị không null (tự chuẩn hoá lại trọng số khi có mã null). Đây
    # là universe top-10-theo-GTGD (tickers_out), KHÁC universe top-10-theo-
    # VỐN-HOÁ của market_concentration["topStocks"] bên dưới — không gộp nhầm.
    def _weighted_avg(field: str):
        pairs = [(t[field], w) for t, w in zip(tickers_out, ticker_turnovers_bn) if t.get(field) is not None and w]
        total_w = sum(w for _, w in pairs)
        return round(sum(v * w for v, w in pairs) / total_w, 2) if total_w else None

    leaders_rollup = {
        "n": len(tickers_out),
        "weightBasis": "GTGD phiên hôm nay của từng mã (turnover-weighted)",
        **{field: _weighted_avg(field) for field in LEADERS_ROLLUP_FIELDS},
    }

    # "Sắp cạn room ngoại" — quét TOÀN BỘ board đã fetch sẵn (không gọi thêm
    # request), lọc mã có room ngoại > 0 (đủ điều kiện sở hữu nước ngoài) và
    # đủ thanh khoản (≥5 tỷ VND/phiên, tránh mã ít giao dịch làm nhiễu danh
    # sách), sắp theo room % còn lại tăng dần — nhóm 8 mã foreign investor sắp
    # hết room mua thêm trên sàn (phải giao dịch thoả thuận nếu muốn mua tiếp).
    room_board = board.copy()
    room_board["room_pct_val"] = room_board.apply(
        lambda r: room_pct(r["match_current_room"], r["match_total_room"]), axis=1
    )
    room_board["turnover_bn_val"] = room_board["match_accumulated_value"] / 1000
    room_board = room_board[
        room_board["match_total_room"].gt(0) & room_board["room_pct_val"].notna()
        & room_board["turnover_bn_val"].ge(5)
    ].sort_values("room_pct_val", ascending=True)
    foreign_room_watch = [
        {
            "code": rr["listing_symbol"],
            "room_pct": rr["room_pct_val"],
            "turnover_bn": round(rr["turnover_bn_val"], 1),
        }
        for _, rr in room_board.head(8).iterrows()
    ]

    # Mức độ cô đặc vốn hoá — quét TOÀN BỘ board đã fetch sẵn (0 request mới).
    # market_cap = số CP niêm yết × giá (khớp lệnh gần nhất, hoặc giá tham
    # chiếu nếu mã chưa khớp lệnh phiên này — tránh loại nhầm blue-chip ít
    # thanh khoản khỏi bảng cô đặc). Công thức đã kiểm chứng khớp với
    # company.trading_stats().market_cap của HPG trước khi đưa vào script.
    cap_board = board.copy()
    cap_board["price_for_cap"] = cap_board["match_match_price"].where(
        cap_board["match_match_price"] > 0, cap_board["listing_ref_price"]
    )
    cap_board["market_cap_bn"] = cap_board["listing_listed_share"] * cap_board["price_for_cap"] / 1e9
    cap_board = cap_board[cap_board["market_cap_bn"] > 0].sort_values("market_cap_bn", ascending=False)
    total_cap_bn = cap_board["market_cap_bn"].sum()
    top10_cap = cap_board.head(10)
    top5_pct = round(cap_board.head(5)["market_cap_bn"].sum() / total_cap_bn * 100, 1) if total_cap_bn else None
    top10_pct = round(top10_cap["market_cap_bn"].sum() / total_cap_bn * 100, 1) if total_cap_bn else None
    market_concentration = {
        "top5Pct": top5_pct,
        "top10Pct": top10_pct,
        "topStocks": [
            {
                "code": r["listing_symbol"],
                "marketCapBn": round(r["market_cap_bn"], 1),
                "weightPct": round(r["market_cap_bn"] / total_cap_bn * 100, 2) if total_cap_bn else None,
            }
            for _, r in top10_cap.iterrows()
        ],
    }
    log(f"market cap concentration: top5={top5_pct}% top10={top10_pct}% (tổng vốn hoá ước tính {total_cap_bn:.0f} tỷ VND)")

    # Năng lực hấp thụ vốn cấp thị trường — cùng công thức capacity_days(),
    # dùng total_turnover_bn đã tính ở trên (không request thêm). Mốc vốn là
    # MINH HOẠ để người đọc tự quy đổi theo vốn thật, không phải khuyến nghị.
    capacity = {
        "participationPct": round(CAPACITY_PARTICIPATION_PCT * 100, 1),
        "tiers": [
            {"capitalBn": tier, "days": capacity_days(tier, total_turnover_bn, CAPACITY_PARTICIPATION_PCT)}
            for tier in CAPACITY_TIERS_BN
        ],
    }

    generated_at = pd.Timestamp.now(tz="Asia/Bangkok")
    today_ict = generated_at.date().isoformat()
    proprietary_net_bn, proprietary_quality = load_proprietary_from_live(today_ict)

    payload = {
        "schemaVersion": "1.0",
        "generatedAtIct": generated_at.isoformat(timespec="seconds"),
        "source": "VCI (qua thư viện mã nguồn mở vnstock) — bulk price_board toàn bộ mã HOSE/HNX/UPCOM",
        "method": {
            "totalTurnoverBn": "Σ GTGD khớp lệnh tích luỹ toàn bộ mã (accumulated_value), đơn vị tỷ VND — số thật từ snapshot.",
            "foreignNetBn": "Σ (foreign_buy_value − foreign_sell_value) toàn bộ mã — số thật từ snapshot, đơn vị tỷ VND.",
            "sectorValueChg": "GTGD & %thay đổi (bình quân theo GTGD) của các mã thuộc nhóm ngành ICB tương ứng — số thật.",
            "volRatio": "Ước tính từ khối lượng hôm nay / TB 5 phiên của 1-3 mã đại diện lớn nhất ngành (theo GTGD) — KHÔNG phải toàn ngành.",
            "proprietaryFlow": "Không có nguồn dữ liệu miễn phí qua API này. Lấy từ public/data/live.json field 'proprietary' (agent nghiên cứu công khai, xem daily_update.py merge_grok_fill), CHỈ khi cùng phiên hôm nay — quality=proxy. Không có nguồn cùng ngày → null (quality=missing), KHÔNG bịa/carry-forward.",
            "tickerForeignFlow": "foreign_buy_value / foreign_sell_value thật của từng mã, KHÔNG phải ước tính toàn bộ lệnh mua/bán (không tách được lệnh của NĐT trong nước).",
            "foreignRoom": "current_room/total_room thật từ price_board (đơn vị cổ phiếu) — room % = current_room/total_room×100. Mã có total_room=0 (không giới hạn sở hữu nước ngoài hoặc thiếu dữ liệu) bị loại khỏi foreignRoomWatch.",
            "topOfBook": "Giá + khối lượng đặt mua/bán tốt nhất (mức 1) thật từ price_board tại thời điểm snapshot — KHÔNG phải toàn bộ sổ lệnh (chỉ 1 trong 3 mức API trả về). spread_pct = (ask1−bid1)/bid1×100.",
            "marketConcentration": "market_cap = số CP niêm yết × giá khớp lệnh gần nhất (hoặc giá tham chiếu nếu chưa khớp lệnh phiên này) — số thật từ price_board, đã đối chiếu khớp với company.trading_stats().market_cap. top5Pct/top10Pct = % tổng vốn hoá toàn thị trường (theo mã có market_cap>0) do 5/10 mã lớn nhất nắm giữ — dùng đánh giá rủi ro tập trung khi phân bổ theo tỷ trọng vốn hoá.",
            "fundamentals": "pe/pb/roe từ company.ratio_summary() (dòng TTM mới nhất, báo cáo theo quý — CÓ ĐỘ TRỄ so với ngày công bố BCTC thật, không phải số real-time). foreigner_pct/state_pct/free_float_pct từ company.trading_stats() (snapshot sở hữu). Cả 2 nguồn là số thật của VCI, null nếu công ty chưa công bố/API lỗi tạm thời — không bịa.",
            "capacity": f"Số phiên cần để giải ngân/rút vốn nếu tự giới hạn ở {CAPACITY_PARTICIPATION_PCT*100:.0f}% GTGD/phiên (participation-rate heuristic, quy ước thực thi tổ chức phổ biến ≤10-20%/phiên để giảm market impact) = capital_bn / (turnover_bn × participation_pct). Dùng GTGD CỦA ĐÚNG PHIÊN HÔM NAY (snapshot 1 phiên/lần chạy, không phải ADTV nhiều phiên). Mốc vốn (tiers/capacity_days_500bn) là MINH HOẠ, KHÔNG phải khuyến nghị quy mô vị thế — cơ học thực thi lệnh thuần tuý.",
            "leadersRollup": "Trung bình theo tỷ trọng GTGD phiên hôm nay (turnover-weighted, chỉ trên giá trị không null, tự chuẩn hoá lại trọng số) của pe/pb/roe/foreigner_pct/state_pct/free_float_pct trên 10 mã dẫn dắt theo GTGD (tickers[]) — KHÔNG phải toàn thị trường, và KHÔNG cùng universe với marketConcentration.topStocks (universe đó là top-10 theo VỐN HOÁ, có thể khác top-10 theo GTGD).",
        },
        "quality": {
            "foreignNetBn": "live",
            "proprietaryNetBn": proprietary_quality,
        },
        "totalTurnoverBn": round(total_turnover_bn, 1),
        "foreignNetBn": round(foreign_net_bn, 1),
        "proprietaryNetBn": round(proprietary_net_bn, 1) if proprietary_net_bn is not None else None,
        "capacity": capacity,
        "sectors": sectors_out,
        "tickers": tickers_out,
        "leadersRollup": leaders_rollup,
        "foreignRoomWatch": foreign_room_watch,
        "marketConcentration": market_concentration,
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
