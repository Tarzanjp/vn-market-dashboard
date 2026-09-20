---
name: market-data-sources
description: Sổ tra nguồn dữ liệu thị trường VN và JP đã KIỂM CHỨNG thật — endpoint nào chạy, endpoint nào không và vì sao, cạm bẫy của từng nguồn. Đọc TRƯỚC khi đi tìm nguồn cho một trường dữ liệu mới, để khỏi dò lại từ đầu.
---

# Nguồn dữ liệu thị trường — đã kiểm chứng

Mỗi dòng dưới đây là **kết quả thử thật**, không phải phỏng đoán. Ghi cả nguồn
đã LOẠI và lý do, vì phần lớn thời gian dò nguồn bị đốt vào việc thử lại những
thứ người trước đã thử và bỏ.

Kiểm lần cuối: **2026-09-20**. Endpoint web đổi mà không báo — thấy sai thì
sửa file này ngay, đừng để nó thành bản đồ cũ.

**Trước khi thêm bất kỳ nguồn nào**: đọc `robots.txt` và ghi lại chỉ thị thật
vào đây. CLAUDE.md §1.5 cấm scrape site có ToS cấm. Và không bao giờ né bot
protection (Cloudflare challenge, CSRF) — đó là ranh giới khác với scrape.

---

## 1. Việt Nam

### 1.1 VNDirect finfo — nguồn chính, không cần key

`https://api-finfo.vndirect.com.vn/v4/<resource>?q=<filter>&size=N`
Bộ lọc dạng `field:value~field2:value2`. robots: Cloudflare mặc định,
`User-agent: *  Allow: /` (có chặn `ClaudeBot`, xem §4).

| Resource | Cho gì | Dùng ở |
|---|---|---|
| `stock_prices` | giá/khối lượng từng mã theo `date` | `daily_update.py: fetch_breadth` |
| `foreigns` | `buyVal/sellVal/netVal` từng mã theo `tradingDate` | `daily_update.py: fetch_foreign` |
| `bonds` | metadata trái phiếu | — |

**Cạm bẫy đã sập:**

- `foreigns` trả cả dòng `type: "INDEX"` — **dòng tổng hợp cấp chỉ số**, không
  phải một mã. Cộng chung với từng mã là đếm hai lần cả thị trường: 2026-09-11
  các dòng INDEX thêm −8.831 tỷ, biến ròng −834 tỷ thành −10.575 tỷ. Số sai đó
  lớn hơn cả tổng GTGD phiên (16.123 tỷ). **Chỉ lấy `type == "STOCK"`.**
- `foreigns` trả chứng quyền **hai lần**, một lần `EW` một lần `CW` (287 mã
  trùng ở phiên trên). Giá trị 0 nên vô hại hôm đó, không phải mãi mãi.
- `stock_prices` dùng trường ngày là `date`; `foreigns` dùng `tradingDate`.
  Nhầm sẽ ra `totalElements: 0` chứ không báo lỗi.
- `stock_prices` **không có** trường khối ngoại; `bonds` **chỉ có trái phiếu
  doanh nghiệp**, không có giá, không có coupon. Không có type trái phiếu trong
  `stock_prices` (chỉ STOCK/ETF/IFC).

**Cổng kiểm nên dùng**: `a+d+u == totalElements` (breadth), `mua − bán == ròng`
(foreign), số mã không trùng, số dòng hợp lý so với quy mô sàn.

### 1.2 HNX — lợi suất trái phiếu Chính phủ

`POST https://www.hnx.vn/ModuleReportBonds/Bond_DauThau/Bond_KetQua_DauThau_Default`
body `p_keysearch=&p_pageIndex=1`, header `X-Requested-With: XMLHttpRequest` +
`Referer` trang đấu thầu. Trả **bảng HTML** `<table id="_tableDatas">`.
robots.txt: **404 — không tuyên bố hạn chế nào**.

Cột quan trọng (0-index): 1 `Đợt đấu thầu` · 5 `Kỳ hạn` · 7 `Ngày phát hành` ·
11 `GT trúng thầu` · 18 `Lãi suất trúng thầu`.

**Cạm bẫy:**

- **Đấu thầu trượt vẫn có dòng**: `GT trúng thầu = 0`, lãi suất hiện `0` hoặc
  rỗng. Đọc thẳng là công bố "lợi suất 30 năm = 0%". Phiên 2026-09-10 có 3/5 kỳ
  hạn như vậy. Chỉ nhận dòng `GT trúng thầu > 0` VÀ `lãi suất > 0`.
- **Chỉ trả 10 dòng gần nhất**, không nhận tham số phân trang nào (đã thử
  `p_pageIndex` / `pageIndex` / `p_currentpage` / `p_recordonpage` /
  `txtFromDate` — đều trả đúng 10 dòng đó). Nên phải **tích luỹ** qua nhiều
  ngày: xem `automation/vn_bond_yields.py`, khoá theo mã đợt.
