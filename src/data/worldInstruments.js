/* ============================================================
   Danh mục thị trường thế giới hiển thị ở trang "Thế giới".
   Đóng cửa 07/08/2026 — thay bằng API bằng cách gán lại MARKETS
   rồi gọi render(); cấu trúc giữ nguyên (xem world/worldEngine.js).

   v    : giá trị (null = chờ dữ liệu)
   p    : % thay đổi phiên
   c    : thay đổi tuyệt đối (bỏ trống thì tự suy từ v và p)
   dec  : số chữ số thập phân
   tz   : chênh lệch múi giờ so với UTC
   sess : [mở, đóng] theo giờ địa phương, dạng thập phân
   note : nhãn nhỏ hiển thị góc phải ô
   ============================================================ */
export const MARKETS = [
  /* ============================ CHỨNG KHOÁN ============================
     Góc chuyên gia VN — quét mỗi sáng (theo độ ưu tiên):
     1) VN  2) Châu Á live (JP · Hang Seng dẫn dắt)  3) US phiên đêm
     4) Châu Âu (chiều ICT)  5) Châu Mỹ khác
     Không gộp Mỹ–Âu chung một block. */
  /* 1. Thị trường trong nước */
  { id: "VNINDEX", name: "VN-Index", cty: "HOSE", grp: "stock", sub: "Việt Nam", v: 1768.06, p: 0.19, dec: 2, tz: 7, sess: [9, 15] },
  { id: "VN30", name: "VN30-Index", cty: "HOSE", grp: "stock", sub: "Việt Nam", v: null, p: null, dec: 2, tz: 7, sess: [9, 15], note: "chờ dữ liệu" },
  { id: "HNX", name: "HNX-Index", cty: "HNX", grp: "stock", sub: "Việt Nam", v: null, p: null, dec: 2, tz: 7, sess: [9, 15], note: "chờ dữ liệu" },
  { id: "UPCOM", name: "UPCoM-Index", cty: "UPCoM", grp: "stock", sub: "Việt Nam", v: null, p: null, dec: 2, tz: 7, sess: [9, 15], note: "chờ dữ liệu" },

  /* 2a. Châu Á — tâm điểm: JP & Hang Seng dẫn dắt phiên A-share/ASEAN */
  { id: "N225", name: "Nikkei 225", cty: "Nhật Bản", grp: "stock", sub: "Châu Á — Nhật Bản & Hồng Kông", v: 65482.34, p: -0.31, dec: 2, tz: 9, sess: [9, 15.5] },
  { id: "HSI", name: "Hang Seng", cty: "Hồng Kông", grp: "stock", sub: "Châu Á — Nhật Bản & Hồng Kông", v: 25668.03, p: 0.54, dec: 2, tz: 8, sess: [9.5, 16] },

  /* 2b. Trung Quốc — đối tác thương mại #1 của VN */
  { id: "SSEC", name: "Shanghai Comp.", cty: "Trung Quốc", grp: "stock", sub: "Châu Á — Trung Quốc", v: 3940.04, p: 1.02, dec: 2, tz: 8, sess: [9.5, 15] },
  { id: "SZI", name: "Shenzhen Comp.", cty: "Trung Quốc", grp: "stock", sub: "Châu Á — Trung Quốc", v: 14311.01, p: 1.42, dec: 2, tz: 8, sess: [9.5, 15] },

  /* 2c. Hàn · Đài — chu kỳ bán dẫn, KCN & điện tử VN */
  { id: "KS11", name: "KOSPI", cty: "Hàn Quốc", grp: "stock", sub: "Châu Á — Hàn Quốc & Đài Loan", v: 6258.77, p: -0.60, dec: 2, tz: 9, sess: [9, 15.5] },
  { id: "TWII", name: "TAIEX", cty: "Đài Loan", grp: "stock", sub: "Châu Á — Hàn Quốc & Đài Loan", v: 44225.91, p: -0.38, dec: 2, tz: 8, sess: [9, 13.5] },

  /* 2d. ASEAN — cùng hạng, so dòng vốn ngoại */
  { id: "STI", name: "Straits Times", cty: "Singapore", grp: "stock", sub: "Châu Á — ASEAN", v: 5698.43, p: 1.05, dec: 2, tz: 8, sess: [9, 17] },
  { id: "SET", name: "SET Index", cty: "Thái Lan", grp: "stock", sub: "Châu Á — ASEAN", v: null, p: null, dec: 2, tz: 7, sess: [10, 16.5], note: "chờ dữ liệu" },
  { id: "JKSE", name: "IDX Composite", cty: "Indonesia", grp: "stock", sub: "Châu Á — ASEAN", v: 6409.65, p: 1.04, dec: 2, tz: 7, sess: [9, 16] },
  { id: "KLSE", name: "FTSE Bursa KLCI", cty: "Malaysia", grp: "stock", sub: "Châu Á — ASEAN", v: 1735.75, p: -0.08, dec: 2, tz: 8, sess: [9, 17] },

  /* 2e. Ấn Độ & châu Đại Dương */
  { id: "SENSEX", name: "BSE Sensex", cty: "Ấn Độ", grp: "stock", sub: "Châu Á — Ấn Độ & châu Đại Dương", v: 78499.17, p: -0.58, dec: 2, tz: 5.5, sess: [9.25, 15.5] },
  { id: "AXJO", name: "S&P/ASX 200", cty: "Úc", grp: "stock", sub: "Châu Á — Ấn Độ & châu Đại Dương", v: 9263.60, p: -0.09, dec: 2, tz: 10, sess: [10, 16] },
  { id: "NZ50", name: "S&P/NZX 50", cty: "New Zealand", grp: "stock", sub: "Châu Á — Ấn Độ & châu Đại Dương", v: 13824.13, p: -0.96, dec: 2, tz: 12, sess: [10, 16.75] },

  /* 3. Hoa Kỳ — đã đóng cửa lúc 3–4h sáng ICT, quyết định ATO */
  { id: "SPX", name: "S&P 500", cty: "Mỹ", grp: "stock", sub: "Hoa Kỳ — phiên đêm qua", v: 7757.64, p: 0.62, dec: 2, tz: -4, sess: [9.5, 16], note: "đỉnh lịch sử" },
  { id: "IXIC", name: "Nasdaq Composite", cty: "Mỹ", grp: "stock", sub: "Hoa Kỳ — phiên đêm qua", v: 26690.62, p: 1.30, dec: 2, tz: -4, sess: [9.5, 16] },
  { id: "DJI", name: "Dow Jones", cty: "Mỹ", grp: "stock", sub: "Hoa Kỳ — phiên đêm qua", v: 54036.93, p: 0.28, dec: 2, tz: -4, sess: [9.5, 16] },
  { id: "VIX", name: "VIX", cty: "Mỹ", grp: "stock", sub: "Hoa Kỳ — phiên đêm qua", v: 14.90, p: -1.65, dec: 2, tz: -4, sess: [9.5, 16] },
  { id: "RUT", name: "Russell 2000", cty: "Mỹ", grp: "stock", sub: "Hoa Kỳ — phiên đêm qua", v: 3034.49, p: 1.10, dec: 2, tz: -4, sess: [9.5, 16] },

  /* 4. Châu Âu — mở ~14h ICT, có thể đổi chiều phiên chiều / ATC */
  { id: "GDAXI", name: "DAX", cty: "Đức", grp: "stock", sub: "Châu Âu", v: 26385.46, p: 0.94, dec: 2, tz: 2, sess: [9, 17.5] },
  { id: "SX5E", name: "Euro Stoxx 50", cty: "Eurozone", grp: "stock", sub: "Châu Âu", v: 6545.94, p: 0.67, dec: 2, tz: 2, sess: [9, 17.5] },
  { id: "FTSE", name: "FTSE 100", cty: "Anh", grp: "stock", sub: "Châu Âu", v: 10910.00, p: 0.39, dec: 2, tz: 1, sess: [8, 16.5] },
  { id: "FCHI", name: "CAC 40", cty: "Pháp", grp: "stock", sub: "Châu Âu", v: 8734.93, p: 0.40, dec: 2, tz: 2, sess: [9, 17.5] },
  { id: "BFX", name: "BEL 20", cty: "Bỉ", grp: "stock", sub: "Châu Âu", v: 5814.11, p: 0.94, dec: 2, tz: 2, sess: [9, 17.5] },

  /* 5. Châu Mỹ khác — theo dõi bổ sung */
  { id: "GSPTSE", name: "S&P/TSX", cty: "Canada", grp: "stock", sub: "Châu Mỹ khác", v: 36324.23, p: 0.52, dec: 2, tz: -4, sess: [9.5, 16] },
  { id: "BVSP", name: "Bovespa", cty: "Brazil", grp: "stock", sub: "Châu Mỹ khác", v: 176012.98, p: 0.27, dec: 2, tz: -3, sess: [10, 17] },

  /* ============================ TIỀN TỆ ============================
     Ưu tiên: DXY + USD/VND → cặp quy VND → majors → châu Á so sánh */
  { id: "DXY", name: "Chỉ số USD (DXY)", cty: "ICE", grp: "fx", sub: "Chỉ số USD & tỷ giá USD/VND", v: 99.54, p: -0.43, dec: 2, tz: -4, sess: [0, 24] },
  { id: "USDVND_CB", name: "USD/VND trung tâm", cty: "NHNN", grp: "fx", sub: "Chỉ số USD & tỷ giá USD/VND", v: 25338, p: null, dec: 0, tz: 7, sess: [8, 16], note: "NHNN 31/07" },
  { id: "USDVND", name: "USD/VND", cty: "Vietcombank", grp: "fx", sub: "Chỉ số USD & tỷ giá USD/VND", v: 26085, c: -15, p: -0.06, dec: 0, tz: 7, sess: [8, 16], note: "mua CK 04/08" },

  { id: "EURVND", name: "EUR/VND", cty: "Vietcombank", grp: "fx", sub: "Ngoại tệ quy đổi ra VND", v: 29755.87, c: -123, p: -0.41, dec: 2, tz: 7, sess: [8, 16], note: "mua CK 04/08" },
  { id: "JPYVND", name: "JPY/VND", cty: "Vietcombank", grp: "fx", sub: "Ngoại tệ quy đổi ra VND", v: 162.67, c: -2.03, p: -1.23, dec: 2, tz: 7, sess: [8, 16], note: "mua CK 04/08" },
  { id: "CNYVND", name: "CNY/VND", cty: "FX_IDC", grp: "fx", sub: "Ngoại tệ quy đổi ra VND", v: null, p: null, dec: 2, tz: 7, sess: [0, 24], note: "theo TradingView" },
  { id: "GBPVND", name: "GBP/VND", cty: "Vietcombank", grp: "fx", sub: "Ngoại tệ quy đổi ra VND", v: 34716.04, c: -198.38, p: -0.57, dec: 2, tz: 7, sess: [8, 16], note: "mua CK 04/08" },
  { id: "AUDVND", name: "AUD/VND", cty: "Vietcombank", grp: "fx", sub: "Ngoại tệ quy đổi ra VND", v: 18102.82, c: -126.79, p: -0.70, dec: 2, tz: 7, sess: [8, 16], note: "mua CK 04/08" },
  { id: "KRWVND", name: "KRW/VND", cty: "FX_IDC", grp: "fx", sub: "Ngoại tệ quy đổi ra VND", v: null, p: null, dec: 4, tz: 7, sess: [0, 24], note: "theo TradingView" },
  { id: "SGDVND", name: "SGD/VND", cty: "FX_IDC", grp: "fx", sub: "Ngoại tệ quy đổi ra VND", v: null, p: null, dec: 2, tz: 7, sess: [0, 24], note: "theo TradingView" },
  { id: "THBVND", name: "THB/VND", cty: "FX_IDC", grp: "fx", sub: "Ngoại tệ quy đổi ra VND", v: null, p: null, dec: 2, tz: 7, sess: [0, 24], note: "theo TradingView" },
  { id: "CHFVND", name: "CHF/VND", cty: "FX_IDC", grp: "fx", sub: "Ngoại tệ quy đổi ra VND", v: null, p: null, dec: 2, tz: 7, sess: [0, 24], note: "theo TradingView" },

  { id: "EURUSD", name: "EUR/USD", cty: "Cặp chính", grp: "fx", sub: "Cặp tiền chính toàn cầu", v: null, p: null, dec: 4, tz: 2, sess: [0, 24], note: "theo TradingView" },
  { id: "USDJPY", name: "USD/JPY", cty: "Cặp chính", grp: "fx", sub: "Cặp tiền chính toàn cầu", v: 158.33, p: null, dec: 2, tz: 9, sess: [0, 24], note: "trong phiên 07/08" },
  { id: "GBPUSD", name: "GBP/USD", cty: "Cặp chính", grp: "fx", sub: "Cặp tiền chính toàn cầu", v: null, p: null, dec: 4, tz: 1, sess: [0, 24], note: "theo TradingView" },
  { id: "USDCHF", name: "USD/CHF", cty: "Cặp chính", grp: "fx", sub: "Cặp tiền chính toàn cầu", v: null, p: null, dec: 4, tz: 2, sess: [0, 24], note: "theo TradingView" },
  { id: "USDCAD", name: "USD/CAD", cty: "Cặp chính", grp: "fx", sub: "Cặp tiền chính toàn cầu", v: null, p: null, dec: 4, tz: -4, sess: [0, 24], note: "theo TradingView" },
  { id: "AUDUSD", name: "AUD/USD", cty: "Cặp chính", grp: "fx", sub: "Cặp tiền chính toàn cầu", v: null, p: null, dec: 4, tz: 10, sess: [0, 24], note: "theo TradingView" },
  { id: "NZDUSD", name: "NZD/USD", cty: "Cặp chính", grp: "fx", sub: "Cặp tiền chính toàn cầu", v: null, p: null, dec: 4, tz: 12, sess: [0, 24], note: "theo TradingView" },
  { id: "EURJPY", name: "EUR/JPY", cty: "Cặp chéo", grp: "fx", sub: "Cặp tiền chính toàn cầu", v: null, p: null, dec: 2, tz: 9, sess: [0, 24], note: "theo TradingView" },

  { id: "USDCNY", name: "USD/CNY", cty: "Trung Quốc (onshore)", grp: "fx", sub: "Tiền tệ châu Á", v: null, p: null, dec: 4, tz: 8, sess: [0, 24], note: "theo TradingView" },
  { id: "USDCNH", name: "USD/CNH", cty: "Trung Quốc (offshore)", grp: "fx", sub: "Tiền tệ châu Á", v: null, p: null, dec: 4, tz: 8, sess: [0, 24], note: "theo TradingView" },
  { id: "USDKRW", name: "USD/KRW", cty: "Hàn Quốc", grp: "fx", sub: "Tiền tệ châu Á", v: null, p: null, dec: 2, tz: 9, sess: [0, 24], note: "theo TradingView" },
  { id: "USDTWD", name: "USD/TWD", cty: "Đài Loan", grp: "fx", sub: "Tiền tệ châu Á", v: null, p: null, dec: 3, tz: 8, sess: [0, 24], note: "theo TradingView" },
  { id: "USDTHB", name: "USD/THB", cty: "Thái Lan", grp: "fx", sub: "Tiền tệ châu Á", v: null, p: null, dec: 3, tz: 7, sess: [0, 24], note: "theo TradingView" },
  { id: "USDSGD", name: "USD/SGD", cty: "Singapore", grp: "fx", sub: "Tiền tệ châu Á", v: null, p: null, dec: 4, tz: 8, sess: [0, 24], note: "theo TradingView" },
  { id: "USDIDR", name: "USD/IDR", cty: "Indonesia", grp: "fx", sub: "Tiền tệ châu Á", v: null, p: null, dec: 0, tz: 7, sess: [0, 24], note: "theo TradingView" },
  { id: "USDMYR", name: "USD/MYR", cty: "Malaysia", grp: "fx", sub: "Tiền tệ châu Á", v: null, p: null, dec: 4, tz: 8, sess: [0, 24], note: "theo TradingView" },
  { id: "USDINR", name: "USD/INR", cty: "Ấn Độ", grp: "fx", sub: "Tiền tệ châu Á", v: null, p: null, dec: 3, tz: 5.5, sess: [0, 24], note: "theo TradingView" },

  /* ============================ HÀNG HOÁ ============================
     Góc chuyên gia CK VN — độ ưu tiên theo kênh truyền dẫn vào VN:
     1) Dầu (CPI + PLX/GAS/BSR)  2) Vàng (trú ẩn + tỷ giá)
     3) Thép/Đồng (HPG, chu kỳ)  4) Nông sản XK (Robusta, gạo, cao su) */
  { id: "WTI", name: "Dầu WTI", cty: "USD/thùng", grp: "cmd", sub: "Năng lượng", v: 78.18, p: 1.15, dec: 2, tz: -4, sess: [0, 24] },
  { id: "BRENT", name: "Dầu Brent", cty: "USD/thùng", grp: "cmd", sub: "Năng lượng", v: null, p: null, dec: 2, tz: 1, sess: [0, 24], note: "theo TradingView" },
  { id: "NGAS", name: "Khí tự nhiên", cty: "USD/MMBtu", grp: "cmd", sub: "Năng lượng", v: null, p: null, dec: 3, tz: -4, sess: [0, 24], note: "theo TradingView" },

  { id: "GOLD", name: "Vàng giao ngay", cty: "USD/oz", grp: "cmd", sub: "Kim loại quý", v: 4399.70, p: 2.33, dec: 2, tz: -4, sess: [0, 24] },
  { id: "SILVER", name: "Bạc giao ngay", cty: "USD/oz", grp: "cmd", sub: "Kim loại quý", v: null, p: null, dec: 2, tz: -4, sess: [0, 24], note: "theo TradingView" },

  { id: "HRC", name: "Thép cuộn HRC", cty: "USD/tấn", grp: "cmd", sub: "Kim loại công nghiệp", v: null, p: null, dec: 2, tz: -4, sess: [0, 24], note: "theo TradingView" },
  { id: "COPPER", name: "Đồng", cty: "USD/lb", grp: "cmd", sub: "Kim loại công nghiệp", v: null, p: null, dec: 4, tz: -4, sess: [0, 24], note: "theo TradingView" },

  /* Robusta & gạo trước — VN là nước XK hàng đầu; Arabica/đường theo sau */
  { id: "ROBUS", name: "Cà phê Robusta", cty: "USD/tấn", grp: "cmd", sub: "Nông sản xuất khẩu VN", v: null, p: null, dec: 0, tz: 1, sess: [0, 24], note: "theo TradingView" },
  { id: "RICE", name: "Gạo", cty: "USD/cwt", grp: "cmd", sub: "Nông sản xuất khẩu VN", v: null, p: null, dec: 2, tz: -4, sess: [0, 24], note: "theo TradingView" },
  { id: "RUBBER", name: "Cao su", cty: "JPY/kg", grp: "cmd", sub: "Nông sản xuất khẩu VN", v: null, p: null, dec: 1, tz: 9, sess: [0, 24], note: "theo TradingView" },
  { id: "SUGAR", name: "Đường", cty: "US cent/lb", grp: "cmd", sub: "Nông sản xuất khẩu VN", v: null, p: null, dec: 2, tz: -4, sess: [0, 24], note: "theo TradingView" },
  { id: "ARAB", name: "Cà phê Arabica", cty: "US cent/lb", grp: "cmd", sub: "Nông sản xuất khẩu VN", v: null, p: null, dec: 2, tz: -4, sess: [0, 24], note: "theo TradingView" },

  /* ============================ TIỀN SỐ ============================ */
  { id: "BTC", name: "Bitcoin", cty: "USD", grp: "crypto", sub: "Tài sản số", v: 64943.97, p: 1.07, dec: 2, tz: 0, sess: [0, 24] },
  { id: "ETH", name: "Ethereum", cty: "USD", grp: "crypto", sub: "Tài sản số", v: null, p: null, dec: 2, tz: 0, sess: [0, 24], note: "theo TradingView" },
  { id: "BNB", name: "BNB", cty: "USD", grp: "crypto", sub: "Tài sản số", v: null, p: null, dec: 2, tz: 0, sess: [0, 24], note: "theo TradingView" },
  { id: "SOL", name: "Solana", cty: "USD", grp: "crypto", sub: "Tài sản số", v: null, p: null, dec: 2, tz: 0, sess: [0, 24], note: "theo TradingView" },
  { id: "XRP", name: "XRP", cty: "USD", grp: "crypto", sub: "Tài sản số", v: null, p: null, dec: 4, tz: 0, sess: [0, 24], note: "theo TradingView" }
];

