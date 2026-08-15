# Regime Engine (VN)

Tổng hợp `live.json` + `world-live.json` + `sector-flows.json` + `cashout-vn.json`
thành 4 điểm số (Liquidity / Positioning / Momentum / Macro) + 1 verdict + cờ
lệch pha. Xem `regime-architecture` (artifact đã gửi trong hội thoại) cho bối
cảnh đầy đủ — đây là bản triển khai Phase 1 + Phase 3 của lộ trình đó.

**STDLIB-ONLY** — không cần cài gì thêm, kể cả khi chạy độc lập:

```bash
py automation/vn_regime/compute_regime.py
```

## Chạy tự động

Chạy nối tiếp trong `.github/workflows/vn-vnstock-update.yml`, ngay sau
`fetch_sector_flows.py` và `fetch_cashout_data.py` (đọc lại chính JSON 2
script đó vừa ghi trong cùng lần chạy) — không có workflow riêng.

## Output

- **`public/data/regime.json`** — verdict mới nhất (đọc bởi trang tương lai,
  chưa xây). Có `method` giải thích công thức từng điểm số ngay trong file.
- **`public/data/history/regime-<year>.jsonl`** — 1 dòng/phiên, upsert theo
  `date` (idempotent, chạy lại trong ngày không nhân đôi). Đây vừa là nguồn
  tính percentile (Liquidity Score cần lịch sử), vừa là log để backtest sau
  này — join theo `date` với `public/data/history/<year>.jsonl` để xem
  verdict hôm đó dự báo đúng diễn biến VN-Index N phiên sau hay không.

  Mỗi dòng còn giữ nguyên `cashoutSectors` (5 ngành) và `cashoutTickers`
  (HPG/TCB/VHM/SSI) sao chép từ `cashout-vn.json` — file đó bị **ghi đè**
  mỗi lần chạy nên chỉ có snapshot hôm nay; không sao chép vào đây thì chi
  tiết từng ngành/mã của các phiên trước sẽ mất vĩnh viễn, không backtest
  lại được. `sector-flows.json` thì KHÔNG cần sao chép vì bản thân nó đã tự
  lưu lịch sử tháng/quý từ 2019 (không có nguy cơ mất dữ liệu tương tự).

## Thiết kế: xuống cấp trung thực khi thiếu lịch sử

Không có đủ dữ liệu → điểm số trả về `null` với `band: "insufficient_history"`
và lý do cụ thể (`"cần ≥20 phiên lịch sử, hiện có 3"`), **không** suy diễn số
liệu để lấp chỗ trống. `verdict` chỉ lấy trung bình các điểm số đang có, bỏ
qua điểm `null` — không zero-fill.

| Điểm số | Cần lịch sử? | Ngưỡng tối thiểu |
|---|---|---|
| Liquidity | Có (percentile) | 20 phiên |
| Positioning | Có (TB 5 phiên) | 5 phiên |
| Momentum | Không (đọc trực tiếp RRG) | — |
| Macro | Một phần (xu hướng DXY) | có vẫn tính được phần F&G |

## Giới hạn đã biết — cần đọc trước khi tin verdict

- **Công thức Positioning/Macro là v1, ngưỡng thô ước lượng** (`50 + avg5/500*15`,
  `50 - dxy_chg*10`) — **chưa hiệu chỉnh bằng backtest thật**, sẽ cần tinh
  chỉnh lại sau khi `regime-<year>.jsonl` tích luỹ đủ vài tháng dữ liệu.
- **Margin debt đã lưu vào mỗi dòng lịch sử nhưng chưa gộp vào công thức
  Positioning** — margin chỉ cập nhật theo tháng, cần vài điểm dữ liệu tháng
  phân biệt mới tính được tốc độ tăng (MoM) có ý nghĩa.
- **Divergence là quy tắc thô** (3 cặp cố định: liquidity↔positioning,
  momentum↔positioning, macro↔liquidity) — không phải mô hình thống kê,
  chỉ là heuristic dựa trên trực giác Dalio ("tín hiệu lệch pha đáng chú ý
  hơn đồng thuận").
- **`world-live.json` được đọc nhưng chưa dùng trực tiếp trong công thức** —
  Macro Score hiện chỉ dùng `dxy`/`fgUs` từ `live.json` (đã có sẵn lịch sử
  qua `history/<year>.jsonl`); world-live.json phong phú hơn (31 chỉ số) sẽ
  cân nhắc gộp thêm ở bản sau.
