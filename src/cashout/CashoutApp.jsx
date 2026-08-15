import { useEffect, useRef } from "react";
import SiteHeader from "../components/layout/SiteHeader.jsx";
import Footer from "../components/layout/Footer.jsx";
import { useCashout } from "../hooks/useCashout.js";
import { initCashout } from "./cashoutEngine.js";
import "../styles/tokens.css";
import "../styles/layout.css";
import "./cashout.css";

export default function CashoutApp() {
  const { data, status } = useCashout();
  const initedRef = useRef(false);

  useEffect(() => {
    if (status === "loading" || initedRef.current) return;
    initedRef.current = true;
    initCashout(status === "ready" ? data : null);
  }, [status, data]);

  return (
    <>
      <SiteHeader active="cashout" subtitle="Dòng tiền & Cashout · HOSE/HNX">
        <span className="pill" id="dataStatus"><span id="dataStatusText">Đang tải…</span></span>
        <span className="pill"><span className="num" id="clock">--:--:--</span> ICT</span>
      </SiteHeader>

      <main className="wrap">
        <div className="page-hd">
          <div>
            <h2>Dòng tiền &amp; Cashout Monitor</h2>
            <p>Sector Shift &amp; Liquidity Risk Dashboard — GTGD toàn thị trường, khối ngoại, ma trận ngành, và 4 mã dẫn dắt.</p>
          </div>
        </div>

        {/* ① Market Liquidity & Cashout Alert */}
        <section className="panel" style={{ marginTop: 16 }}>
          <div className="p-hd">
            <div>
              <h2>💧 Market Liquidity &amp; Cashout Alert</h2>
              <span className="sub">Đánh giá tổng GTGD toàn thị trường để xác định dòng tiền đang luân chuyển trong nội bộ (sector rotation) hay đang rút hẳn ra ngoài (cashout).</span>
            </div>
          </div>
          <div className="p-body">
            <div className="co-input-row">
              <label htmlFor="turnoverInput">Total Market Turnover / Tổng GTGD toàn thị trường</label>
              <div className="input-group">
                <input type="number" id="turnoverInput" defaultValue={18500} step="100" min="0" max="40000" aria-label="Tổng giá trị giao dịch (tỷ VND)" />
                <span className="unit">VND Billion</span>
              </div>
              <div className="slider-wrap">
                <input type="range" id="turnoverSlider" defaultValue={18500} step="100" min="0" max="30000" aria-label="Slider tổng GTGD" />
              </div>
            </div>

            <div className="co-banner ok" id="cashoutBanner">
              <div className="cb-icon" id="cbIcon">🟢</div>
              <div className="cb-text">
                <p className="cb-title" id="cbTitle">Healthy Rotation / Strong Market Liquidity</p>
                <p className="cb-desc" id="cbDesc" />
              </div>
              <div className="cb-val" id="cbVal" />
            </div>

            <div className="co-scale">
              <div className="seg danger" />
              <div className="seg warn" />
              <div className="seg ok" />
              <div className="marker" id="scaleMarker" />
            </div>
            <div className="co-scale-labels">
              <span>0</span><span>12,000</span><span>20,000</span><span>30,000+</span>
            </div>

            <div className="co-flow-widgets">
              <div className="co-flow-item" id="flowForeign">
                <div className="co-flow-item-hd">
                  <span className="name">Foreign Net Flow <span className="vi">(Khối ngoại Ròng)</span></span>
                </div>
                <div className="co-flow-current">
                  <span className="amt num" id="flowForeignVal" />
                  <span className="unit">VND Billion</span>
                  <span className="dir-tag" id="flowForeignTag" />
                </div>
                <div className="co-flow-form">
                  <input type="number" id="flowForeignInput" step="10" aria-label="Khối ngoại ròng — cập nhật" />
                  <button type="button" onClick={() => window.updateFlow("foreign")}>Cập nhật</button>
                </div>
              </div>

              <div className="co-flow-item" id="flowProp">
                <div className="co-flow-item-hd">
                  <span className="name">Proprietary Flow <span className="vi">(Tự doanh)</span></span>
                </div>
                <div className="co-flow-current">
                  <span className="amt num" id="flowPropVal" />
                  <span className="unit">VND Billion</span>
                  <span className="dir-tag" id="flowPropTag" />
                </div>
                <div className="co-flow-form">
                  <input type="number" id="flowPropInput" step="10" aria-label="Tự doanh — cập nhật" />
                  <button type="button" onClick={() => window.updateFlow("prop")}>Cập nhật</button>
                </div>
                <p className="co-flow-hint">Chưa có nguồn dữ liệu miễn phí cho Tự doanh — luôn cần nhập tay.</p>
              </div>
            </div>
          </div>
        </section>

        {/* ② VN Core Sector Matrix */}
        <section className="panel" style={{ marginTop: 16 }}>
          <div className="p-hd">
            <div>
              <h2>📊 VN Core Sector Matrix</h2>
              <span className="sub">Kết hợp tỷ lệ khối lượng so với trung bình 5 phiên (Vol Ratio) và % thay đổi giá để tự động phân loại dòng tiền theo từng nhóm ngành.</span>
            </div>
          </div>
          <div className="p-body">
            <div className="co-table-scroll">
              <table className="co-table" id="sectorTable">
                <thead>
                  <tr>
                    <th>Sector / Ngành</th>
                    <th>% Change</th>
                    <th>Daily Value (VND B)</th>
                    <th>5D Avg Vol Ratio</th>
                    <th>Classification</th>
                  </tr>
                </thead>
                <tbody id="sectorTableBody" />
              </table>
            </div>
            <div className="co-legend-note">
              <span className="lg-dot" style={{ background: "var(--tang)" }} />Vol Ratio &gt; 1.2 &amp; % Change &gt; 0 → <b style={{ color: "var(--tang)" }}>Cash Inflow (Dòng tiền vào)</b>&nbsp;&nbsp;&nbsp;
              <span className="lg-dot" style={{ background: "var(--giam)" }} />Vol Ratio &gt; 1.2 &amp; % Change &lt; 0 → <b style={{ color: "var(--giam)" }}>Cash Outflow (Tháo chạy)</b>&nbsp;&nbsp;&nbsp;
              <span className="lg-dot" style={{ background: "var(--dim)" }} />Còn lại → Neutral / Rotation<br />
              <span id="sectorDataNote">※ Toàn bộ số liệu ngành là dữ liệu mẫu (preset/simulated), không phải dữ liệu khớp lệnh thật từ HOSE/HNX.</span>
            </div>
          </div>
        </section>

        {/* ③ Market Leader Flow */}
        <section className="panel" style={{ marginTop: 16 }}>
          <div className="p-hd">
            <div>
              <h2>🎯 Market Leader Flow (Ticker Tracking)</h2>
              <span className="sub" id="stocksSub">Giá trị mua/bán của khối ngoại (Foreign Buy/Sell Value) trong phiên của 4 mã dẫn dắt thị trường.</span>
            </div>
          </div>
          <div className="p-body">
            <div className="co-stocks-grid" id="stocksGrid" />
          </div>
        </section>

        <Footer>
          Tổng GTGD, khối ngoại ròng, GTGD/%thay đổi theo ngành, và khối ngoại mua/bán của 4 mã dẫn dắt lấy từ snapshot thật (nguồn VCI qua vnstock) khi trang tải được <code>data/cashout-vn.json</code>.
          5D Avg Vol Ratio là ước tính từ 1 mã đại diện lớn nhất mỗi ngành, không phải toàn ngành. Tự doanh (proprietary flow) không có nguồn miễn phí — luôn là số nhập tay.
          Không sử dụng trực tiếp cho quyết định đầu tư.
        </Footer>
      </main>
    </>
  );
}