/* Thứ tự block — chuyên viên CK Việt Nam quét bảng mỗi sáng.
   Châu Á trước Hoa Kỳ (phiên live cùng giờ HOSE); Mỹ–Âu tách riêng. */
export const SUB_ORDER = [
  "Việt Nam",
  "Châu Á — Nhật Bản & Hồng Kông",
  "Châu Á — Trung Quốc",
  "Châu Á — Hàn Quốc & Đài Loan",
  "Châu Á — ASEAN",
  "Châu Á — Ấn Độ & châu Đại Dương",
  "Hoa Kỳ — phiên đêm qua",
  "Châu Âu",
  "Châu Mỹ khác",
  "Chỉ số USD & tỷ giá USD/VND",
  "Ngoại tệ quy đổi ra VND",
  "Cặp tiền chính toàn cầu",
  "Tiền tệ châu Á",
  "Năng lượng",
  "Kim loại quý",
  "Kim loại công nghiệp",
  "Nông sản xuất khẩu VN",
  "Tài sản số"
];

export const GRP_NAME = { stock: "Chứng khoán", fx: "Tiền tệ", cmd: "Hàng hoá", crypto: "Tiền số" };
export const GRP_ORDER = ["stock", "fx", "cmd", "crypto"];
export const GRP_DESC = {
  stock: "Theo khung giờ phiên Việt Nam: Châu Á đang mở → Hoa Kỳ đã chốt đêm qua → Châu Âu mở buổi chiều. JP & Hang Seng là hai chỉ số dẫn dắt khu vực.",
  fx: "Bắt đầu từ DXY và USD/VND — hai biến số quyết định dòng vốn ngoại và dư địa điều hành của NHNN.",
  cmd: "Ưu tiên dầu (CPI + dầu khí), vàng (trú ẩn & tỷ giá), thép/đồng (HPG, chu kỳ), rồi nông sản xuất khẩu Việt Nam.",
  crypto: "Thước đo khẩu vị rủi ro toàn cầu; ít truyền dẫn trực tiếp vào cổ phiếu VN nhưng thường đi trước nhóm mid/small-cap."
};

