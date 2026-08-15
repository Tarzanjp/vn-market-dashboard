/* ============================================================
   Dòng tiền & Cashout — engine kiểu DOM-manipulation, cùng phong cách với
   worldEngine.js/sectorFlowsEngine.js. Nhận `data` đã fetch từ
   public/data/cashout-vn.json (null nếu fetch lỗi/chưa có file — khi đó
   dùng nguyên dữ liệu mẫu bên dưới, không tự bịa số).
   ============================================================ */

// Dữ liệu mẫu (preset/simulated) — fallback khi chưa fetch được cashout-vn.json.
const PRESET_SECTORS = [
  { en: "Securities", vi: "Chứng khoán", chg: 3.1, value: 1420, volRatio: 1.67 },
  { en: "Steel & Materials", vi: "Thép", chg: 2.4, value: 1650, volRatio: 1.58 },
  { en: "Technology", vi: "Công nghệ", chg: 1.5, value: 290, volRatio: 1.31 },
  { en: "Banking", vi: "Ngân hàng", chg: 1.8, value: 4200, volRatio: 1.35 },
  { en: "Logistics", vi: "Vận tải", chg: 0.9, value: 380, volRatio: 0.88 },
  { en: "Utilities", vi: "Điện/Tiện ích", chg: 0.4, value: 520, volRatio: 1.05 },
  { en: "Construction", vi: "Xây dựng", chg: -0.8, value: 310, volRatio: 1.05 },
  { en: "F&B / Retail", vi: "Bán lẻ/Thực phẩm", chg: -0.6, value: 780, volRatio: 0.95 },
  { en: "Oil & Gas", vi: "Dầu khí", chg: -1.3, value: 640, volRatio: 1.25 },
  { en: "Real Estate", vi: "Bất động sản", chg: -2.1, value: 2800, volRatio: 1.42 },
];
const PRESET_STOCKS = [
  { code: "HPG", sector: "Thép / Steel", buy: 452, sell: 381 },
  { code: "TCB", sector: "Ngân hàng / Banking", buy: 318, sell: 296 },
  { code: "VHM", sector: "Bất động sản / Real Estate", buy: 274, sell: 312 },
  { code: "SSI", sector: "Chứng khoán / Securities", buy: 214, sell: 176 },
];
const PRESET_TURNOVER = 18500;
const PRESET_FOREIGN = -320;
const PRESET_PROP = 210;

