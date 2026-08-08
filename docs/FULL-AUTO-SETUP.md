# Chạy tự động hết — hướng dẫn 5 phút

## Trả lời ngắn

| Không có `XAI_API_KEY` | Có `XAI_API_KEY` (xAI / Grok API) |
|------------------------|-------------------------------------|
| Auto: UST, VN-Index, DXY, F&G US | **Auto full**: API free + Grok lấp margin / breadth / TPCP VN… |
| Margin/breadth vẫn mẫu hoặc file tay | Grok API tự gọi trong Actions, ghi `grok-fill.json` + `live.js` |

→ **Có thể chạy tự động hết**, với điều kiện thêm **API key xAI** (trả theo usage, không free vô hạn).

---

## Bật full auto (1 lần)

### 1. Lấy API key xAI

1. Vào https://console.x.ai/ (hoặc account xAI)  
2. Tạo **API Key**  
3. Copy key (chỉ hiện 1 lần)

### 2. Gắn secret trên GitHub

1. https://github.com/Tarzanjp/vn-market-dashboard/settings/secrets/actions  
2. **New repository secret**  
3. Name: `XAI_API_KEY`  
4. Value: dán key → Save  

Optional: Settings → **Variables** → `XAI_MODEL` = `grok-3-latest` (hoặc model bạn có quyền)

### 3. Quyền Actions ghi repo

Settings → Actions → General → **Workflow permissions** → **Read and write** → Save

### 4. Chạy thử

1. Actions → **Daily market data update** → **Run workflow**  
2. Xem log:  
   - `US yields OK` / `VN-Index OK` / …  
   - `Grok auto OK fields=...` (nếu có key)  
   - hoặc `Grok auto: skip (no XAI_API_KEY secret)` nếu chưa gắn  
3. Refresh https://tarzanjp.github.io/vn-market-dashboard/  
4. Footer: `LIVE … quality=…` có thêm `margin:proxy` khi Grok fill được  

### 5. Lịch tự chạy (đã cấu hình)

| ICT | Job |
|-----|-----|
| 08:15 T2–T6 | Morning pack |
| 16:00 T2–T6 | Sau phiên VN |

Không cần paste prompt tay nữa **nếu đã có key**.

---

## Luồng full auto

```
Cron GitHub Actions
  ├─ 1. Free API: Treasury, Yahoo VNI/DXY, CNN F&G
  ├─ 2. Nếu có XAI_API_KEY → Grok API điền field còn thiếu
  │     (margin, breadth, vnYields, usdVnd…) quality=proxy
  ├─ 3. Merge data/grok-fill.json (nếu bạn vẫn dán tay — optional)
  ├─ 4. Ghi data/live.js
  └─ 5. Commit → Deploy Pages
```

**Ưu tiên số:** `live` (API) > `proxy` (Grok) > mẫu HTML.

---

## Chi phí & rủi ro

| | |
|--|--|
| GitHub Actions | Free tier thường đủ 2 run/ngày |
| xAI API | Tính theo token — theo dõi console.x.ai |
| Độ tin cậy Grok | **Proxy**, không phải feed sàn — UI đã có nhãn |
| Key lộ | Chỉ để trong GitHub Secrets, không commit vào code |

---

## Local test full auto

```powershell
cd C:\Users\shimo\Downloads\vn-market-site
$env:XAI_API_KEY = "xai-..."   # key của bạn
py scripts/daily_update.py
```

Chỉ free API:

```powershell
py scripts/daily_update.py --no-grok
```

---

## Nếu không muốn trả API Grok

Vẫn auto phần free; phần VN (margin/breadth) giữ mẫu hoặc thỉnh thoảng dán `grok-fill.json` bằng chat Grok (prompt trong `docs/PROMPT-GROK-DAILY.md`).
