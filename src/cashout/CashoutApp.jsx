import { useEffect, useRef } from "react";
import SiteHeader from "../components/layout/SiteHeader.jsx";
import Footer from "../components/layout/Footer.jsx";
import { useCashout } from "../hooks/useCashout.js";
import { useMarketInsight } from "../hooks/useMarketInsight.js";
import { initCashout } from "./cashoutEngine.js";
import "../styles/tokens.css";
import "../styles/layout.css";
import "./cashout.css";

export default function CashoutApp() {
  const { data, status } = useCashout();
  const { data: insight, status: insightStatus } = useMarketInsight();
  const initedRef = useRef(false);

  useEffect(() => {
    if (status === "loading" || insightStatus === "loading" || initedRef.current) return;
    initedRef.current = true;
    initCashout(status === "ready" ? data : null, insightStatus === "ready" ? insight : null);
  }, [status, data, insightStatus, insight]);

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
            <p>Sector Shift &amp; Liquidity Risk Dashboard — GTGD toàn thị trường, khối ngoại, ma trận ngành, và 10 mã dẫn dắt.</p>
          </div>
          <img className="page-mascot" src="mascots/dollar-wave.png" alt="" />
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
              <img className="cb-icon" id="cbIcon" src="mascots/confident-glow.png" alt="" />
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
                  <span className="co-flow-quality" id="flowForeignQ" />
                </div>
                <div className="co-flow-current">
                  <span className="amt num" id="flowForeignVal" />
                  <span className="unit">VND Billion</span>
                  <span className="dir-tag" id="flowForeignTag" />
                </div>
                <p className="co-flow-hint" id="flowForeignHint" />
              </div>

              <div className="co-flow-item" id="flowProp">
                <div className="co-flow-item-hd">
                  <span className="name">Proprietary Flow <span className="vi">(Tự doanh)</span></span>
                  <span className="co-flow-quality" id="flowPropQ" />
                </div>
                <div className="co-flow-current">
                  <span className="amt num" id="flowPropVal" />
                  <span className="unit">VND Billion</span>
                  <span className="dir-tag" id="flowPropTag" />
                </div>
                <p className="co-flow-hint" id="flowPropHint" />
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
              <span className="sub" id="stocksSub">Giá trị mua/bán của khối ngoại (Foreign Buy/Sell Value) trong phiên của 10 mã dẫn dắt thị trường (GTGD lớn nhất, chọn động mỗi phiên).</span>
            </div>
          </div>
          <div className="p-body">
            <div className="co-stocks-grid" id="stocksGrid" />
          </div>
        </section>

        {/* ④ Sắp cạn room ngoại */}
        <section className="panel" style={{ marginTop: 16 }}>
          <div className="p-hd">
            <div>
              <h2>🚧 Sắp cạn room ngoại</h2>
              <span className="sub">Mã có room sở hữu nước ngoài còn lại thấp nhất toàn thị trường (thanh khoản ≥5 tỷ VND/phiên) — khối ngoại gần như không thể mua thêm qua khớp lệnh, phải giao dịch thoả thuận nếu muốn mua tiếp.</span>
            </div>
          </div>
          <div className="p-body">
            <div className="co-table-scroll">
              <table className="co-table" id="roomWatchTable">
                <thead>
                  <tr>
                    <th>Mã</th>
                    <th>Room ngoại còn lại</th>
                    <th>GTGD (tỷ)</th>
                  </tr>
                </thead>
                <tbody id="roomWatchTableBody" />
              </table>
            </div>
          </div>
        </section>

        {/* ⑤ Mức độ cô đặc vốn hoá */}
        <section className="panel" style={{ marginTop: 16 }}>
          <div className="p-hd">
            <div>
              <h2>📐 Mức độ cô đặc vốn hoá</h2>
              <span className="sub">% tổng vốn hoá thị trường do 5/10 mã lớn nhất nắm giữ — rủi ro tương quan khi phân bổ danh mục theo tỷ trọng vốn hoá.</span>
            </div>
          </div>
          <div className="p-body">
            <div className="co-vn30-stats" id="concentrationStats" />
            <div className="co-table-scroll">
              <table className="co-table" id="concentrationTable">
                <thead>
                  <tr>
                    <th>Mã</th>
                    <th>Vốn hoá (tỷ)</th>
                    <th>% Tổng vốn hoá</th>
                  </tr>
                </thead>
                <tbody id="concentrationTableBody" />
              </table>
            </div>
          </div>
        </section>

        {/* ⑤b Năng lực hấp thụ vốn & định giá nhóm dẫn dắt */}
        <section className="panel" style={{ marginTop: 16 }}>
          <div className="p-hd">
            <div>
              <h2>📦 Năng lực hấp thụ vốn & định giá nhóm dẫn dắt</h2>
              <span className="sub">Số phiên cần giải ngân/rút vốn nếu tự giới hạn ≤15% GTGD/phiên (cơ học thực thi lệnh, không phải khuyến nghị quy mô vị thế) — và định giá/cơ cấu sở hữu bình quân theo tỷ trọng GTGD của 10 mã dẫn dắt.</span>
            </div>
          </div>
          <div className="p-body">
            <div className="co-vn30-stats" id="capacityStats" />
            <div className="co-vn30-stats" style={{ marginTop: 10 }} id="leadersRollupStats" />
          </div>
        </section>

        {/* ⑥ Tín hiệu tổ chức (VN30) */}
        <section className="panel" style={{ marginTop: 16 }}>
          <div className="p-hd">
            <div>
              <h2>🏛️ Tín hiệu tổ chức (VN30)</h2>
              <span className="sub">Basis hợp đồng tương lai VN30F1M so với VN30 giao ngay, và giao dịch cổ đông lớn/nội bộ công bố gần đây của 30 mã cấu thành VN30.</span>
            </div>
          </div>
          <div className="p-body">
            <div className="co-vn30-stats" id="vn30Stats" />
            <div className="co-insider-list" id="insiderList" />
          </div>
        </section>

        <Footer>
          Tổng GTGD, khối ngoại ròng, GTGD/%thay đổi theo ngành, và khối ngoại mua/bán của 10 mã dẫn dắt (GTGD lớn nhất, chọn động mỗi phiên) lấy từ snapshot thật (nguồn VCI qua vnstock) khi trang tải được <code>data/cashout-vn.json</code>.
          5D Avg Vol Ratio là ước tính từ 1 mã đại diện lớn nhất mỗi ngành, không phải toàn ngành. Tự doanh (proprietary flow) không có nguồn miễn phí — agent tự động tìm số công khai mỗi ngày (nhãn Proxy khi có); phần lớn phiên sẽ hiện "—" vì báo chí VN hiếm khi công bố số này.
          Room ngoại, top-of-book bid/ask, basis VN30F1M là số thật từ snapshot VCI. Giao dịch cổ đông lớn/nội bộ chỉ theo dõi 30 mã VN30, tiêu đề hiển thị nguyên văn từ công bố HOSE — không tự tách số lượng cổ phiếu.
          P/E, P/B, ROE, tỷ lệ sở hữu của 10 mã dẫn dắt lấy từ báo cáo quý thật (company.ratio_summary/trading_stats) — có độ trễ theo lịch công bố BCTC, không phải số real-time. Mức độ cô đặc vốn hoá tính từ toàn bộ price_board.
          Năng lực hấp thụ vốn (capacity) = vốn ÷ (GTGD phiên hôm nay × 15%) — quy ước participation-rate phổ biến ở bàn giao dịch tổ chức, dùng GTGD của đúng phiên hôm nay (không phải trung bình nhiều phiên); mốc vốn chỉ là minh hoạ để tự quy đổi, không phải khuyến nghị quy mô vị thế. Định giá/sở hữu bình quân nhóm dẫn dắt tính theo tỷ trọng GTGD của 10 mã đó (turnover-weighted) — khác universe top-10 theo vốn hoá ở mục cô đặc vốn hoá bên trên.
          Không sử dụng trực tiếp cho quyết định đầu tư.
        </Footer>
      </main>
    </>
  );
}