export function initCashout(data) {
  const el = (id) => document.getElementById(id);

  let SECTOR_DATA = PRESET_SECTORS;
  let LEADING_STOCKS = PRESET_STOCKS;

  const isReal = !!data;
  if (isReal && Array.isArray(data.sectors) && data.sectors.length) {
    SECTOR_DATA = data.sectors
      .filter((s) => s.vol_ratio != null)
      .map((s) => ({ en: s.en, vi: s.vi, chg: s.chg, value: s.value_bn, volRatio: s.vol_ratio }));
  }
  if (isReal && Array.isArray(data.tickers) && data.tickers.length) {
    LEADING_STOCKS = data.tickers.map((t) => ({
      code: t.code, sector: t.sector, buy: t.foreign_buy_bn, sell: t.foreign_sell_bn,
    }));
  }

  /* ============ Đồng hồ ============ */
  function tick() {
    const d = new Date();
    el("clock").textContent = [d.getHours(), d.getMinutes(), d.getSeconds()]
      .map((x) => String(x).padStart(2, "0")).join(":");
  }
  tick();
  setInterval(tick, 1000);

  /* ============ Cashout Alert ============ */
  const numInput = el("turnoverInput");
  const rangeInput = el("turnoverSlider");
  const banner = el("cashoutBanner");
  const cbIcon = el("cbIcon");
  const cbTitle = el("cbTitle");
  const cbDesc = el("cbDesc");
  const cbVal = el("cbVal");
  const scaleMarker = el("scaleMarker");

  function evalCashout(v) {
    if (v >= 20000) {
      return {
        cls: "ok", icon: "🟢",
        title: "Healthy Rotation / Strong Market Liquidity",
        desc: "Dòng tiền vẫn ở lại thị trường. Sự luân chuyển giữa các nhóm ngành (sector rotation) là động lực chính của phiên.",
      };
    }
    if (v >= 12000) {
      return {
        cls: "warn", icon: "🟡",
        title: "Caution: Liquidity Consolidating",
        desc: "Thanh khoản đang co lại. Dòng tiền có xu hướng thu hẹp về một số nhóm ngành/mã trụ thay vì lan toả toàn thị trường.",
      };
    }
    return {
      cls: "danger", icon: "🔴",
      title: "Danger: Market Cashout / Liquidity Crunch",
      desc: "Thanh khoản sụt giảm mạnh — dấu hiệu dòng tiền rút hẳn khỏi thị trường thay vì chỉ luân chuyển giữa các nhóm ngành.",
    };
  }

  function renderCashout(v) {
    const r = evalCashout(v);
    banner.className = "co-banner " + r.cls;
    cbIcon.textContent = r.icon;
    cbTitle.textContent = r.title;
    cbDesc.textContent = r.desc;
    cbVal.innerHTML = v.toLocaleString("en-US") + '<span class="u">VND Billion</span>';
    const pct = Math.max(0, Math.min(100, (v / 30000) * 100));
    scaleMarker.style.left = pct + "%";
  }

  function setTurnover(v) {
    v = Math.max(0, Math.min(40000, v));
    numInput.value = v;
    rangeInput.value = Math.min(30000, v);
    renderCashout(v);
  }

  numInput.addEventListener("input", () => setTurnover(parseFloat(numInput.value) || 0));
  rangeInput.addEventListener("input", () => setTurnover(parseFloat(rangeInput.value) || 0));

  /* ============ Foreign / Proprietary flow ============ */
  function renderFlow(key) {
    const valEl = el(key === "foreign" ? "flowForeignVal" : "flowPropVal");
    const tagEl = el(key === "foreign" ? "flowForeignTag" : "flowPropTag");
    const input = el(key === "foreign" ? "flowForeignInput" : "flowPropInput");
    const v = parseFloat(input.value) || 0;
    const isBuy = v >= 0;
    valEl.textContent = (isBuy ? "+" : "") + v.toLocaleString("en-US");
    valEl.className = "amt num " + (isBuy ? "buy" : "sell");
    tagEl.textContent = isBuy ? "Mua ròng / Net Buy" : "Bán ròng / Net Sell";
    tagEl.className = "dir-tag " + (isBuy ? "buy" : "sell");
  }

  window.updateFlow = function (key) {
    renderFlow(key);
    const item = el(key === "foreign" ? "flowForeign" : "flowProp");
    item.classList.remove("co-flow-flash");
    void item.offsetWidth;
    item.classList.add("co-flow-flash");
  };

  /* ============ VN Core Sector Matrix ============ */
  function classify(chg, volRatio) {
    if (volRatio > 1.2 && chg > 0) return { label: "Cash Inflow", vi: "Dòng tiền vào", cls: "in" };
    if (volRatio > 1.2 && chg < 0) return { label: "Cash Outflow", vi: "Tháo chạy", cls: "out" };
    return { label: "Neutral", vi: "Rotation", cls: "neutral" };
  }

  function renderSectorTable() {
    const tbody = el("sectorTableBody");
    tbody.innerHTML = "";
    const sorted = [...SECTOR_DATA].sort((a, b) => b.chg - a.chg);
    sorted.forEach((s) => {
      const tr = document.createElement("tr");

      const tdName = document.createElement("td");
      const nameSpan = document.createElement("span");
      nameSpan.className = "co-sec-name";
      nameSpan.textContent = s.en;
      const viSpan = document.createElement("span");
      viSpan.className = "vi";
      viSpan.textContent = s.vi;
      nameSpan.appendChild(viSpan);
      tdName.appendChild(nameSpan);

      const tdChg = document.createElement("td");
      const chgSpan = document.createElement("span");
      chgSpan.className = "num " + (s.chg > 0 ? "co-val-up" : s.chg < 0 ? "co-val-down" : "co-val-flat");
      chgSpan.textContent = (s.chg > 0 ? "+" : "") + s.chg.toFixed(1) + "%";
      tdChg.appendChild(chgSpan);

      const tdVal = document.createElement("td");
      const valSpan = document.createElement("span");
      valSpan.className = "num";
      valSpan.style.color = "var(--text)";
      valSpan.textContent = s.value.toLocaleString("en-US");
      tdVal.appendChild(valSpan);

      const tdVol = document.createElement("td");
      const volSpan = document.createElement("span");
      volSpan.className = "co-volratio num" + (s.volRatio > 1.2 ? " hot" : "");
      volSpan.textContent = s.volRatio.toFixed(2) + "x";
      tdVol.appendChild(volSpan);

      const tdFlow = document.createElement("td");
      const c = classify(s.chg, s.volRatio);
      const badge = document.createElement("span");
      badge.className = "co-flow-badge " + c.cls;
      badge.textContent = (c.cls === "in" ? "🟢 " : c.cls === "out" ? "🔴 " : "▪ ") + c.label + " (" + c.vi + ")";
      tdFlow.appendChild(badge);

      tr.appendChild(tdName);
      tr.appendChild(tdChg);
      tr.appendChild(tdVal);
      tr.appendChild(tdVol);
      tr.appendChild(tdFlow);
      tbody.appendChild(tr);
    });
  }

  /* ============ Market Leader Flow ============ */
  function renderStocks() {
    const grid = el("stocksGrid");
    grid.innerHTML = "";
    const maxVal = Math.max(...LEADING_STOCKS.flatMap((s) => [s.buy, s.sell]));

    LEADING_STOCKS.forEach((s) => {
      const net = s.buy - s.sell;
      const isNetBuy = net >= 0;

      const card = document.createElement("div");
      card.className = "co-stock-card";
      card.innerHTML = `
        <div class="co-stock-card-hd">
          <span class="s-name">${s.code}</span>
          <span class="s-sector">${s.sector}</span>
        </div>
        <div class="co-bar-row">
          <div class="bar-label"><span>Foreign Buy Value</span><span class="bar-val num">${s.buy.toLocaleString("en-US")} tỷ</span></div>
          <div class="co-bar-track"><div class="co-bar-fill buy" style="width:${(s.buy / maxVal * 100).toFixed(1)}%"></div></div>
        </div>
        <div class="co-bar-row">
          <div class="bar-label"><span>Foreign Sell Value</span><span class="bar-val num">${s.sell.toLocaleString("en-US")} tỷ</span></div>
          <div class="co-bar-track"><div class="co-bar-fill sell" style="width:${(s.sell / maxVal * 100).toFixed(1)}%"></div></div>
        </div>
        <div class="co-net-row">
          <span class="net-label">Foreign Net Flow</span>
          <span class="net-val co-net-val ${isNetBuy ? "buy" : "sell"} num">
            ${isNetBuy ? "▲" : "▼"} ${isNetBuy ? "+" : ""}${net.toLocaleString("en-US")} tỷ
          </span>
        </div>
      `;
      grid.appendChild(card);
    });
  }

  /* ============ Khởi tạo giá trị ban đầu ============ */
  const initialTurnover = isReal && typeof data.totalTurnoverBn === "number"
    ? Math.round(data.totalTurnoverBn) : PRESET_TURNOVER;
  const initialForeign = isReal && typeof data.foreignNetBn === "number"
    ? Math.round(data.foreignNetBn) : PRESET_FOREIGN;

  el("flowForeignInput").value = initialForeign;
  el("flowPropInput").value = PRESET_PROP;
  setTurnover(initialTurnover);
  renderFlow("foreign");
  renderFlow("prop");
  renderSectorTable();
  renderStocks();

  /* ============ Trạng thái dữ liệu + ghi chú ============ */
  const statusEl = el("dataStatus");
  const statusText = el("dataStatusText");
  const sectorNote = el("sectorDataNote");
  const stocksSub = el("stocksSub");

  if (isReal) {
    statusEl.className = "pill";
    statusText.textContent = "Dữ liệu thật · " + (data.generatedAtIct || "");
    if (Array.isArray(data.sectors) && data.sectors.length) {
      sectorNote.textContent =
        "※ GTGD & % thay đổi là số thật (snapshot " + (data.generatedAtIct || "") + "). " +
        "5D Avg Vol Ratio là ước tính từ 1 mã đại diện lớn nhất mỗi ngành theo GTGD, không phải toàn ngành.";
    }
    if (Array.isArray(data.tickers) && data.tickers.length) {
      stocksSub.textContent =
        "Khối ngoại mua/bán thật (Foreign Buy/Sell Value) trong phiên của 4 mã dẫn dắt — không bao gồm lệnh của NĐT trong nước. " +
        "Độ dài thanh được chuẩn hoá theo giá trị lớn nhất trong 4 mã.";
    }
  } else {
    statusEl.className = "pill";
    statusText.textContent = "Dữ liệu mẫu (preset)";
  }
}
