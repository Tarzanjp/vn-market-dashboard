#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Regime Engine (VN) — tổng hợp live.json + world-live.json + sector-flows.json +
cashout-vn.json thành 4 điểm số (Liquidity/Positioning/Momentum/Macro) + 1
verdict + cờ lệch pha, đồng thời tích luỹ mỗi ngày vào
public/data/history/regime-<year>.jsonl — vừa để tính percentile theo thời
gian (ngưỡng tự thích nghi, không phải số cố định), vừa làm dữ liệu backtest
sau này (join theo `date` với public/data/history/<year>.jsonl để xem verdict
hôm đó có dự báo đúng diễn biến VN-Index N phiên sau hay không).

STDLIB-ONLY — không cần vnstock/pandas, dù chạy nối tiếp trong cùng workflow
đã cài chúng cho 2 script trước (sector_flows, vn_cashout). Chỉ đọc lại các
file JSON đã có sẵn trên đĩa, không tự fetch gì mới.

Chạy: py automation/vn_regime/compute_regime.py

QUAN TRỌNG — đây là bản v1, các công thức chuẩn hoá điểm số (đặc biệt
Positioning và Macro) là ngưỡng thô ước lượng hợp lý ban đầu, CHƯA hiệu
chỉnh bằng dữ liệu lịch sử thật (chưa đủ để backtest). Sẽ cần tinh chỉnh
lại sau khi regime-<year>.jsonl tích luỹ đủ vài tháng dữ liệu.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "public" / "data"
LIVE = DATA / "live.json"
WORLD = DATA / "world-live.json"
SECTOR_FLOWS = DATA / "sector-flows.json"
CASHOUT = DATA / "cashout-vn.json"
HISTORY_DIR = DATA / "history"
REGIME_OUT = DATA / "regime.json"

ICT = timezone(timedelta(hours=7))
MIN_HISTORY_FOR_PERCENTILE = 20  # phiên — dưới ngưỡng này percentile coi là chưa đáng tin
MIN_HISTORY_FOR_5D_AVG = 5


def now_ict() -> datetime:
    return datetime.now(ICT)


def log(msg: str) -> None:
    print(f"[regime] {msg}", flush=True)


def load_json(path: Path):
    if not path.exists():
        log(f"missing (bỏ qua, không bịa số thay thế): {path.relative_to(ROOT)}")
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        log(f"read fail {path}: {e!r}")
        return None


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


def percentile_rank(value: float, series: list[float]) -> float | None:
    """% giá trị trong series <= value. None nếu series rỗng."""
    if not series:
        return None
    below = sum(1 for v in series if v <= value)
    return round(below / len(series) * 100, 1)


def quadrant_of(rs_ratio, rs_momentum) -> str | None:
    """Khớp chính xác logic quadrantOf() trong sectorFlowsEngine.js — đổi 1
    bên thì phải đổi bên kia, không thì Momentum Score sẽ lệch với trang
    Dòng tiền ngành."""
    if rs_ratio is None or rs_momentum is None:
        return None
    if rs_ratio >= 100 and rs_momentum >= 100:
        return "leading"
    if rs_ratio >= 100 and rs_momentum < 100:
        return "weakening"
    if rs_ratio < 100 and rs_momentum < 100:
        return "lagging"
    return "improving"


def sector_rrg_counts(sector_flows: dict | None) -> dict | None:
    """Đếm số ngành theo góc phần tư RRG ở kỳ tháng gần nhất."""
    if not sector_flows:
        return None
    monthly = sector_flows.get("monthly") or []
    if not monthly:
        return None
    latest_period = max(r["period"] for r in monthly)
    counts = {"leading": 0, "weakening": 0, "lagging": 0, "improving": 0}
    n = 0
    for r in monthly:
        if r["period"] != latest_period:
            continue
        q = quadrant_of(r.get("rs_ratio"), r.get("rs_momentum"))
        if q:
            counts[q] += 1
            n += 1
    if n == 0:
        return None
    counts["n"] = n
    counts["period"] = latest_period
    return counts


