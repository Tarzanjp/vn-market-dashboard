# Dòng tiền & Cashout (VN)

Công cụ độc lập — cần `vnstock` (kéo theo `pandas`), giống `automation/sector_flows/`.
Không chạy trong `daily_update.py` (cố tình chỉ dùng thư viện chuẩn).

**Tự động:** chạy hàng ngày cùng `automation/sector_flows/fetch_sector_flows.py`
trong một workflow chung — `.github/workflows/vn-vnstock-update.yml`
(16:30 ICT, T2–T6) — cài `vnstock` một lần, chạy nối tiếp 2
script, commit chung, trigger deploy chung, thay vì 2 workflow rời rạc.
Giờ chạy cố tình đặt SAU vòng `data-update.yml` buổi chiều (16:00 ICT), không
phải ngay lúc HOSE đóng cửa (15:00 ICT) — xem mục "Tự doanh" bên dưới để biết lý do.
Vẫn chạy tay được khi cần:

## Cài đặt & chạy

```bash
pip install -r automation/vn_cashout/requirements.txt
py automation/vn_cashout/fetch_cashout_data.py
```

Ghi ra `public/data/cashout-vn.json`, dùng bởi `dong-tien-cashout.html`.

## Dữ liệu thật vs. ước tính vs. không có nguồn

Lấy từ **một lần gọi** `price_board` cho toàn bộ ~700 mã HOSE/HNX/UPCOM (nguồn VCI):

- **Thật**: Tổng GTGD toàn thị trường, khối ngoại ròng toàn thị trường, GTGD & %thay đổi theo 5 nhóm ngành (Ngân hàng/Bất động sản/Thép-VLXD/Chứng khoán/Bán lẻ-Thực phẩm), khối ngoại mua/bán của 10 mã dẫn dắt (GTGD lớn nhất phiên, chọn ĐỘNG mỗi lần chạy — không hardcode danh sách), room ngoại còn lại (`foreign_room_pct`) + top-of-book bid/ask (`bid1_price`/`ask1_price`/`spread_pct`) của 10 mã đó, và danh sách "Sắp cạn room ngoại" (`foreignRoomWatch`, top 8 mã toàn thị trường theo room % thấp nhất, thanh khoản ≥5 tỷ VND/phiên) — cả 3 nhóm này trích ra từ CHÍNH `price_board` đã gọi, không tốn thêm request.
- **Ước tính**: 5D Avg Vol Ratio mỗi ngành — chỉ tính từ 1 mã đại diện lớn nhất ngành đó (theo GTGD hôm nay), không phải toàn ngành.
- **Không có nguồn miễn phí, lấy qua agent**: Tự doanh (proprietary flow) — script
  đọc `public/data/live.json` (do `automation/daily_update.py` ghi) và lấy field
  `proprietary` NẾU nó của đúng phiên hôm nay (`asof` khớp ngày ICT hiện tại).
  Field đó do Grok/agent nghiên cứu công khai điền vào `grok-fill.json`, quality
  luôn là `proxy` — không bao giờ ghi đè lên số thật. Đây là lý do
  `vn-vnstock-update.yml` chạy ở 16:30 ICT thay vì 15:00 ICT: phải đợi
  `data-update.yml`'s vòng 16:00 ICT ghi `live.json` của hôm nay trước.
  Vì báo chí VN rất hiếm khi công bố số tự doanh theo phiên, `proprietaryNetBn`
  sẽ THƯỜNG XUYÊN là `null` (quality `missing`) — trang hiển thị "—", đây là
  hành vi đúng, không phải lỗi.

## Giới hạn API

Tài khoản khách (guest) của vnstock giới hạn 20 requests/phút — script đã có
`time.sleep()` giữa các lần gọi lịch sử giá cho vol ratio để không vượt hạn mức.
