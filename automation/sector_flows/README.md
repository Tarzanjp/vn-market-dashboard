# Dòng tiền theo ngành (HOSE)

Công cụ độc lập — **không** chạy trong `automation/daily_update.py` (vốn cố
tình chỉ dùng thư viện chuẩn Python, xem `automation/README.md`). Đây là một
nhánh riêng vì cần `vnstock` (kéo theo `pandas`).

**Tự động:** chạy hàng ngày cùng `automation/vn_cashout/fetch_cashout_data.py`
trong một workflow chung — `.github/workflows/vn-vnstock-update.yml`
(15:00 ICT / 17:00 JST, T2–T6). Vẫn chạy tay được khi cần:

## Cài đặt & chạy

```bash
pip install -r automation/sector_flows/requirements.txt
py automation/sector_flows/fetch_sector_flows.py
```

Ghi ra `public/data/sector-flows.json` — 10 chỉ số ngành ICB cấp 1 do HOSE tự
tính (qua nguồn VCI, thư viện mã nguồn mở `vnstock`), return %/tháng/quý,
GTGD ước tính, và chỉ số RRG (RS-Ratio/RS-Momentum) so với VN-Index.

## Giới hạn đã biết

- HOSE gộp Ngân hàng + Chứng khoán + Bảo hiểm vào một chỉ số Tài chính
  (VNFIN) — không tách riêng được ngành Ngân hàng qua nguồn miễn phí này.
- GTGD là **ước tính** (Σ khối lượng × giá đóng cửa mỗi ngày), không phải số
  khớp lệnh chính thức do HOSE công bố — chỉ dùng để so sánh tương đối giữa
  ngành/kỳ, không phải số liệu tuyệt đối.
- Công thức RRG là xấp xỉ đơn giản hoá kiểu JdK RS-Ratio/RS-Momentum, không
  phải công thức gốc (xem docstring `rs_ratio_momentum()` trong script).
