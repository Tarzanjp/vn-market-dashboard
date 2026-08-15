# Dòng tiền & Cashout (VN)

Công cụ độc lập — cần `vnstock` (kéo theo `pandas`), giống `automation/sector_flows/`.
Không chạy trong `daily_update.py` (cố tình chỉ dùng thư viện chuẩn).

**Tự động:** chạy hàng ngày cùng `automation/sector_flows/fetch_sector_flows.py`
trong một workflow chung — `.github/workflows/vn-vnstock-update.yml`
(15:00 ICT / 17:00 JST, T2–T6) — cài `vnstock` một lần, chạy nối tiếp 2
script, commit chung, trigger deploy chung, thay vì 2 workflow rời rạc.
Vẫn chạy tay được khi cần:

## Cài đặt & chạy

```bash
pip install -r automation/vn_cashout/requirements.txt
py automation/vn_cashout/fetch_cashout_data.py
```

Ghi ra `public/data/cashout-vn.json`, dùng bởi `dong-tien-cashout.html`.

## Dữ liệu thật vs. ước tính vs. không có nguồn

Lấy từ **một lần gọi** `price_board` cho toàn bộ ~700 mã HOSE/HNX/UPCOM (nguồn VCI):

- **Thật**: Tổng GTGD toàn thị trường, khối ngoại ròng toàn thị trường, GTGD & %thay đổi theo 5 nhóm ngành (Ngân hàng/Bất động sản/Thép-VLXD/Chứng khoán/Bán lẻ-Thực phẩm), khối ngoại mua/bán của HPG/TCB/VHM/SSI.
- **Ước tính**: 5D Avg Vol Ratio mỗi ngành — chỉ tính từ 1 mã đại diện lớn nhất ngành đó (theo GTGD hôm nay), không phải toàn ngành.
- **Không có nguồn miễn phí**: Tự doanh (proprietary flow) — trang luôn giữ đây là trường nhập tay.

## Giới hạn API

Tài khoản khách (guest) của vnstock giới hạn 20 requests/phút — script đã có
`time.sleep()` giữa các lần gọi lịch sử giá cho vol ratio để không vượt hạn mức.
