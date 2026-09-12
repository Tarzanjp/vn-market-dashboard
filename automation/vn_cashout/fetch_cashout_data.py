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
cộng lịch sử 25 phiên của mã đại diện lớn nhất mỗi ngành để tính vol ratio.

"Market Leader Flow" (tickers[]): TOP_TICKERS_N (10) mã dẫn dắt, xếp theo
GTGD bình quân LEADER_RANK_SESSIONS (15) phiên gần nhất — sơ tuyển từ top
LEADER_POOL_N (20) mã theo GTGD phiên hôm nay rồi lấy lịch sử cho rổ đó.
Chọn ĐỘNG mỗi lần chạy, không hardcode. Nếu không lấy đủ lịch sử (hạn mức API)
thì tự rơi về cách cũ — xếp theo GTGD 1 phiên — và ghi rõ ở tickersRankBasis.

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

# "Market Leader Flow" — top N mã DẪN DẮT, xếp theo GTGD bình quân
# LEADER_RANK_SESSIONS phiên gần nhất (ADTV) thay vì GTGD của đúng một phiên.
# Lý do: xếp theo 1 phiên khiến danh sách đổi người mỗi ngày theo một cú giao
# dịch đơn lẻ; "mã dẫn dắt" phải là mã dẫn dắt bền qua nhiều phiên.
TOP_TICKERS_N = 10
LEADER_RANK_SESSIONS = 15