export const SUB_GRP = {
  "Việt Nam": "stock",
  "Châu Á — Nhật Bản & Hồng Kông": "stock",
  "Châu Á — Trung Quốc": "stock",
  "Châu Á — Hàn Quốc & Đài Loan": "stock",
  "Châu Á — ASEAN": "stock",
  "Châu Á — Ấn Độ & châu Đại Dương": "stock",
  "Hoa Kỳ — phiên đêm qua": "stock",
  "Châu Âu": "stock",
  "Châu Mỹ khác": "stock",
  "Chỉ số USD & tỷ giá USD/VND": "fx",
  "Ngoại tệ quy đổi ra VND": "fx",
  "Cặp tiền chính toàn cầu": "fx",
  "Tiền tệ châu Á": "fx",
  "Năng lượng": "cmd",
  "Kim loại quý": "cmd",
  "Kim loại công nghiệp": "cmd",
  "Nông sản xuất khẩu VN": "cmd",
  "Tài sản số": "crypto"
};

export const SUB_PRI = {
  "Châu Á — Nhật Bản & Hồng Kông": "Ưu tiên #1 khu vực",
  "Hoa Kỳ — phiên đêm qua": "Quyết định ATO",
  "Năng lượng": "Ưu tiên #1 HH",
  "Kim loại quý": "Ưu tiên #2 HH",
  "Chỉ số USD & tỷ giá USD/VND": "Ưu tiên FX"
};

