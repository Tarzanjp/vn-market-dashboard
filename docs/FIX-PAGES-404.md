# Sửa HTTP 404 GitHub Pages

## Nguyên nhân đã xác định

1. **Deploy job báo success** nhưng URL `https://tarzanjp.github.io/vn-market-dashboard/` trả **404**.
2. Repo đang chạy **hai kênh deploy cùng lúc**:
   - Workflow cũ **pages build and deployment** (Jekyll, “Deploy from a branch”)
   - Workflow **Deploy static site to Pages** (Actions)
3. Hai kênh **đua nhau ghi** site → dễ ra site rỗng / 404 dù log xanh.
4. API `has_pages: true` nhưng endpoint cấu hình Pages public trả 404 (cấu hình source chưa “sạch”).

## Cách sửa (bạn làm trong GitHub UI — bắt buộc)

### Bước 1 — Chọn đúng Source

1. Mở: https://github.com/Tarzanjp/vn-market-dashboard/settings/pages  
2. **Build and deployment** → **Source**:
   - Chọn **Deploy from a branch**
3. **Branch**:
   - `gh-pages`  
   - folder: `/ (root)`  
4. **Save**  
5. Đợi 1–3 phút, bật **Enforce HTTPS** nếu hiện.

> Workflow mới đẩy site tĩnh lên nhánh **`gh-pages`** (không qua Jekyll).  
> **Không** để Source = `main` (sẽ lại chạy Jekyll conflict).  
> **Không** cần “GitHub Actions” source nữa với cách này.

### Bước 2 — Chạy lại deploy

1. https://github.com/Tarzanjp/vn-market-dashboard/actions  
2. **Deploy static site to Pages** → **Run workflow** → main  
3. Đợi job **xanh**  
4. Mở: https://tarzanjp.github.io/vn-market-dashboard/  
5. Hard refresh: **Ctrl+F5**

### Bước 3 — Kiểm tra nhánh gh-pages

1. Repo → nhánh **gh-pages** (dropdown branch)  
2. Phải thấy: `index.html`, `the-gioi.html`, `data/live.js`, `.nojekyll`  
3. Nếu không có nhánh → workflow deploy chưa chạy xong / thiếu quyền `contents: write`

## Sau khi xong

| URL | Kỳ vọng |
|-----|---------|
| https://tarzanjp.github.io/vn-market-dashboard/ | Dashboard |
| https://tarzanjp.github.io/vn-market-dashboard/the-gioi.html | Thế giới |
| https://tarzanjp.github.io/vn-market-dashboard/data/live.js | Có `__MARKET_LIVE` |

## Vẫn 404?

1. Settings → Pages: có thông báo lỗi màu đỏ không?  
2. Tài khoản GitHub có bị hạn chế Pages không (hiếm)?  
3. Thử incognito / mạng khác  
4. Đợi thêm 10 phút (DNS/CDN lần đầu)  
5. Backup: Netlify Drop folder `public` sau khi build local  

## Không đụng agent

Agent + `run_agent_daily.ps1` vẫn push `main` → workflow deploy lại `gh-pages` tự động.
