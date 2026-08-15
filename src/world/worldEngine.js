import { MARKETS as MARKETS_SRC, SUB_ORDER, GRP_NAME, GRP_ORDER, GRP_DESC, SUB_GRP, SUB_PRI, SUBDESC, TV } from "../data/worldInstruments.js";

/* ============================================================
   World Indices engine — ported near-verbatim from the legacy
   the-gioi.html inline <script>. See dashboardEngine.js for the
   rationale on keeping this as DOM-manipulating code rather than
   idiomatic React state.
   ============================================================ */
export function initWorldIndices() {
  let MARKETS = MARKETS_SRC.map(m => ({ ...m }));
  MARKETS.sort((a, b) => SUB_ORDER.indexOf(a.sub) - SUB_ORDER.indexOf(b.sub));
  MARKETS.forEach(m => { m.tv = TV[m.id] || ""; });
  const tvChartURL = sym => "https://www.tradingview.com/chart/?symbol=" + encodeURIComponent(sym);

  /* ============================================================
     2. TIỆN ÍCH
     ============================================================ */
  const el = id => document.getElementById(id);
  const nf = (v, d = 2) => v == null ? "—" : v.toLocaleString("vi-VN", { minimumFractionDigits: d, maximumFractionDigits: d });
  const sgn = (v, d = 2) => v == null ? "—" : (v > 0 ? "+" : v < 0 ? "−" : "") + nf(Math.abs(v), d);
  const cls = v => v == null ? "flat" : v > 0 ? "up" : v < 0 ? "down" : "flat";
  const hhmm = h => {
    const H = Math.floor(h) % 24, M = Math.round((h - Math.floor(h)) * 60);
    return String(H).padStart(2, "0") + ":" + String(M).padStart(2, "0");
  };

  MARKETS.forEach(m => {
    if (m.c == null && m.v != null && m.p != null) m.c = m.v - m.v / (1 + m.p / 100);
  });

  function status(m) {
    const d = new Date(Date.now() + m.tz * 3600000);
    const h = d.getUTCHours() + d.getUTCMinutes() / 60, day = d.getUTCDay();
    const c247 = m.sess[0] === 0 && m.sess[1] === 24;
    if (c247) return { open: day !== 6, label: "Giao dịch 24 giờ", local: hhmm(h) };
    if (day === 0 || day === 6) return { open: false, label: "Nghỉ cuối tuần", local: hhmm(h) };
    const open = h >= m.sess[0] && h < m.sess[1];
    return { open, label: open ? "Đang giao dịch" : (h < m.sess[0] ? "Chưa mở cửa" : "Đã đóng cửa"), local: hhmm(h) };
  }
  const toICT = (h, tz) => ((h - tz + 7) % 24 + 24) % 24;

  /* ============================================================
     3. VẼ Ô CHỈ SỐ
     ============================================================ */
  const EXTICON = `<svg class="t-ext" width="12" height="12" viewBox="0 0 16 16" fill="none" aria-hidden="true">
    <path d="M6.2 2.6H3.4A1.4 1.4 0 0 0 2 4v8.6A1.4 1.4 0 0 0 3.4 14H12a1.4 1.4 0 0 0 1.4-1.4V9.8"
          stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
    <path d="M9.6 2h4.4v4.4M14 2 7.4 8.6" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
  </svg>`;

  function tileHTML(m) {
    const st = status(m), na = m.v == null;
    const k = na ? "t-na" : (m.p > 0 ? "t-up" : m.p < 0 ? "t-down" : "");
    // Luôn dùng biểu đồ TradingView trực tiếp (realtime). Mã nào chưa có mã TV
    // tương ứng trong TV (worldInstruments.js) thì không vẽ gì — trước đây có
    // sparkline giả (random walk theo seed) làm fallback, đã bỏ vì hiển thị số
    // liệu bịa trông giống biểu đồ thật (vi phạm CLAUDE.md §1.5).
    const chart = m.tv ? `<div class="tv-slot" data-sym="${m.tv}"></div>` : "";
    const inner = `
      <div class="t-top">
        <span class="t-name">${m.name}</span>
        <span class="t-cty">${m.cty}</span>
      </div>
      <div class="t-val">${nf(m.v, m.dec)}</div>
      <div class="t-chg">
        <span class="${cls(m.p)}">${sgn(m.c, m.dec)}</span>
        <span class="${cls(m.p)}">${m.p == null ? "—" : sgn(m.p, 2) + "%"}</span>
      </div>
      <div class="t-spark">${chart}</div>
      <div class="t-foot">
        <span class="t-stat ${st.open ? "open" : ""}"><i></i>${st.label}</span>
        ${m.note ? `<span class="t-note">${m.note}</span>` : `<span class="t-note">${st.local} giờ ĐP</span>`}
      </div>`;
    if (!m.tv) return `<article class="tile ${k}">${inner}</article>`;
    return `<a class="tile ${k}" href="${tvChartURL(m.tv)}" target="_blank" rel="noopener"
               title="Mở biểu đồ ${m.name} trên TradingView">${EXTICON}${inner}</a>`;
  }

  /* ============================================================
     4. BẢNG DANH SÁCH
     ============================================================ */
  let sortKey = "grp", sortDir = 1;
  function rowHTML(m) {
    const st = status(m);
    const ict = `${hhmm(toICT(m.sess[0], m.tz))}–${hhmm(toICT(m.sess[1], m.tz))}`;
    const c247 = m.sess[0] === 0 && m.sess[1] === 24;
    return `<tr>
      <td>${m.tv ? `<a class="tvlink" href="${tvChartURL(m.tv)}" target="_blank" rel="noopener">${m.name}</a>`
        : `<b style="font-weight:600">${m.name}</b>`} <span style="color:var(--dim);font-size:11.5px">${m.cty}</span></td>
      <td><span class="grp-tag grp-${m.grp}">${m.sub || GRP_NAME[m.grp]}</span></td>
      <td class="num" style="font-weight:600">${nf(m.v, m.dec)}</td>
      <td class="num ${cls(m.p)}">${sgn(m.c, m.dec)}</td>
      <td class="num ${cls(m.p)}">${m.p == null ? "—" : sgn(m.p, 2) + "%"}</td>
      <td style="color:${st.open ? "var(--tang)" : "var(--dim)"}">${st.label}</td>
      <td class="num" style="color:var(--muted)">${c247 ? "24/24" : ict}</td>
    </tr>`;
  }

  /* ============================================================
     6. WIDGET TRADINGVIEW (nạp khi ô lọt vào tầm nhìn)
     ============================================================ */
  const TV_SCRIPT = "https://s3.tradingview.com/external-embedding/embed-widget-mini-symbol-overview.js";
  let tvObserver = null;
  function mountTV(slot) {
    if (slot.dataset.done) return;
    slot.dataset.done = "1";
    const box = document.createElement("div");
    box.className = "tradingview-widget-container";
    box.style.height = "100%";
    const inner = document.createElement("div");
    inner.className = "tradingview-widget-container__widget";
    inner.style.height = "100%";
    box.appendChild(inner);
    const sc = document.createElement("script");
    sc.type = "text/javascript"; sc.async = true; sc.src = TV_SCRIPT;
    sc.textContent = JSON.stringify({
      symbol: slot.dataset.sym, width: "100%", height: "100%",
      locale: "vi_VN", dateRange: "1M", colorTheme: "light",
      isTransparent: true, autosize: true, chartOnly: true, noTimeScale: true
    });
    box.appendChild(sc);
    slot.appendChild(box);
  }
  function watchTV() {
    if (tvObserver) tvObserver.disconnect();
    const slots = [...document.querySelectorAll(".tv-slot")];
    if (!slots.length) return;
    if (!("IntersectionObserver" in window)) { slots.forEach(mountTV); return; }
    tvObserver = new IntersectionObserver(es => {
      es.forEach(e => { if (e.isIntersecting) { mountTV(e.target); tvObserver.unobserve(e.target); } });
    }, { rootMargin: "250px 0px" });
    slots.forEach(x => tvObserver.observe(x));
  }

  function subBlockHTML(sub, items) {
    const pri = SUB_PRI[sub] ? `<span class="sub-pri">${SUB_PRI[sub]}</span>` : "";
    return `<div class="sub-hd"><h3><span class="region">${sub}</span>${pri}<span class="sub-n">${items.length}</span></h3>${
      SUBDESC[sub] ? `<p>${SUBDESC[sub]}</p>` : ""}</div>` + items.map(tileHTML).join("");
  }
  function tilesHTML(list) {
    const subs = SUB_ORDER.filter(x => list.some(m => m.sub === x));
    if (!subs.length) return list.map(tileHTML).join("");

    if (grp !== "all") {
      return subs.map(sub => subBlockHTML(sub, list.filter(m => (m.sub || "") === sub))).join("");
    }

    return GRP_ORDER.map(g => {
      const gSubs = subs.filter(s => SUB_GRP[s] === g);
      if (!gSubs.length) return "";
      const n = list.filter(m => m.grp === g).length;
      const gHead = `<div class="grp-hd"><h2>${GRP_NAME[g]}<span class="g-badge g-${g}">${n}</span></h2>${
        GRP_DESC[g] ? `<p>${GRP_DESC[g]}</p>` : ""}</div>`;
      return gHead + gSubs.map(sub => subBlockHTML(sub, list.filter(m => (m.sub || "") === sub))).join("");
    }).join("");
  }

  /* ============================================================
     7. ĐIỀU KHIỂN
     ============================================================ */
  let grp = "all", view = "grid";
  function render() {
    const list = MARKETS.filter(m => grp === "all" || m.grp === grp);
    el("tiles").className = "tiles tv-mode";
    el("tiles").innerHTML = list.length ? tilesHTML(list) : `<div class="empty">Không có dữ liệu cho nhóm này.</div>`;
    watchTV();
    const sorted = [...list].sort((a, b) => {
      if (sortKey === "grp") return 0;
      const A = a[sortKey], B = b[sortKey];
      if (A == null) return 1; if (B == null) return -1;
      return (typeof A === "string" ? A.localeCompare(B, "vi") : A - B) * sortDir;
    });
    el("listBody").innerHTML = sorted.map(rowHTML).join("");
    el("count").textContent = list.length + " thị trường";
    const open = MARKETS.filter(m => status(m).open).length;
    el("openCount").textContent = open + " thị trường đang mở";
  }
  el("grpSeg").addEventListener("click", e => {
    const b = e.target.closest("button"); if (!b) return;
    grp = b.dataset.g;
    [...e.currentTarget.children].forEach(x => x.setAttribute("aria-pressed", String(x === b)));
    render();
  });
  el("viewSeg").addEventListener("click", e => {
    const b = e.target.closest("button"); if (!b) return;
    view = b.dataset.v;
    [...e.currentTarget.children].forEach(x => x.setAttribute("aria-pressed", String(x === b)));
    el("gridView").hidden = view !== "grid";
    el("listView").hidden = view !== "list";
  });
  document.querySelectorAll("th.sortable").forEach(th => {
    th.addEventListener("click", () => {
      const k = th.dataset.k;
      if (sortKey === k) sortDir *= -1; else { sortKey = k; sortDir = k === "name" ? 1 : -1; }
      document.querySelectorAll("th.sortable").forEach(x => x.removeAttribute("aria-sort"));
      th.setAttribute("aria-sort", sortDir > 0 ? "ascending" : "descending");
      th.querySelector(".ar").textContent = sortDir > 0 ? "▴" : "▾";
      render();
    });
  });

  function tick() {
    const d = new Date(Date.now() + 7 * 3600000);
    el("clock").textContent = [d.getUTCHours(), d.getUTCMinutes(), d.getUTCSeconds()]
      .map(x => String(x).padStart(2, "0")).join(":");
  }
  tick(); setInterval(tick, 1000);
  // Không tự render() lại định kỳ nữa — mỗi lần render sẽ tạo lại toàn bộ DOM tile,
  // buộc mọi widget TradingView đang chạy phải tải lại từ đầu (xấu trải nghiệm vì
  // widget đã tự cập nhật realtime bên trong iframe của nó rồi).

  render();

  // Số trong worldInstruments.js chỉ là fallback tĩnh (baked lúc viết file).
  // Ghi đè bằng public/data/world-live.json — do automation/daily_update.py
  // fetch qua Yahoo Finance cùng cơ chế với VN-Index/DXY của trang chính.
  // Render tĩnh trước để trang không trắng khi chờ fetch; fetch lỗi/thiếu mã
  // nào thì tile đó giữ nguyên số tĩnh, không có gì vỡ.
  loadLiveOverlay();

  async function loadLiveOverlay() {
    try {
      const res = await fetch("data/world-live.json", { cache: "no-store" });
      if (!res.ok) return;
      const data = await res.json();
      const quotes = data.quotes || {};
      let changed = false;
      MARKETS.forEach(m => {
        const q = quotes[m.id];
        if (!q || q.price == null) return;
        m.v = q.price;
        m.p = q.pct;
        m.c = q.chg;
        changed = true;
      });
      if (changed) render();
    } catch {
      // Không có mạng / file chưa tồn tại — giữ số tĩnh làm dự phòng, không báo lỗi.
    }
  }
}
