# Prompt Grok → JSON LIVE (copy-paste hàng ngày)

Dùng sau phiên HOSE (~15:30–17:00 ICT) hoặc sáng trước 8:30.  
Mục tiêu: điền phần **chưa có API free** (margin, TPCP VN, breadth…), **không bịa số**.

---

## Prompt (copy toàn bộ khối dưới)

```
Bạn là trợ lý dữ liệu cho dashboard non-profit "Thông tin thị trường" (Việt Nam).

NHIỆM VỤ:
1) Thu thập số LIÊN QUAN đến phiên giao dịch gần nhất (HOSE, giờ Việt Nam) từ nguồn CÔNG KHAI bạn truy cập được.
2) Chỉ ghi số CÓ NGUỒN. Không suy đoán, không bịa.
3) Trả về ĐÚNG 1 object JSON (không markdown, không giải thích ngoài JSON).
4) Mọi field không chắc → null hoặc bỏ field đó.
5) quality chỉ dùng: "proxy" | "live" | "stale" | "missing"

NGÀY / PHIÊN CẦN LẤY:
- Ưu tiên phiên HOSE mới nhất đã đóng cửa (sau ATC).
- Ghi asof = YYYY-MM-DD của phiên đó (ICT).

SCHEMA BẮT BUỘC (chỉ các key sau; bỏ key không có data):

{
  "schemaVersion": "1.0",
  "asof": "YYYY-MM-DD",
  "sourceNotes": ["Nguồn 1 + URL/tên", "Nguồn 2..."],
  "quality": {
    "vnIndex": "proxy",
    "usYields": "missing",
    "vnYields": "proxy",
    "margin": "proxy",
    "breadth": "proxy",
    "fgUs": "missing",
    "dxy": "missing",
    "usdVnd": "proxy",
    "foreign": "proxy"
  },
  "vnIndex": {
    "price": 0,
    "pct": 0,
    "chg": 0,
    "date": "YYYY-MM-DD"
  },
  "usYields": [
    { "t": "1 năm", "y": 0, "d": 0, "m": 0, "yr": 0, "x": 1, "est": true },
    { "t": "3 năm", "y": 0, "d": 0, "m": 0, "yr": 0, "x": 3, "est": false },
    { "t": "5 năm", "y": 0, "d": 0, "m": 0, "yr": 0, "x": 5, "est": false },
    { "t": "10 năm", "y": 0, "d": 0, "m": 0, "yr": 0, "x": 10, "est": false },
    { "t": "30 năm", "y": 0, "d": 0, "m": 0, "yr": 0, "x": 30, "est": false }
  ],
  "vnYields": [
    { "t": "1 năm", "y": 0, "d": 0, "m": 0, "yr": 0, "x": 1, "est": true },
    { "t": "3 năm", "y": 0, "d": 0, "m": 0, "yr": 0, "x": 3, "est": true },
    { "t": "5 năm", "y": 0, "d": 0, "m": 0, "yr": 0, "x": 5, "est": true },
    { "t": "10 năm", "y": 0, "d": 0, "m": 0, "yr": 0, "x": 10, "est": false },
    { "t": "30 năm", "y": 0, "d": 0, "m": 0, "yr": 0, "x": 30, "est": true }
  ],
  "margin": {
    "asof": "YYYY-MM-DD",
    "freq": "daily",
    "note": "Nguồn ...",
    "days": [
      { "date": "YYYY-MM-DD", "debt": 0, "net": 0 }
    ],
    "brokers": [
      { "code": "SSI", "name": "SSI", "debt": 0, "d": 0, "room": 0, "share": 0 }
    ]
  },
  "breadth": {
    "date": "YYYY-MM-DD",
    "gtgd": 0,
    "all": { "a": 0, "d": 0, "u": 0, "ceil": 0, "floor": 0, "total": 0 },
    "vn100": { "a": 0, "d": 0, "u": 0, "total": 100 },
    "vn30": { "a": 0, "d": 0, "u": 0, "total": 30 }
  },
  "usdVnd": { "central": 0, "note": "NHNN trung tâm" },
  "foreign": { "net": null, "note": "mua/bán ròng phiên (tỷ VND) nếu có" },
  "fgUs": {
    "score": null,
    "hist": { "prev": null, "week": null, "month": null, "year": null },
    "asofEt": null
  },
  "dxy": null,
  "notes": ["Ghi chú ngắn"]
}

QUY TẮC SỐ:
- debt / gtgd: đơn vị tỷ đồng (số, không dấu phẩy).
- y (yield): %/năm, ví dụ 4.65.
- room: % còn lại (0–100) nếu không có thì bỏ field room.
- share: % trên tổng dư nợ nếu biết.
- days: có thể 1 điểm (phiên mới nhất) hoặc nhiều điểm nếu có chuỗi; net = debt_t − debt_t-1 (0 nếu chỉ 1 điểm).
- Không invent broker list nếu không có nguồn.

ƯU TIÊN THU THẬP (theo thứ tự):
1) VN-Index đóng cửa + % 
2) GTGD HOSE + tăng/giảm/trần/sàn (nếu có)
3) Dư nợ margin toàn TT (ngày hoặc tuần — ghi freq)
4) USD/VND trung tâm
5) TPCP VN 5Y/10Y nếu có
6) Khối ngoại phiên nếu có

CHỈ TRẢ JSON THUẦN.
```

---

## Sau khi Grok trả JSON

### Cách 1 — Local (nhanh)

1. Copy JSON vào file:

```text
C:\Users\shimo\Downloads\vn-market-site\data\grok-fill.json
```

2. Chạy:

```powershell
cd C:\Users\shimo\Downloads\vn-market-site
py scripts/daily_update.py
git add data
git commit -m "data: merge Grok fill + auto APIs"
git push origin main
```

### Cách 2 — Chỉ validate + merge Grok (không fetch lại net)

```powershell
py scripts/apply_grok_fill.py
git add data
git commit -m "data: Grok fill only"
git push
```

### Cách 3 — GitHub web

1. Repo → `data/grok-fill.json` → Edit → dán JSON → Commit  
2. Actions → **Daily market data update** → **Run workflow**  

(Actions sẽ fetch API free + merge `grok-fill.json`.)

---

## Quy tắc merge (pipeline)

| Field | API free = live | Grok fill |
|--------|------------------|-----------|
| usYields, vnIndex, dxy, fgUs | **Thắng** | Chỉ dùng nếu API stale/missing |
| margin, vnYields, breadth, usdVnd, foreign | — | **Điền** (quality=proxy) |

→ Grok **không ghi đè** số API đang live; chỉ lấp chỗ trống.
