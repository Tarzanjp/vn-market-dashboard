# Tín hiệu tổ chức (VN30)

Công cụ độc lập — cần `vnstock` (kéo theo `pandas`), giống `automation/vn_cashout/`
và `automation/sector_flows/`. Không chạy trong `daily_update.py` (cố tình chỉ dùng
thư viện chuẩn).

**Tự động:** chạy cùng `automation/vn_cashout/fetch_cashout_data.py` và
`automation/sector_flows/fetch_sector_flows.py` trong `.github/workflows/vn-vnstock-update.yml`
(16:30 ICT, T2–T6). Vẫn chạy tay được khi cần:

## Cài đặt & chạy

```bash
pip install -r automation/vn_insight/requirements.txt
py automation/vn_insight/fetch_market_insight.py
```

Ghi ra `public/data/vn-insight.json`, dùng bởi `dong-tien-cashout.html`.

## Dữ liệu

- **VN30 futures basis**: VN30F1M (hợp đồng gần nhất) trừ VN30 giao ngay — số
  thật từ VCI qua vnstock. `basis > 0` (contango) thường phản ánh kỳ vọng tăng/chi
  phí carry dương; `basis < 0` (backwardation) thường đi kèm áp lực phòng hộ/bán.
  Nếu 1 trong 2 mã không fetch được, `quality = "missing"`, không suy đoán basis.
- **Giao dịch cổ đông lớn/nội bộ**: công bố thông tin thật từ HOSE (qua
  `company.events()`, category `MAJOR_SHAREHOLDER_TRADING`), CHỈ 30 mã cấu thành
  VN30 (lấy động qua `listing.symbols_by_group("VN30")`), 30 ngày gần nhất. Tiêu
  đề hiển thị nguyên văn từ nguồn — không tự tách số lượng cổ phiếu ra khỏi câu
  (rủi ro tách sai tạo số liệu trông như thật nhưng không đúng).

## Giới hạn API

Tài khoản khách (guest) của vnstock giới hạn 20 requests/phút. Script này gọi
~32 lần tuần tự (1 VN30 giao ngay + 1 VN30F1M + 30 mã VN30), cách quãng 3.2s/lần
— mất khoảng 2 phút chạy. Một mã lỗi tạm thời sẽ retry 1 lần rồi bỏ qua, không
làm hỏng cả lượt chạy.