def build_today_row(live: dict | None, sector_flows: dict | None, cashout: dict | None) -> dict:
    date = (live or {}).get("asof") or now_ict().date().isoformat()

    margin_days = ((live or {}).get("margin") or {}).get("days") or []
    us_yields = {str(int(r["x"])): r["y"] for r in ((live or {}).get("usYields") or []) if r.get("y") is not None}

    return {
        "date": date,
        "turnoverBn": (cashout or {}).get("totalTurnoverBn"),
        # "live" cho phiên có snapshot cashout-vn.json thật; các phiên backfill
        # (xem backfill_liquidity.py) tự đặt "estimate_backfill" khi ghi row —
        # dùng để công khai trong basis text tỷ lệ thật/ước tính của percentile.
        "turnoverQuality": "live" if (cashout or {}).get("totalTurnoverBn") is not None else None,
        "foreignNetBn": (cashout or {}).get("foreignNetBn"),
        # marginBn: lưu lại để dùng sau (MoM cần vài điểm dữ liệu tháng phân biệt,
        # v1 CHƯA gộp vào công thức điểm số nào — xem docstring đầu file).
        "marginBn": margin_days[-1]["debt"] if margin_days else None,
        "dxy": (live or {}).get("dxy"),
        "us10y": us_yields.get("10"),
        "fgUs": ((live or {}).get("fgUs") or {}).get("score"),
        "sectorRRG": sector_rrg_counts(sector_flows),
        "vnIndex": ((live or {}).get("vnIndex") or {}).get("price"),
        "vnIndexPct": ((live or {}).get("vnIndex") or {}).get("pct"),
        # cashout-vn.json bị GHI ĐÈ mỗi ngày (chỉ giữ snapshot hôm nay) — sao
        # chép nguyên 5 ngành + 4 ticker vào đây để không mất khi ngày mai đè
        # lên. sector-flows.json thì KHÔNG cần sao chép vì bản thân nó đã tự
        # lưu lịch sử tháng/quý từ 2019 rồi (không có nguy cơ mất dữ liệu).
        "cashoutSectors": (cashout or {}).get("sectors"),
        "cashoutTickers": (cashout or {}).get("tickers"),
    }


def compute_scores(today: dict, history_excl_today: dict) -> dict:
    past = sorted(history_excl_today.values(), key=lambda r: r["date"])
    scores: dict = {}

    # --- Liquidity: percentile GTGD trên lịch sử tích luỹ (tự thích nghi,
    # không phải ngưỡng tuyệt đối 20.000/12.000 tỷ cố định). Lịch sử có thể
    # gồm cả phiên "estimate_backfill" (xem backfill_liquidity.py) — LUÔN công
    # khai tỷ lệ thật/ước tính trong basis, không giấu trong con số tổng n. ---
    past_turnover = [r["turnoverBn"] for r in past if r.get("turnoverBn") is not None]
    n_liq = len(past_turnover)
    n_liq_est = sum(1 for r in past if r.get("turnoverBn") is not None and r.get("turnoverQuality") == "estimate_backfill")
    n_liq_live = n_liq - n_liq_est
    if today.get("turnoverBn") is not None and n_liq >= MIN_HISTORY_FOR_PERCENTILE:
        pct = percentile_rank(today["turnoverBn"], past_turnover)
        band = "healthy" if pct >= 60 else "caution" if pct >= 30 else "danger"
        est_note = f" ({n_liq_live} thật + {n_liq_est} ước tính backfill)" if n_liq_est else ""
        scores["liquidity"] = {"value": pct, "band": band, "n": n_liq,
                                "basis": f"percentile GTGD trên {n_liq} phiên tích luỹ{est_note}"}
    else:
        scores["liquidity"] = {"value": None, "band": "insufficient_history", "n": n_liq,
                                "basis": f"cần ≥{MIN_HISTORY_FOR_PERCENTILE} phiên lịch sử, hiện có {n_liq}"}

    # --- Positioning: khối ngoại TB 5 phiên gần nhất (margin MoM sẽ gộp sau
    # khi có đủ điểm dữ liệu tháng phân biệt — xem marginBn trong today row). ---
    recent_foreign = [r["foreignNetBn"] for r in past[-4:] if r.get("foreignNetBn") is not None]
    if today.get("foreignNetBn") is not None:
        recent_foreign = recent_foreign + [today["foreignNetBn"]]
    n_pos = len(recent_foreign)
    if n_pos >= MIN_HISTORY_FOR_5D_AVG:
        window = recent_foreign[-5:]
        avg5 = sum(window) / len(window)
        # Ngưỡng thô v1: quanh 0 tỷ = 50 điểm, mỗi 500 tỷ lệch = 15 điểm.
        # CHƯA hiệu chỉnh bằng dữ liệu thật — xem docstring đầu file.
        val = max(0.0, min(100.0, 50 + (avg5 / 500) * 15))
        band = "healthy" if val >= 60 else "caution" if val >= 40 else "danger"
        scores["positioning"] = {"value": round(val, 1), "band": band, "n": n_pos,
                                  "basis": f"khối ngoại TB {len(window)} phiên gần nhất = {avg5:.0f} tỷ VND"}
    else:
        scores["positioning"] = {"value": None, "band": "insufficient_history", "n": n_pos,
                                  "basis": f"cần ≥{MIN_HISTORY_FOR_5D_AVG} phiên lịch sử, hiện có {n_pos}"}

    # --- Momentum: % ngành ở góc Dẫn dắt+Cải thiện trên RRG — không cần
    # lịch sử riêng, sector-flows.json đã tự có chiều sâu lịch sử. ---
    rrg = today.get("sectorRRG")
    if rrg and rrg.get("n"):
        good = rrg.get("leading", 0) + rrg.get("improving", 0)
        val = round(good / rrg["n"] * 100, 1)
        band = "healthy" if val >= 60 else "caution" if val >= 35 else "danger"
        scores["momentum"] = {"value": val, "band": band, "n": rrg["n"],
                               "basis": f"{good}/{rrg['n']} ngành ở góc Dẫn dắt+Cải thiện (kỳ {rrg.get('period', '')})"}
    else:
        scores["momentum"] = {"value": None, "band": "insufficient_history", "n": 0,
                               "basis": "chưa đọc được sector-flows.json"}

    # --- Macro: F&G Mỹ + xu hướng DXY 10 phiên gần nhất (DXY giảm = risk-on
    # cho EM/VN → điểm cao hơn). ---
    macro_parts = []
    if today.get("fgUs") is not None:
        macro_parts.append(today["fgUs"])
    past_dxy = [r["dxy"] for r in past[-10:] if r.get("dxy") is not None]
    if today.get("dxy") is not None and past_dxy:
        dxy_chg = today["dxy"] - past_dxy[0]
        macro_parts.append(max(0.0, min(100.0, 50 - dxy_chg * 10)))
    if macro_parts:
        val = round(sum(macro_parts) / len(macro_parts), 1)
        band = "healthy" if val >= 60 else "caution" if val >= 40 else "danger"
        basis = "F&G Mỹ" + (" + xu hướng DXY 10 phiên" if past_dxy else " (chưa có đủ lịch sử DXY)")
        scores["macro"] = {"value": val, "band": band, "n": len(macro_parts), "basis": basis}
    else:
        scores["macro"] = {"value": None, "band": "insufficient_history", "n": 0,
                            "basis": "chưa đọc được dữ liệu vĩ mô"}

    return scores


