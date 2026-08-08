# Hướng dẫn đưa trang lên mạng (chi phí ~$0)

Bộ file trong thư mục này:

| File | Nội dung |
|------|----------|
| `index.html` | Dashboard trong nước (từ `vn-market-dashboard_13.html`) |
| `the-gioi.html` | Chỉ số thế giới |
| `README.md` | Hướng dẫn này |

**Mục tiêu:** trang public HTTPS, free, phù hợp non-profit.

---

## Cách 1 — GitHub Pages (khuyến nghị, ~15 phút)

### Bước 1. Cài Git (nếu chưa có)

1. Tải: https://git-scm.com/download/win  
2. Cài xong, mở **PowerShell** hoặc **Git Bash**.  
3. Kiểm tra:

```powershell
git --version
```

### Bước 2. Tạo tài khoản GitHub

1. Vào https://github.com/signup  
2. Bật **2FA** (Settings → Password and authentication) — nên bật cho non-profit.

### Bước 3. Tạo repository

1. https://github.com/new  
2. **Repository name:** ví dụ `vn-market-dashboard`  
3. Public (free Pages dễ hơn) hoặc Private (Pages free cho private trên plan cá nhân hiện tại — nếu lỗi thì để Public).  
4. **Không** tick “Add README” (tránh conflict).  
5. Create repository.

### Bước 4. Đẩy code lên GitHub

Trong PowerShell, **sửa** `YOUR_USER` thành username GitHub của bạn:

```powershell
cd C:\Users\shimo\Downloads\vn-market-site

git init
git add index.html the-gioi.html README.md
git commit -m "Initial publish: VN market dashboard"
git branch -M main
git remote add origin https://github.com/YOUR_USER/vn-market-dashboard.git
git push -u origin main
```

Đăng nhập GitHub khi được hỏi (Personal Access Token nếu không dùng password):

- Tạo token: GitHub → Settings → Developer settings → Personal access tokens  
- Scope tối thiểu: `repo`

### Bước 5. Bật GitHub Pages

1. Repo → **Settings** → **Pages** (menu trái)  
2. **Source:** Deploy from a branch  
3. **Branch:** `main` → folder `/ (root)` → **Save**  
4. Đợi 1–2 phút, refresh trang Settings → Pages  

URL dạng:

```text
https://YOUR_USER.github.io/vn-market-dashboard/
```

- Trong nước: `.../vn-market-dashboard/` hoặc `.../vn-market-dashboard/index.html`  
- Thế giới: `.../vn-market-dashboard/the-gioi.html`

### Bước 6. Kiểm tra sau khi lên

- [ ] Mở URL trên Chrome/Edge (HTTPS ổ khóa)  
- [ ] Nav **Trong nước** / **Thế giới** chuyển trang được  
- [ ] Font, biểu đồ, bảng hiện bình thường  
- [ ] Mobile: thu nhỏ cửa sổ vẫn đọc được  

---

## Cách 2 — Cloudflare Pages (cũng free, rất nhanh)

1. Tạo tài khoản https://dash.cloudflare.com/sign-up  
2. **Workers & Pages** → **Create** → **Pages** → **Connect to Git**  
3. Chọn repo vừa push (cần login GitHub)  
4. Build settings:  
   - Framework preset: **None**  
   - Build command: *(để trống)*  
   - Build output directory: `/` hoặc `.`  
5. Save and Deploy  
6. URL dạng: `https://vn-market-dashboard-xxxx.pages.dev`

**Ưu điểm:** CDN nhanh, HTTPS free, custom domain dễ.

---

## Cách 3 — Netlify Drop (không cần Git, ~5 phút)

1. Vào https://app.netlify.com/drop  
2. Kéo **cả thư mục** `vn-market-site` vào  
3. Nhận URL `https://random-name.netlify.app`  
4. (Optional) Đổi tên site trong Site settings  

Phù hợp thử nhanh; lâu dài nên chuyển GitHub/Cloudflare để cập nhật có lịch sử.

---

## Cập nhật trang sau khi sửa

### Sửa HTML local rồi publish lại

```powershell
cd C:\Users\shimo\Downloads\vn-market-site

# Nếu bạn sửa bản gốc _13, copy lại:
# Copy-Item ..\vn-market-dashboard_13.html .\index.html -Force
# Copy-Item ..\the-gioi.html .\the-gioi.html -Force

git add -A
git commit -m "Update dashboard data/UI"
git push
```

Pages/Cloudflare tự deploy sau 1–3 phút.

### Cập nhật số liệu (giai đoạn đầu — thủ công)

1. Mở `index.html` bằng VS Code / Cursor  
2. Sửa các hàm đầu script:  
   - `ASOF`  
   - `loadUSYields()` / `loadVNYields()`  
   - `loadBreadth()` (hoặc neo phiên cuối)  
   - `loadMargin()`  
3. Lưu → `git commit` + `git push`  

Sau này (phase pipeline): job ghi `data/snapshot-latest.json`, HTML chỉ `fetch` — xem `vn-market-dashboard-ops-design.md`.

---

## Custom domain (optional, ~100–300k VND/năm)

Ví dụ domain `thitruong.example.org`:

### GitHub Pages

1. Domain provider → DNS:  
   - `CNAME` `thitruong` → `YOUR_USER.github.io`  
2. Repo Settings → Pages → Custom domain → nhập `thitruong.example.org` → Save  
3. Bật **Enforce HTTPS**

### Cloudflare Pages

1. Add domain trong project  
2. Cloudflare hướng dẫn record DNS (thường tự nếu domain cũng ở CF)

---

## Bảo mật tối thiểu (non-profit)

| Việc | Trạng thái |
|------|------------|
| HTTPS | Pages/Cloudflare tự có |
| Không nhúng API key trong HTML | Bắt buộc |
| 2FA GitHub | Nên bật |
| Repo public = ai cũng xem code + số | OK nếu chỉ data công khai |
| Không commit file `.env`, token | Kiểm tra trước `git push` |

---

## Sự cố thường gặp

| Hiện tượng | Cách xử lý |
|------------|------------|
| 404 trên GitHub Pages | Đợi 2 phút; kiểm tra branch `main`, folder `/root`; URL có đúng tên repo |
| CSS/font lỗi | Cần mạng (Google Fonts); hoặc mở DevTools xem bị chặn |
| Nav 404 `vn-market-dashboard_13.html` | Dùng bộ `vn-market-site` (đã trỏ `index.html` / `the-gioi.html`) |
| `git push` bị từ chối | `git pull --rebase origin main` rồi push lại; hoặc sai token |
| Trang cũ không đổi | Hard refresh `Ctrl+F5`; xóa cache CDN vài phút |

---

## Checklist “đã lên production”

- [ ] URL HTTPS mở được  
- [ ] Trong nước + Thế giới link chéo OK  
- [ ] Footer disclaimer còn  
- [ ] Nhãn Mẫu / Proxy / Nội suy còn (tránh hiểu nhầm official)  
- [ ] 1 người biết `git push` khi cập nhật  
- [ ] (Optional) Bookmark URL cho team non-profit  

---

## Liên kết tài liệu liên quan

- Vận hành data / pipeline: `../vn-market-dashboard-ops-design.md`  
- File gốc chỉnh sửa: `../vn-market-dashboard_13.html`  

Sau khi push xong, URL của bạn sẽ là:

```text
https://YOUR_USER.github.io/vn-market-dashboard/
```