/* ------------------------------------------------------------
   Mã ký hiệu TradingView — sửa ở đúng một chỗ này.
   Kiểm tra mã tại https://www.tradingview.com/symbols/<mã>/
   Nếu để trống, ô sẽ không mở được biểu đồ.
   ------------------------------------------------------------ */
export const TV = {
  VNINDEX: "HOSE:VNINDEX", VN30: "HOSE:VN30", HNX: "HNX:HNXINDEX", UPCOM: "HNX:UPCOMINDEX",
  N225: "TVC:NI225", HSI: "TVC:HSI", SSEC: "SSE:000001", SZI: "SZSE:399001",
  KS11: "KRX:KOSPI", TWII: "TWSE:TAIEX", STI: "TVC:STI", JKSE: "IDX:COMPOSITE",
  KLSE: "MYX:FBMKLCI", SET: "SET:SET", SENSEX: "BSE:SENSEX", AXJO: "ASX:XJO", NZ50: "NZX:NZ50G",
  SPX: "SP:SPX", IXIC: "NASDAQ:IXIC", DJI: "DJ:DJI", RUT: "TVC:RUT", VIX: "TVC:VIX",
  GSPTSE: "TSX:TSX", BVSP: "BMFBOVESPA:IBOV", FTSE: "TVC:UKX", GDAXI: "XETR:DAX",
  FCHI: "EURONEXT:PX1", SX5E: "TVC:SX5E", BFX: "EURONEXT:BEL20",
  DXY: "TVC:DXY", USDVND_CB: "FX_IDC:USDVND", USDVND: "FX_IDC:USDVND",
  EURVND: "FX_IDC:EURVND", JPYVND: "FX_IDC:JPYVND", GBPVND: "FX_IDC:GBPVND", AUDVND: "FX_IDC:AUDVND",
  CNYVND: "FX_IDC:CNYVND", KRWVND: "FX_IDC:KRWVND", SGDVND: "FX_IDC:SGDVND",
  THBVND: "FX_IDC:THBVND", CHFVND: "FX_IDC:CHFVND",
  EURUSD: "FX:EURUSD", USDJPY: "FX:USDJPY", GBPUSD: "FX:GBPUSD", USDCHF: "FX:USDCHF",
  USDCAD: "FX:USDCAD", AUDUSD: "FX:AUDUSD", NZDUSD: "FX:NZDUSD", EURJPY: "FX:EURJPY",
  USDCNY: "FX_IDC:USDCNY", USDCNH: "FX:USDCNH", USDKRW: "FX_IDC:USDKRW", USDTWD: "FX_IDC:USDTWD",
  USDTHB: "FX_IDC:USDTHB", USDSGD: "FX:USDSGD", USDIDR: "FX_IDC:USDIDR", USDMYR: "FX_IDC:USDMYR",
  USDINR: "FX_IDC:USDINR",
  NGAS: "NYMEX:NG1!", COPPER: "COMEX:HG1!", HRC: "COMEX:HRC1!",
  RICE: "CBOT:ZR1!", ROBUS: "ICEEUR:RC1!", ARAB: "ICEUS:KC1!", RUBBER: "TOCOM:RSS1!", SUGAR: "ICEUS:SB1!",
  BNB: "CRYPTO:BNBUSD", SOL: "CRYPTO:SOLUSD", XRP: "CRYPTO:XRPUSD",
  GOLD: "TVC:GOLD", WTI: "TVC:USOIL", BRENT: "TVC:UKOIL", SILVER: "TVC:SILVER",
  BTC: "CRYPTO:BTCUSD", ETH: "CRYPTO:ETHUSD"
};