# Rổ ứng viên: xếp hạng đúng theo ADTV cho TOÀN thị trường cần lịch sử của
# ~1.600 mã — không có API lấy lịch sử hàng loạt (Trading.price_history báo
# NotImplementedError ở cả nguồn VCI lẫn KBS), nên phải sơ tuyển từ GTGD hôm
# nay rồi mới lấy lịch sử cho rổ đó.
#
# ĐÃ ĐO (phiên 2026-09-11, rổ 45 mã, giãn cách 4s để không chạm hạn mức): top-10
# theo ADTV15 rút hết từ hạng 1–15 của GTGD hôm nay, tức 20 còn dư 5 bậc. Đây là
# một phiên, không phải bảo chứng vĩnh viễn: một mã dẫn dắt nghỉ giao dịch bất
# thường một hôm vẫn có thể tụt khỏi rổ. Nới rổ tốn đúng 1 request/mã.
LEADER_POOL_N = 20
# 15 phiên giao dịch ≈ 21 ngày lịch; lấy dư cho nghỉ lễ/Tết.
LEADER_CALENDAR_DAYS = 50

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

    # Cửa sổ nền của vol ratio: khối lượng hôm nay so với trung bình N phiên
    # TRƯỚC đó. 25 phiên (~1 tháng giao dịch) thay cho 5 phiên trước đây — nền
    # 5 phiên quá ngắn nên chỉ cần một phiên đột biến lọt vào mẫu là mẫu số bị
    # kéo lên và ratio hôm sau tụt xuống, khiến nhãn Cash Inflow/Outflow nhấp
    # nháy theo nhiễu chứ không theo dòng tiền.
    #
    # Đổi cửa sổ KHÔNG tốn thêm request — chỉ kéo dài khoảng ngày của cùng
    # một lần fetch (xem history_for bên dưới, dùng chung với ADTV).
    VOL_RATIO_BASE_SESSIONS = 25
    # Số mã đại diện mỗi ngành. 3 là đánh đổi với hạn mức 20 request/phút
    # (5 ngành × 3 = 15 lần gọi lịch sử, phần lớn trùng rổ mã dẫn dắt nên
    # được cache dùng lại). KHÔNG phải cả ngành — tỷ trọng phủ được ghi ra
    # JSON để trang nói rõ, thay vì để người đọc tưởng là toàn ngành.
    VOL_RATIO_REP_N = 3
    # Ngưỡng "khối lượng nóng" KHÔNG còn là hằng số 1,2x. Đo trên 120 phiên
    # (2026-09-12): với cùng ngưỡng 1,2 thì Bất động sản vượt ngưỡng 41,7%
    # số phiên còn Ngân hàng chỉ 11,7% — cùng một chữ "Cash Inflow" nhưng
    # hiếm gặp gấp gần 4 lần tuỳ ngành, tức nhãn không so sánh được giữa các
    # dòng. Thay bằng phân vị của CHÍNH ngành đó trên lịch sử của nó, nên
    # "nóng" luôn nghĩa là "thuộc nhóm N% phiên sôi động nhất của ngành này".
    VOL_RATIO_HOT_PCTILE = 0.80
    # Dưới mức này thì mẫu quá nhỏ để nói phân vị có nghĩa → không phân loại.
    VOL_RATIO_MIN_OBS = 40
    # Cần đủ 25 phiên nền + phiên hôm nay. Lấy dư lịch cho chắc: 25 phiên giao
    # dịch ≈ 35 ngày lịch, cộng nghỉ lễ/Tết → 75 ngày là an toàn mà không đắt.
    # Dài hơn mức 25 phiên cần cho mẫu số: còn phải dựng chuỗi tỷ lệ lịch sử
    # để tự hiệu chỉnh ngưỡng (xem VOL_RATIO_HOT_PCTILE). ~200 ngày lịch ≈ 135
    # phiên → khoảng 110 quan sát tỷ lệ. KHÔNG tốn thêm request, chỉ dài ngày.
    VOL_RATIO_CALENDAR_DAYS = 200

    # ---- Lịch sử giá: fetch MỘT LẦN cho mỗi mã, dùng chung ----
    # Vol Ratio (nền 25 phiên) và ADTV (15 phiên) trước đây gọi lịch sử riêng
    # cho những mã trùng nhau — vừa tốn request trên hạn mức 20/phút của tier
    # khách, vừa có nguy cơ hai chỉ số đọc hai lần fetch khác nhau (nguồn cùng
    # là VCI nhưng snapshot lệch thời điểm). Một lần fetch, một bộ nến, hai
    # phép tính đọc chung — số liệu trên trang do đó nhất quán với nhau.
    HIST_CALENDAR_DAYS = max(VOL_RATIO_CALENDAR_DAYS, LEADER_CALENDAR_DAYS)
    _hist_cache: dict[str, "pd.DataFrame | None"] = {}

    def history_for(sym: str):
        """Nến ngày của `sym`, hoặc None nếu không lấy được. Kết quả (kể cả
        None) được nhớ để không gọi lại mã đã hỏng."""
        if sym in _hist_cache:
            return _hist_cache[sym]
        df = None
        try:
            time.sleep(3.2)
            df = vs.stock(symbol=sym, source="VCI").quote.history(
                start=(pd.Timestamp.today() - timedelta(days=HIST_CALENDAR_DAYS)).strftime("%Y-%m-%d"),
                end=pd.Timestamp.today().strftime("%Y-%m-%d"), interval="1D",
            )
        except Exception as e:
            log(f"history fail {sym}: {e!r}")
        _hist_cache[sym] = df
        return df

    def vol_ratio_for(symbols):
        """GTGD hôm nay / GTGD bình quân 25 phiên trước, trên cùng một rổ mã.

        Trước đây hàm này lấy KHỐI LƯỢNG của đúng MỘT mã (symbols[:1]) làm
        "Vol Ratio" của cả ngành, trong khi hai cột bên cạnh (% Change và Daily
        Value) tính trên TOÀN BỘ mã trong ngành. Nói cách khác cột phân loại
        dòng tiền ngành Ngân hàng thực chất là của riêng STB. Giờ dùng
        VOL_RATIO_REP_N mã lớn nhất ngành theo GTGD.

        Cộng GTGD chứ không cộng khối lượng: số cổ phiếu của hai mã khác thị giá
        không cộng được với nhau cho ra đại lượng có nghĩa. GTGD thì được, và
        cùng đơn vị với cột Daily Value ngay cạnh.

        Tử và mẫu dùng CÙNG rổ mã, nên tỷ lệ vẫn đúng kể cả khi rổ chỉ phủ một
        phần ngành; phần phủ được trả về để UI nói rõ.

        Trả (ratio, số mã dùng, ngưỡng 'nóng' của riêng ngành này).
        """
        need = VOL_RATIO_BASE_SESSIONS + 1
        today_sum = 0.0
        base_sum = None
        used = []
        for sym in symbols[:VOL_RATIO_REP_N]:
            df = history_for(sym)
            if df is None or len(df) < need:
                log(f"vol_ratio {sym}: chỉ có {0 if df is None else len(df)} phiên, cần {need} — bỏ qua")
                continue
            val = (df["close"] * df["volume"])          # nghìn đồng, xem adtv_bn_for
            today_sum += float(val.iloc[-1])
            b = val.iloc[-need:-1].reset_index(drop=True)
            base_sum = b if base_sum is None else base_sum.add(b, fill_value=0)
            used.append(sym)
        if not used or base_sum is None:
            return None, 0, None
        avg_base = float(base_sum.mean())
        if avg_base <= 0:
            return None, len(used), None
        ratio = today_sum / avg_base

        # Ngưỡng tự hiệu chỉnh: dựng lại chính tỷ lệ này cho từng phiên lịch sử
        # rồi lấy phân vị. Chuỗi CHỈ gồm các phiên TRƯỚC phiên đang xét — phiên
        # hôm nay không được nằm trong tập tham chiếu của chính nó
        # (CLAUDE.md §1.3, cùng khuôn với compute_regime.py: history_excl_today).
        # Căn từ CUỐI: các mã có độ dài lịch sử khác nhau (niêm yết khác thời
        # điểm, phiên nghỉ khác nhau), reset_index từ đầu sẽ cộng nhầm phiên của
        # mã này với phiên khác của mã kia.
        series = [(history_for(sym)["close"] * history_for(sym)["volume"]) for sym in used]
        m = min(len(v) for v in series)
        tv = None
        for v in series:
            v = v.iloc[-m:].reset_index(drop=True)
            tv = v if tv is None else tv.add(v, fill_value=0)
        hist_ratios = []
        for t in range(VOL_RATIO_BASE_SESSIONS, len(tv) - 1):   # -1: bỏ phiên hôm nay
            base_t = float(tv.iloc[t - VOL_RATIO_BASE_SESSIONS:t].mean())
            if base_t > 0:
                hist_ratios.append(float(tv.iloc[t]) / base_t)
        thr = (round(float(pd.Series(hist_ratios).quantile(VOL_RATIO_HOT_PCTILE)), 2)
               if len(hist_ratios) >= VOL_RATIO_MIN_OBS else None)
        return ratio, len(used), thr

    sectors_out = []
    for names, label_en, label_vi in SECTOR_DEFS:
        daily_value_bn, pct_chg, top3 = sector_bucket(names)
        vr, rep_n, hot_thr = vol_ratio_for(top3)
        used = top3[:rep_n]
        # Rổ đại diện phủ bao nhiêu phần GTGD của ngành hôm nay. Không có con số
        # này thì "Vol Ratio" trông như đại lượng toàn ngành, ngang hàng với hai
        # cột bên cạnh — mà nó không phải.
        sub_all = board[board["industry_name"].isin(names)]
        rep_val = sub_all[sub_all["listing_symbol"].isin(used)]["match_accumulated_value"].sum() / 1000
        cov = round(rep_val / daily_value_bn * 100, 1) if daily_value_bn else None
        log(f"sector {label_en}: value={daily_value_bn:.1f} chg={pct_chg:.2f} "
            f"vol_ratio={vr} nguong_nong={hot_thr} rep={used} phủ={cov}% GTGD ngành")
        sectors_out.append({
            "en": label_en,
            "vi": label_vi,
            "chg": round(pct_chg, 2),
            "value_bn": round(daily_value_bn, 1),
            "vol_ratio": round(vr, 2) if vr else None,
            "vol_ratio_proxy_symbols": used,
            "vol_ratio_rep_n": rep_n,
            "vol_ratio_coverage_pct": cov,
            # Ngưỡng "nóng" riêng của ngành này (phân vị trên lịch sử của
            # chính nó, loại trừ phiên hôm nay). null = chưa đủ quan sát.
            "vol_ratio_hot_threshold": hot_thr,
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

    def adtv_bn_for(symbols, sessions):
        """GTGD bình quân `sessions` phiên gần nhất (GỒM phiên hôm nay), tỷ VND.

        Khác vol_ratio_for(): ở đây phiên hôm nay PHẢI nằm trong mẫu — đây là
        thước đo "mã này giao dịch lớn cỡ nào trong 15 phiên qua", không phải
        so hôm nay với một nền trước đó.

        ĐƠN VỊ: quote.history trả `close` theo NGHÌN ĐỒNG (VIC = 243.3 nghĩa
        là 243.300 đ/cp), nên close × volume ra nghìn đồng; chia 1e6 mới thành
        TỶ VND. Chia 1e9 (như thể close tính bằng đồng) cho ra số nhỏ hơn
        1.000 lần — thứ hạng không đổi vì sai số là hằng số, nên lỗi này KHÔNG
        lộ ra ở danh sách, chỉ lộ ở con số. Đã đối chiếu: VIC phiên 11/09
        243.3 × 4.264.000 / 1e6 = 1.037,4 tỷ, khớp GTGD bảng giá 1.041,7 tỷ.

        Dùng close × volume vì đây là số duy nhất suy ra được GTGD từ lịch sử
        giá; nó là GTGD toàn phiên (khớp lệnh + thoả thuận nếu nguồn gộp), có
        thể lệch nhẹ so với match_accumulated_value của bảng giá — chấp nhận,
        vì so sánh giữa các mã đều dùng chung một định nghĩa.

        Trả dict {mã: adtv}; mã nào lỗi/thiếu lịch sử thì KHÔNG có mặt trong
        dict (không đoán bằng 0 — 0 sẽ đẩy mã xuống đáy như thể nó ế).
        """
        out = {}
        for sym in symbols:
            df = history_for(sym)
            if df is None or len(df) < sessions:
                log(f"adtv {sym}: chỉ có {0 if df is None else len(df)} phiên, cần {sessions} — bỏ qua")
                continue
            val = (df["close"] * df["volume"]).iloc[-sessions:]
            out[sym] = float(val.mean()) / 1e6   # nghìn đồng → tỷ VND
        return out

    # Sơ tuyển theo GTGD hôm nay, rồi xếp lại theo ADTV 15 phiên.
    pool_board = board.sort_values("match_accumulated_value", ascending=False).head(LEADER_POOL_N)
    pool_syms = pool_board["listing_symbol"].tolist()
    log(f"xếp hạng mã dẫn dắt: rổ {len(pool_syms)} mã theo GTGD hôm nay → ADTV {LEADER_RANK_SESSIONS} phiên")
    adtv_by_sym = adtv_bn_for(pool_syms, LEADER_RANK_SESSIONS)

    # Cổng kiểm ĐƠN VỊ. ADTV suy từ lịch sử (close nghìn đồng × volume) và GTGD
    # của bảng giá (match_accumulated_value, triệu đồng) là hai đường tính độc
    # lập cho cùng một đại lượng — phải cùng bậc độ lớn. Một lỗi ×1000 ở đây
    # KHÔNG làm sai thứ hạng (sai số là hằng số) nên không thể phát hiện bằng
    # mắt qua danh sách; chỉ phép đối chiếu này bắt được. Đã sập một lần.
    if adtv_by_sym:
        _chk = pool_board.set_index("listing_symbol")["match_accumulated_value"]
        for _s, _a in list(adtv_by_sym.items())[:3]:
            _board_bn = float(_chk.get(_s, 0)) / 1000
            if _board_bn > 0:
                _r = _a / _board_bn
                if not (0.2 <= _r <= 5):
                    log(f"CẢNH BÁO đơn vị: ADTV{LEADER_RANK_SESSIONS}({_s})={_a:.1f} tỷ nhưng "
                        f"GTGD bảng giá={_board_bn:.1f} tỷ (tỷ lệ {_r:.4f}) — lệch bậc độ lớn, "
                        f"kiểm lại hệ số quy đổi trước khi tin con số này")
                else:
                    log(f"đơn vị OK: ADTV{LEADER_RANK_SESSIONS}({_s})={_a:.1f} tỷ vs GTGD phiên {_board_bn:.1f} tỷ")

    # Suy giảm êm: đủ mã có ADTV thì xếp theo ADTV; không thì giữ nguyên cách cũ
    # (GTGD 1 phiên). Cơ sở thực tế được ghi vào JSON để UI nói đúng, thay vì
    # dán nhãn "15 phiên" lên một danh sách xếp theo 1 phiên.
    if len(adtv_by_sym) >= TOP_TICKERS_N:
        ranked = sorted(adtv_by_sym.items(), key=lambda kv: -kv[1])[:TOP_TICKERS_N]
        ranked_syms = [k for k, _ in ranked]
        rank_basis = f"adtv{LEADER_RANK_SESSIONS}"
        rank_basis_note = (f"GTGD bình quân {LEADER_RANK_SESSIONS} phiên gần nhất (ADTV), "
                           f"sơ tuyển từ top {LEADER_POOL_N} mã theo GTGD phiên hôm nay")
    else:
        ranked_syms = pool_syms[:TOP_TICKERS_N]
        rank_basis = "today_turnover"
        rank_basis_note = (f"GTGD phiên hôm nay — chỉ lấy được ADTV cho {len(adtv_by_sym)}/"
                           f"{len(pool_syms)} mã (thiếu lịch sử hoặc chạm hạn mức API), "
                           f"chưa đủ {TOP_TICKERS_N} mã để xếp theo {LEADER_RANK_SESSIONS} phiên")
        log(f"CẢNH BÁO: {rank_basis_note}")

    # asof = NGÀY PHIÊN của số liệu, khác generatedAtIct (giờ script chạy).
    # Bảng giá là ảnh chụp trạng thái "hiện tại": chạy 16:30 thứ Sáu thì đó là
    # phiên thứ Sáu, nhưng chạy sáng thứ Bảy thì VẪN là phiên thứ Sáu — mà
    # generatedAtIct lại ghi thứ Bảy. Thiếu asof, người xem đọc giờ sinh file
    # thành ngày phiên. Lấy từ nến cuối của lịch sử đã fetch sẵn (không tốn
    # thêm request); đó đúng là phiên gần nhất đã chốt.
    _last = [pd.to_datetime(df["time"]).max()
             for df in _hist_cache.values() if df is not None and len(df)]
    asof_session = max(_last).strftime("%Y-%m-%d") if _last else None
    if asof_session:
        log(f"asof (ngày phiên) = {asof_session}; generatedAtIct = giờ chạy script")
    else:
        log("CẢNH BÁO: không suy được ngày phiên (không có lịch sử nào) — asof = null")

    order = {sym: i for i, sym in enumerate(ranked_syms)}
    top_tickers_board = (board[board["listing_symbol"].isin(ranked_syms)]
                         .assign(_o=lambda d: d["listing_symbol"].map(order))
                         .sort_values("_o"))
    tickers_out = []
    ticker_turnovers_bn = []  # song song với tickers_out — trọng số cho leadersRollup
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
            # GTGD bình quân 15 phiên — cơ sở xếp hạng. None nếu không lấy
            # được lịch sử cho mã đó (khi đó cả danh sách rơi về xếp 1 phiên).
            "adtv15_bn": round(adtv_by_sym[sym], 2) if sym in adtv_by_sym else None,
        })
        ticker_turnovers_bn.append(ticker_turnover_bn)
    log(f"top {TOP_TICKERS_N} mã dẫn dắt ({rank_basis}): {[t['code'] for t in tickers_out]}")

    # leadersRollup — trung bình theo tỷ trọng GTGD phiên hôm nay (turnover-
    # weighted) của các field fundamentals/ownership trên 10 mã dẫn dắt, chỉ
    # trên giá trị không null (tự chuẩn hoá lại trọng số khi có mã null). Đây
    # là universe top-10-theo-GTGD (tickers_out), KHÁC universe top-10-theo-
    # VỐN-HOÁ của market_concentration["topStocks"] bên dưới — không gộp nhầm.
    # Trọng số phải cùng cơ sở với thứ hạng: danh sách xếp theo ADTV15 mà lại
    # bình quân theo GTGD 1 phiên thì một phiên bất thường của 1 mã sẽ lái cả
    # rollup, dù mã đó vào danh sách nhờ 15 phiên.
    if rank_basis.startswith("adtv"):
        rollup_weights = [adtv_by_sym.get(t["code"]) or 0 for t in tickers_out]
        weight_basis = (f"GTGD bình quân {LEADER_RANK_SESSIONS} phiên của từng mã "
                        f"(ADTV-weighted, cùng cơ sở với thứ hạng)")
    else:
        rollup_weights = ticker_turnovers_bn
        weight_basis = "GTGD phiên hôm nay của từng mã (turnover-weighted)"

    def _weighted_avg(field: str):
        pairs = [(t[field], w) for t, w in zip(tickers_out, rollup_weights) if t.get(field) is not None and w]
        total_w = sum(w for _, w in pairs)
        return round(sum(v * w for v, w in pairs) / total_w, 2) if total_w else None

    leaders_rollup = {
        "n": len(tickers_out),
        "weightBasis": weight_basis,
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
        "asof": asof_session,
        "generatedAtIct": generated_at.isoformat(timespec="seconds"),
        "source": "VCI (qua thư viện mã nguồn mở vnstock) — bulk price_board toàn bộ mã HOSE/HNX/UPCOM",
        "method": {
            "tickers": rank_basis_note + (
                f". Rổ ứng viên là top {LEADER_POOL_N} mã theo GTGD phiên hôm nay — không có API "
                "lấy lịch sử hàng loạt nên không xếp hạng được trên toàn bộ ~1.600 mã; "
                "một mã ngoài rổ vẫn có thể thuộc top-10 thật theo ADTV."),
            "totalTurnoverBn": "Σ GTGD khớp lệnh tích luỹ toàn bộ mã (accumulated_value), đơn vị tỷ VND — số thật từ snapshot.",
            "foreignNetBn": "Σ (foreign_buy_value − foreign_sell_value) toàn bộ mã — số thật từ snapshot, đơn vị tỷ VND.",
            "sectorValueChg": "GTGD & %thay đổi (bình quân theo GTGD) của các mã thuộc nhóm ngành ICB tương ứng — số thật.",
            "volRatio": (f"GTGD hôm nay / GTGD bình quân {VOL_RATIO_BASE_SESSIONS} phiên TRƯỚC ĐÓ "
                          f"(phiên hôm nay không nằm trong mẫu số), tính trên tối đa {VOL_RATIO_REP_N} mã "
                          "lớn nhất ngành theo GTGD — tử và mẫu cùng rổ mã. KHÔNG phải toàn ngành: "
                          "xem vol_ratio_coverage_pct để biết rổ phủ bao nhiêu phần GTGD của ngành "
                          "(hai cột chg/value bên cạnh thì tính trên toàn bộ mã). Thiếu đủ "
                          f"{VOL_RATIO_BASE_SESSIONS + 1} phiên lịch sử → null, không hạ cửa sổ cho vừa dữ liệu."),
            "volRatioThreshold": (f"Ngưỡng \"khối lượng nóng\" của mỗi ngành = phân vị "
                                  f"{VOL_RATIO_HOT_PCTILE*100:.0f} của CHÍNH tỷ lệ đó trên lịch sử ngành, "
                                  "tính trên các phiên TRƯỚC phiên hiện tại (không look-ahead). "
                                  "Trước đây dùng hằng số 1,2x cho mọi ngành: đo trên 120 phiên thì "
                                  "Bất động sản vượt 1,2 ở 41,7% số phiên còn Ngân hàng chỉ 11,7%, "
                                  f"nên cùng một nhãn không so sánh được giữa các dòng. Cần tối thiểu "
                                  f"{VOL_RATIO_MIN_OBS} quan sát, thiếu thì null và không phân loại."),
            "proprietaryFlow": "Không có nguồn dữ liệu miễn phí qua API này. Lấy từ public/data/live.json field 'proprietary' (agent nghiên cứu công khai, xem daily_update.py merge_grok_fill), CHỈ khi cùng phiên hôm nay — quality=proxy. Không có nguồn cùng ngày → null (quality=missing), KHÔNG bịa/carry-forward.",
            "tickerForeignFlow": "foreign_buy_value / foreign_sell_value thật của từng mã, KHÔNG phải ước tính toàn bộ lệnh mua/bán (không tách được lệnh của NĐT trong nước).",
            "foreignRoom": "current_room/total_room thật từ price_board (đơn vị cổ phiếu) — room % = current_room/total_room×100. Mã có total_room=0 (không giới hạn sở hữu nước ngoài hoặc thiếu dữ liệu) bị loại khỏi foreignRoomWatch.",
            "topOfBook": "Giá + khối lượng đặt mua/bán tốt nhất (mức 1) thật từ price_board tại thời điểm snapshot — KHÔNG phải toàn bộ sổ lệnh (chỉ 1 trong 3 mức API trả về). spread_pct = (ask1−bid1)/bid1×100.",
            "marketConcentration": "market_cap = số CP niêm yết × giá khớp lệnh gần nhất (hoặc giá tham chiếu nếu chưa khớp lệnh phiên này) — số thật từ price_board, đã đối chiếu khớp với company.trading_stats().market_cap. top5Pct/top10Pct = % tổng vốn hoá toàn thị trường (theo mã có market_cap>0) do 5/10 mã lớn nhất nắm giữ — dùng đánh giá rủi ro tập trung khi phân bổ theo tỷ trọng vốn hoá.",
            "fundamentals": "pe/pb/roe từ company.ratio_summary() (dòng TTM mới nhất, báo cáo theo quý — CÓ ĐỘ TRỄ so với ngày công bố BCTC thật, không phải số real-time). foreigner_pct/state_pct/free_float_pct từ company.trading_stats() (snapshot sở hữu). Cả 2 nguồn là số thật của VCI, null nếu công ty chưa công bố/API lỗi tạm thời — không bịa.",
            "capacity": f"Số phiên cần để giải ngân/rút vốn nếu tự giới hạn ở {CAPACITY_PARTICIPATION_PCT*100:.0f}% GTGD/phiên (participation-rate heuristic, quy ước thực thi tổ chức phổ biến ≤10-20%/phiên để giảm market impact) = capital_bn / (turnover_bn × participation_pct). Dùng GTGD CỦA ĐÚNG PHIÊN HÔM NAY (snapshot 1 phiên/lần chạy, không phải ADTV nhiều phiên). Mốc vốn (tiers/capacity_days_500bn) là MINH HOẠ, KHÔNG phải khuyến nghị quy mô vị thế — cơ học thực thi lệnh thuần tuý.",
            "leadersRollup": f"Trung bình có trọng số ({weight_basis}), chỉ trên giá trị không null, tự chuẩn hoá lại trọng số, của pe/pb/roe/foreigner_pct/state_pct/free_float_pct trên {len(tickers_out)} mã dẫn dắt (tickers[]) — KHÔNG phải toàn thị trường, và KHÔNG cùng universe với marketConcentration.topStocks (universe đó là top-10 theo VỐN HOÁ).",
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
        # Cơ sở xếp hạng THỰC TẾ của tickers[] ở lượt chạy này. UI phải đọc
        # field này để dán nhãn, không được giả định luôn là 15 phiên.
        "tickersRankBasis": rank_basis,
        "tickersRankBasisNote": rank_basis_note,
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