- **TLS: HNX không gửi cert trung gian.** Python stdlib không dựng được chuỗi,
  mọi kết nối hỏng (`openssl` code 21). KHÔNG tắt verify — cert trung gian
  GlobalSign đóng gói sẵn ở `automation/certs/`, nạp qua
  `ctx.load_verify_locations(cafile=...)`. **Hết hạn 2027-07-16**, tải lại ở
  `http://secure.globalsign.com/cacert/gsgccr3evtlsca2025.crt`.
- Đây là lợi suất **sơ cấp**, chỉ đổi vào ngày đấu thầu → `quality = "proxy"`,
  không bao giờ `live`, và mỗi kỳ hạn mang ngày riêng.

### 1.3 Vietcombank — tỷ giá

`https://www.vietcombank.com.vn/api/exchangerates?date=YYYY-MM-DD` → JSON.
robots: `User-agent: *  Allow: /`.
Cũng có `https://portal.vietcombank.com.vn/UserControls/TVPortal.TyGia/pXML.aspx`
(XML, tự ghi "one request every 5 minutes").

**Cạm bẫy:** tham số `date` được **echo nguyên văn** vào trường `Date` của
response kể cả khi không có bảng mới — hỏi thứ Bảy vẫn trả bảng thứ Sáu nhưng
`Date` ghi thứ Bảy. **Chỉ `UpdatedDate` nói thật.**

**KHÔNG PHẢI tỷ giá trung tâm.** `usdVnd`/`usdVndCentral` là tỷ giá NHNN, một
đại lượng khác (25.463 vs VCB mua CK 25.730 / bán 26.110). Ghi chung một key sẽ
tạo bậc nhảy 1–2,5% vô hình trên biểu đồ lịch sử. Dùng key riêng `usdVndVcb`.

### 1.4 Đã LOẠI (đừng thử lại)

| Nguồn | Vì sao |
|---|---|
| **VBMA** `vbma.org.vn/vi/market-data/government-bond-yield` | Có đúng đường cong lợi suất, nhưng là Laravel+Angular sau **Cloudflare challenge + CSRF**. Lấy được = né bot protection. Không làm |
| **SBV / NHNN** | robots cho phép (`Disallow:` rỗng) và trang tải được **với UA trình duyệt thật** (UA đơn giản bị chặn). Nhưng chưa tìm ra trang tỷ giá trung tâm dạng máy đọc được |
| **TCBS** `apipubaws.tcbs.com.vn` | 403 |
| **FireAnt** `restv2.fireant.vn` | 401, cần bearer token của tài khoản |
| **SSI iBoard** `iboard-api.ssi.com.vn/statistics/charts/defaultAllStocks` | Chạy, nhưng chỉ có danh sách mã. TPCP ở đó chỉ là **6 hợp đồng tương lai**, không phải đường cong. Không tìm ra endpoint giá |
| **vnstock** (thư viện) | Không có module trái phiếu/lãi suất. `Trading.price_history` (lấy lịch sử nhiều mã 1 lần) báo **NotImplementedError** ở cả nguồn `VCI` lẫn `KBS` |
| **worldgovernmentbonds.com** | robots mở hoàn toàn, nhưng đường cong render bằng JS |

### 1.5 Hạn mức vnstock (pipeline phụ)

Tier khách = **20 request/phút**, vượt là vnstock **tự dừng tiến trình** (không
phải ném exception bắt được). Giãn 3,2s giữa các lần gọi là an toàn. API key
miễn phí (vnstocks.com/login) nâng lên 60/phút — chưa cấu hình.

Lớp `Vnstock()` đã **ngừng hỗ trợ từ 2025-08-31**, khuyến nghị chuyển
`vnstock.api`. Cả 3 script pipeline phụ còn dùng lớp cũ.

---

## 2. Nhật Bản

### 2.1 Yahoo Finance JP — xếp hạng GTGD ⭐ nguồn tốt nhất tìm được

`https://finance.yahoo.co.jp/stocks/ranking/tradingValueHigh?market=all&page=N`

robots: `User-agent: *` chỉ chặn `/cm/personal/...`, `/portfolio`, `/my` —
trang ranking **được phép**. Không khai `Crawl-delay`.

- **50 dòng/trang**, phân trang bằng `&page=N` (trang 1 không cần tham số).
- Cột: `順位` là **`<th>`**, còn lại **4 `<td>`**: `名称・コード・市場` /
  `取引値` / `前日比` / `売買代金`. Đòi ≥5 `<td>` sẽ ra 0 dòng — lỗi tôi đã mắc.
- `売買代金` là **yên, chính xác tới đồng** (vd `1,818,861,709,000`).
- Mỗi dòng có nhãn thị trường (`東証PRM`/`東証STD`/`東証GRT`) → lọc Prime được
  ngay từ `market=all`, không cần request riêng.
- Có `__PRELOADED_STATE__` nhúng nếu muốn parse JSON thay vì HTML.

**Đã đo độ hội tụ (2026-09-18, market=all):**

| Trang | Số mã | Luỹ kế | % tổng |
|---|---|---|---|
| 1 | 50 | 6,56兆円 | 58% |
| 10 | 500 | 10,42兆円 | 93% |
| **20** | **1.000** | **11,02兆円** | **98,2%** |
| 35 | 1.750 | 11,22兆円 | ~100% |