def compute_divergence(scores: dict) -> list[dict]:
    """Quy tắc thô, dựa trên nguyên lý Dalio: tín hiệu LỆCH PHA đáng chú ý
    hơn tín hiệu đồng thuận. Chỉ vài cặp có ý nghĩa thật, không so combinatorial
    toàn bộ."""
    def val(k):
        return (scores.get(k) or {}).get("value")

    liq, pos, mom, mac = val("liquidity"), val("positioning"), val("momentum"), val("macro")
    flags = []

    if liq is not None and pos is not None and liq >= 55 and pos <= 40:
        flags.append({
            "pair": ["liquidity", "positioning"],
            "note": "Thanh khoản cao nhưng khối ngoại đang bán ròng mạnh — có thể là dòng tiền luân chuyển nội bộ, không phải tiền mới thật vào thị trường.",
        })
    if mom is not None and pos is not None and mom >= 60 and pos <= 40:
        flags.append({
            "pair": ["momentum", "positioning"],
            "note": "Nhiều ngành đang mạnh trên RRG nhưng khối ngoại tiêu cực — sức mạnh có thể đến từ dòng tiền trong nước ngắn hạn, dễ đảo chiều khi khối ngoại tiếp tục bán.",
        })
    if mac is not None and liq is not None and mac <= 40 and liq >= 55:
        flags.append({
            "pair": ["macro", "liquidity"],
            "note": "Bối cảnh vĩ mô toàn cầu đang risk-off nhưng thanh khoản VN vẫn cao — theo dõi xem là tách biệt (decouple) thật hay chỉ trễ nhịp phản ứng.",
        })
    return flags


