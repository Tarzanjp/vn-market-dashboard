# Agent thay vì xAI API trong GitHub Actions

## Có được không?

**Có.** Thay vì `XAI_API_KEY` trên GitHub Actions, bạn có thể dùng **Grok agent** (Grok Build / `grok -p` headless) chạy trên máy (hoặc máy luôn bật) để:

1. Lấy tin/số (web_search / browse / kiến thức phiên)  
2. Ghi `data/grok-fill.json`  
3. Chạy `scripts/daily_update.py` (API free + merge)  
4. `git push` → GitHub Pages tự deploy  

GitHub Actions **chỉ còn** deploy Pages (không cần gọi xAI).

---

## So sánh 2 kiểu auto

| | **GitHub Actions + XAI_API_KEY** | **Grok Agent (local / máy luôn mở)** |
|--|--------------------------------|--------------------------------------|
| Chạy ở đâu | Cloud GitHub | Máy bạn / PC always-on |
| Grok | API xAI (trả theo token) | Subscription Grok Build / grok CLI |
| Secret | `XAI_API_KEY` trên GitHub | Login `grok` local (`auth.json`) |
| Lịch | Cron Actions (UTC) | Windows Task Scheduler / cron |
| Free API (UST, VNI…) | Actions hoặc agent đều chạy `daily_update.py` | Agent gọi cùng script |
| Rủi ro | Key trên cloud | Máy phải bật đúng giờ |

**Non-profit:** Agent local thường **đơn giản hơn** nếu đã dùng Grok hàng ngày — không cần mua thêm API console.

---

## Kiến trúc khuyến nghị (agent-first)

```
Windows Task Scheduler (08:20 & 16:10 ICT)
        │
        ▼
  grok -p --prompt-file scripts/agent_daily_prompt.md --yolo
        │  (agent: research → ghi data/grok-fill.json)
        ▼
  py scripts/daily_update.py --no-grok
        │  (free API + merge grok-fill, KHÔNG gọi XAI_API)
        ▼
  git add data && git commit && git push
        │
        ▼
  GitHub Actions: Deploy static site to Pages
```

`--no-grok` = không dùng XAI_API_KEY trong script; phần “Grok” đã do **agent CLI** lo.

---

## Cài đặt agent daily (Windows)

### 0. Điều kiện

- Đã cài Grok CLI (`grok --version`)  
- Đã login (`grok` mở browser login)  
- Repo local: `C:\Users\shimo\Downloads\vn-market-site`  
- `git push` được (token/credential)  

### 1. Thử tay 1 lần

```powershell
cd C:\Users\shimo\Downloads\vn-market-site

# Agent research + ghi grok-fill.json (cần grok trên PATH)
grok -p --prompt-file scripts/agent_daily_prompt.md --yolo --cwd "C:\Users\shimo\Downloads\vn-market-site"

# Free API + merge (không gọi xAI API)
py scripts/daily_update.py --no-grok

git add data
git commit -m "data: agent daily fill"
git push origin main
```

### 2. Script gói sẵn

```powershell
powershell -ExecutionPolicy Bypass -File C:\Users\shimo\Downloads\vn-market-site\scripts\run_agent_daily.ps1
```

### 3. Lịch Windows Task Scheduler

1. Mở **Task Scheduler** → Create Basic Task  
2. Name: `VN Market Agent Daily`  
3. Trigger: **Daily** 08:20 và thêm trigger 16:10 (hoặc 2 task)  
4. Action: Start a program  

| Field | Value |
|-------|--------|
| Program | `powershell.exe` |
| Arguments | `-ExecutionPolicy Bypass -File "C:\Users\shimo\Downloads\vn-market-site\scripts\run_agent_daily.ps1"` |
| Start in | `C:\Users\shimo\Downloads\vn-market-site` |

5. Conditions: bỏ “Start only if on AC power” nếu laptop  
6. Settings: “Run task as soon as possible after a scheduled start is missed”  

---

## Tắt Grok API trên GitHub Actions (nếu chỉ dùng agent)

Không cần xóa workflow. Chỉ **đừng tạo** secret `XAI_API_KEY`.

Log sẽ có: `Grok auto: skip (no XAI_API_KEY secret)` — vẫn fetch free API + merge `grok-fill.json` nếu agent đã push file đó.

Hoặc đổi job Actions chỉ còn:

```yaml
run: python scripts/daily_update.py --no-grok
```

(khi agent đã push `grok-fill.json` + optional pre-merged live.js).

---

## Grok Build scheduler (trong app Grok)

Trong session Grok Build, có thể tạo scheduled task (interval, ví dụ `1d`) với prompt tương tự `agent_daily_prompt.md`.  

Lưu ý:

- Task trong app **hết hạn sau 7 ngày** (theo product) → phải renew  
- Windows Task Scheduler **ổn định hơn** cho non-profit lâu dài  

---

## An toàn

- Agent `--yolo` chỉ nên dùng trên máy bạn, cwd = repo site  
- Không commit API key  
- Số agent/Grok = **proxy** — UI đã có nhãn  
- Review `git log` / `data/last-run.json` thỉnh thoảng  

---

## Kết luận

| Câu hỏi | Trả lời |
|---------|---------|
| Setting agent thay xAI Action được không? | **Được** |
| Cách hay nhất non-profit? | **Agent local + Task Scheduler** + `daily_update.py --no-grok` + git push |
| Còn cần GitHub Actions? | **Có** — chỉ deploy Pages (và optional fetch free API nếu agent không chạy) |