→ **20 trang là điểm dừng hợp lý**: 98,2% tổng GTGD, ~26 giây ở giãn cách 1,3s.
Đi tiếp 15 trang nữa chỉ thêm 1,8%.

Cùng dữ liệu này phục vụ được cả tổng GTGD, nhóm mã dẫn dắt, và (nếu có bảng
mã→ngành) cả phân rã theo ngành.

### 2.2 Yahoo chart API — giá/khối lượng từng mã, không cần key

`https://query1.finance.yahoo.com/v8/finance/chart/{ma}.T?range=5d&interval=1d`

Bắt buộc có `User-Agent`, nếu không trả "Edge: Too Many Requests". Hậu tố `.T`
cho JP, `.VN` cho VN, không hậu tố cho US. Đã dùng trong
`daily_update.py: fetch_yahoo_quote` và `jp_value_screen_graph/tools/market_data.py`.

`close × volume` = GTGD của mã đó (Toyota 2026-09-18: 3.025 × 46.568.200 =
1.409 億円).

**`v7/finance/quote?symbols=A,B,C` (lấy nhiều mã 1 request) trả HTTP 401** —
cần auth, không dùng được. Nên mỗi mã một request.

### 2.3 Kabutan

robots: cho phép, chặn `/search*` và `/94446337/`, **`Crawl-delay: 3`** — phải
tôn trọng, giãn ≥3,2s.

- Trả **403 nếu không có User-Agent**, 200 nếu có.
- `https://kabutan.jp/themes/?industry=N&market=M` — danh sách mã theo ngành
  kèm PER/PBR. **15 dòng/trang**, chỉ `&page=N` có tác dụng (`&disp`/`&num`/
  `&limit`/`&rows` bị bỏ qua). Trang tự khai dân số dạng `「123銘柄」` — dùng
  làm cổng kiểm. Xem `jp_value_screen_graph/tools/sector_benchmark.py`.
- `https://kabutan.jp/warning/?mode=2_1` / `2_2` — xếp hạng **biến động giá**
  (không phải GTGD), 15 dòng/trang, có `株価` và `出来高`.
- Mã Nhật là **4 ký tự**, mã mới kết thúc bằng chữ cái (`285A`, `146A`).
  `\d{4}` sẽ bỏ sót chúng.
- Trang 日経平均 (`?code=0000`) hiện `出来高` nhưng `売買代金` là `－`.

### 2.4 JPX — chính thống nhưng khó máy đọc

robots: `User-Agent:*  Disallow:` — **cho phép toàn bộ**.

| Trang | Định dạng |
|---|---|
| `/markets/statistics-equities/investor-type/` 投資部門別売買状況 (tuần) | `.xls` **định dạng cũ** — stdlib không đọc được, `openpyxl` cũng không, phải `xlrd` |
| `/markets/statistics-equities/daily/` | PDF |
| `/markets/statistics-equities/misc/` | `.xlsx` |

Đây là **nguồn duy nhất** cho 投資部門別売買状況. Muốn dùng thì phải chấp nhận
thêm dependency đọc Excel.

---

## 3. Bài học chung về cạm bẫy

Bốn loại lỗi đã thực sự xảy ra, cả bốn đều cho ra số **trông hợp lý**:

1. **Dòng tổng hợp lẫn với dòng chi tiết** — `foreigns` type=INDEX. Luôn hỏi
   "mỗi dòng ở đây là một cái gì?" trước khi `sum()`.
2. **Sai bậc đơn vị** — `close` của vnstock là **nghìn đồng**, chia 1e9 thay vì
   1e6 làm ADTV nhỏ đi 1.000 lần. Thứ hạng KHÔNG đổi (sai số là hằng số) nên
   nhìn danh sách không phát hiện được. Luôn đối chiếu với một đường tính độc
   lập cùng bậc độ lớn.
3. **Phân trang dừng sớm** — lấy 15/123 mã rồi tính trung vị, số ra hoàn toàn
   hợp lý. Dừng theo con số **trang tự khai**, không theo số dòng parse được.
4. **Ô trống nghĩa là "trượt", không phải 0** — đấu thầu HNX trượt hiện `0`.

Và một loại thứ năm không phải lỗi dữ liệu mà lỗi đặt tên: **hai đại lượng khác
nhau dùng chung một key** (tỷ giá NHNN vs NHTM; GTGD 1 sàn khớp lệnh vs 3 sàn
toàn phiên). Chúng lệch vài phần trăm — đủ nhỏ để không ai nghi, đủ lớn để sai.

## 4. Về `ClaudeBot` trong robots.txt

Nhiều site (VBMA, VNDirect finfo, FireAnt — đều dùng Cloudflare) có
`User-agent: ClaudeBot  Disallow: /` trong khi `User-agent: *  Allow: /`.

Pipeline chạy dưới UA riêng của dự án từ GitHub Actions, **không phải ClaudeBot**
— chỉ thị đó nhắm vào crawler của Anthropic. Nhưng ghi lại để biết, và nếu có
nghi ngờ thì hỏi chủ dự án trước.