/* Ghi chú phân nhóm — góc nhìn chuyên viên chứng khoán / kinh doanh ngoại tệ VN */
export const SUBDESC = {
  "Việt Nam":
    "Điểm xuất phát của mọi phiên. VN-Index cho bức tranh chung; VN30 cho biết nhóm vốn hoá lớn có đang gánh chỉ số hay không — hai chỉ số lệch pha là dấu hiệu dòng tiền phân hoá.",
  "Châu Á — Nhật Bản & Hồng Kông":
    "Hai chỉ số dẫn dắt tâm lý châu Á, giao dịch cùng khung giờ HOSE. Nikkei phản ánh khẩu vị rủi ro risk-on/risk-off khu vực (yen, carry trade); Hang Seng là cầu nối vốn quốc tế vào Trung Quốc và thường dẫn dắt phản ứng của nhà đầu tư nước ngoài với A-share.",
  "Châu Á — Trung Quốc":
    "Đối tác thương mại lớn nhất của Việt Nam. Shanghai/Shenzhen yếu thường đi kèm lo ngại cầu nguyên liệu và đơn hàng gia công; phục hồi mạnh hỗ trợ kỳ vọng xuất khẩu và dòng vốn vào thị trường mới nổi châu Á.",
  "Châu Á — Hàn Quốc & Đài Loan":
    "Thước đo chu kỳ bán dẫn và điện tử toàn cầu. KOSPI và TAIEX ảnh hưởng trực tiếp nhóm khu công nghiệp, linh kiện và chuỗi cung ứng FDI Hàn/Đài tại Việt Nam.",
  "Châu Á — ASEAN":
    "Các thị trường cùng hạng để so sánh dòng vốn ngoại vào khu vực. Khi khối ngoại bán ròng đồng loạt STI/SET/IDX/KLCI, rủi ro lan sang HOSE thường tăng.",
  "Châu Á — Ấn Độ & châu Đại Dương":
    "Sensex là thước đo thị trường mới nổi lớn ngoài Trung Quốc; ASX gắn với hàng hoá (quặng sắt, than) — kênh gián tiếp tới thép và xây dựng Việt Nam.",
  "Hoa Kỳ — phiên đêm qua":
    "Đã chốt lúc 3–4h sáng ICT nên đây là input sẵn có trước ATO. S&P 500 / Nasdaq quyết định tâm lý risk-on; VIX vọt lên thường kéo khối ngoại bán ròng ở thị trường mới nổi. Ưu tiên sau châu Á live vì JP/HSI đang mở cùng phiên.",
  "Châu Âu":
    "Mở cửa khoảng 14h ICT — trùng phiên chiều và ATC. DAX / Euro Stoxx có thể làm đổi chiều đóng cửa trong nước khi Mỹ futures và châu Âu đảo chiều.",
  "Châu Mỹ khác":
    "Theo dõi bổ sung. TSX gắn dầu và kim loại; Bovespa là thước đo khẩu vị rủi ro với thị trường mới nổi.",

  "Chỉ số USD & tỷ giá USD/VND":
    "DXY quyết định hướng USD toàn cầu. Khoảng cách tỷ giá trung tâm – giá ngân hàng cho thấy mức căng: giá CK sát trần biên độ là tín hiệu cầu ngoại tệ vượt cung.",
  "Ngoại tệ quy đổi ra VND":
    "Phục vụ XNK và trả nợ vay ngoại tệ. JPY/VND quan trọng với ODA/FDI Nhật; EUR/VND với dệt may, da giày, thuỷ sản EU; CNY/VND với chuỗi nhập nguyên phụ liệu.",
  "Cặp tiền chính toàn cầu":
    "EUR/USD và USD/JPY chiếm phần lớn rổ DXY — biến động truyền vào sức mạnh USD rồi mới tới VND. USD/JPY còn là thước đo carry trade châu Á.",
  "Tiền tệ châu Á":
    "Đối chiếu trực tiếp của VND. CNY là biến số lớn nhất (VN nhập siêu TQ) — CNY mất giá ép VND điều chỉnh để giữ cạnh tranh XK. KRW, TWD, THB, IDR, MYR: nhóm cùng hạng đo VND mạnh/yếu tương đối.",

  "Năng lượng":
    "Kênh truyền dẫn nhanh nhất vào VN. Dầu WTI/Brent đi thẳng vào CPI qua giao thông và biên LN của GAS, PLX, BSR, PVD, PVS. Khí tự nhiên ảnh hưởng đạm và điện khí.",
  "Kim loại quý":
    "Vàng cạnh tranh trực tiếp với chứng khoán và gây áp lực tỷ giá khi chênh SJC – thế giới doãng rộng. Ưu tiên #2 sau dầu vì Việt Nam có thị trường vàng vật chất rất lớn.",
  "Kim loại công nghiệp":
    "Thép cuộn HRC gắn biên LN HPG, HSG, NKG. Đồng là chỉ báo chu kỳ sản xuất toàn cầu — đồng tăng thường đi cùng risk-on với cổ phiếu nguyên vật liệu.",
  "Nông sản xuất khẩu VN":
    "Robusta và gạo là hai mặt hàng VN giữ vị thế lớn thế giới; giá tăng hỗ trợ LTG, PAN và doanh nghiệp cà phê. Cao su/đường: DPR, PHR, SBT, QNS. Arabica theo sau vì tỷ trọng XK thấp hơn Robusta.",
  "Tài sản số":
    "Không tác động trực tiếp cổ phiếu VN nhưng đo khẩu vị rủi ro đầu cơ toàn cầu; thường đi trước nhóm mid/small-cap trong nước."
};