def compute_verdict(scores: dict, divergence: list[dict]) -> dict:
    vals = [s["value"] for s in scores.values() if s.get("value") is not None]
    if not vals:
        return {"cls": "unknown", "label": "Chưa đủ dữ liệu",
                "summary": "Mới bắt đầu tích luỹ lịch sử — cần thêm vài chục phiên để có verdict đáng tin."}
    avg = sum(vals) / len(vals)
    if divergence:
        return {"cls": "warn", "label": "Tín hiệu lệch pha",
                "summary": f"{len(divergence)} cặp điểm số đang mâu thuẫn nhau — xem chi tiết trước khi kết luận theo điểm trung bình ({avg:.0f}/100)."}
    if avg >= 60:
        return {"cls": "ok", "label": "Đồng thuận tích cực", "summary": f"4 điểm số đồng thuận tích cực, trung bình {avg:.0f}/100."}
    if avg >= 40:
        return {"cls": "warn", "label": "Trung tính", "summary": f"4 điểm số trung tính, trung bình {avg:.0f}/100."}
    return {"cls": "danger", "label": "Đồng thuận tiêu cực", "summary": f"4 điểm số đồng thuận tiêu cực, trung bình {avg:.0f}/100."}


def main() -> int:
    live = load_json(LIVE)
    load_json(WORLD)  # đọc để log rõ có/thiếu — chưa dùng trực tiếp trong công thức v1
    sector_flows = load_json(SECTOR_FLOWS)
    cashout = load_json(CASHOUT)

    if live is None and cashout is None:
        log("FAIL: thiếu cả live.json lẫn cashout-vn.json, dừng")
        return 1

    today = build_today_row(live, sector_flows, cashout)
    date = today["date"]
    year = int(date[:4])

    history_rows = load_regime_history(year)
    history_excl_today = {d: r for d, r in history_rows.items() if d != date}

    scores = compute_scores(today, history_excl_today)
    divergence = compute_divergence(scores)
    verdict = compute_verdict(scores, divergence)

    stored_row = dict(today)
    stored_row["scores"] = {k: v["value"] for k, v in scores.items()}
    stored_row["verdict"] = verdict["cls"]
    history_rows[date] = stored_row
    write_regime_history(year, history_rows)

    history_depth = len(history_excl_today) + 1
    regime = {
        "schemaVersion": "1.0",
        "generatedAtIct": now_ict().isoformat(timespec="seconds"),
        "date": date,
        "method": {
            "liquidity": "Percentile của GTGD hôm nay trên lịch sử tích luỹ (rolling) — tự thích nghi theo thời gian, không phải ngưỡng cố định. Lịch sử ban đầu có thể gồm phiên ước tính backfill (volume VNINDEX × hệ số quy đổi hiệu chỉnh từ 1 phiên thật) trước khi đủ phiên snapshot thật — xem automation/vn_regime/backfill_liquidity.py và tỷ lệ thật/ước tính trong scores.liquidity.basis.",
            "positioning": "TB khối ngoại ròng 5 phiên gần nhất, quy đổi thô sang thang 0-100 (v1, chưa hiệu chỉnh bằng backtest). Margin debt đã lưu vào lịch sử nhưng chưa gộp vào công thức.",
            "momentum": "% số ngành ICB đang ở góc Dẫn dắt+Cải thiện trên bản đồ RRG (public/data/sector-flows.json).",
            "macro": "TB F&G Mỹ + xu hướng DXY 10 phiên gần nhất, quy đổi thô sang thang 0-100 (v1, chưa hiệu chỉnh bằng backtest).",
            "divergence": "Quy tắc thô so từng cặp điểm số có ý nghĩa thật (không phải so combinatorial toàn bộ) — xem compute_divergence() trong script.",
        },
        "scores": scores,
        "verdict": verdict,
        "divergence": divergence,
        "dataQuality": {
            "historyDepthDays": history_depth,
            "note": (
                f"Đã tích luỹ {history_depth} phiên."
                + (f" Liquidity/Positioning cần thêm dữ liệu (percentile cần ≥{MIN_HISTORY_FOR_PERCENTILE} phiên) trước khi đáng tin."
                   if history_depth < MIN_HISTORY_FOR_PERCENTILE else "")
            ),
        },
        "inputs": today,
    }
    REGIME_OUT.write_text(json.dumps(regime, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"wrote {REGIME_OUT.relative_to(ROOT)} verdict={verdict['cls']} depth={history_depth}")
    return 0


if __name__ == "__main__":
    for _s in (sys.stdout, sys.stderr):
        if hasattr(_s, "reconfigure"):
            _s.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
