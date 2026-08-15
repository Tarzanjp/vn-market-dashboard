import { useEffect, useRef } from "react";
import SiteHeader from "../components/layout/SiteHeader.jsx";
import Footer from "../components/layout/Footer.jsx";
import { useSectorFlows } from "../hooks/useSectorFlows.js";
import { initSectorFlows } from "./sectorFlowsEngine.js";
import "../styles/tokens.css";
import "../styles/layout.css";
import "./sectorFlows.css";

export default function SectorFlowsApp() {
  const { data, status } = useSectorFlows();
  const initedRef = useRef(false);

  useEffect(() => {
    if (status !== "ready" || initedRef.current) return;
    initedRef.current = true;
    initSectorFlows(data);
  }, [status, data]);

  return (
    <>
      <SiteHeader active="sectorFlows" subtitle="Dòng tiền theo ngành · HOSE">
        <span className="pill">
          {status === "ready" ? "10 ngành ICB" : status === "error" ? "Chưa có dữ liệu" : "Đang tải…"}
        </span>
      </SiteHeader>

      <main className="wrap">
        <div className="page-hd">
          <div>
            <h2>Dòng tiền ngành</h2>
            <p>So sánh 10 chỉ số ngành ICB cấp 1 do HOSE tự tính — sức mạnh tương đối so với VN-Index, tỷ trọng thanh khoản, và hướng dịch chuyển theo tháng &amp; quý</p>
          </div>
        </div>

        <div id="sfMetaRow" className="toolbar" style={{ marginTop: 4, fontSize: 12.5, color: "var(--dim)", gap: "8px 18px" }} />

        <details className="sf-method">
          <summary>Phương pháp &amp; giới hạn dữ liệu</summary>
          <div className="sf-method-body">
            <dl>
              <dt>Nguồn</dt><dd id="sfSource" />
              <dt>GTGD ước tính</dt><dd id="sfMethodTurnover" />
              <dt>% thay đổi</dt><dd id="sfMethodReturn" />
              <dt>RRG</dt><dd id="sfMethodRrg" />
              <dt>Giới hạn</dt><dd>HOSE gộp Ngân hàng + Chứng khoán + Bảo hiểm chung một chỉ số Tài chính (VNFIN) — không tách riêng được ngành Ngân hàng qua nguồn miễn phí này.</dd>
            </dl>
          </div>
        </details>

        <div className="toolbar">
          <div className="seg" id="sfFreqSeg" role="group" aria-label="Chọn kỳ">
            <button data-f="daily" aria-pressed="false">Theo ngày</button>
            <button data-f="monthly" aria-pressed="true">Theo tháng</button>
            <button data-f="quarterly" aria-pressed="false">Theo quý</button>
          </div>
          <div className="tool-right">
            <button className="sf-tbtn" id="sfTableToggle" aria-pressed="false">Xem dạng bảng</button>
          </div>
        </div>

        {!data && status !== "error" && (
          <section className="panel" style={{ marginTop: 16, padding: "40px 0" }}>
            <p style={{ textAlign: "center", color: "var(--dim)", fontSize: 13, margin: 0 }}>Đang tải dữ liệu…</p>
          </section>
        )}
        {status === "error" && (
          <section className="panel" style={{ marginTop: 16, padding: "40px 0" }}>
            <p style={{ textAlign: "center", color: "var(--dim)", fontSize: 13, margin: 0 }}>
              Chưa có <code>data/sector-flows.json</code> — chạy <code>automation/sector_flows/fetch_sector_flows.py</code> để tạo dữ liệu.
            </p>
          </section>
        )}

        <section className="panel" style={{ marginTop: 16 }}>
          <div className="p-hd">
            <div>
              <h2>Nhiệt độ ngành theo kỳ</h2>
              <span className="sub">Màu = % thay đổi giá chỉ số ngành so với kỳ trước. Xanh = tăng, đỏ = giảm — đậm hơn là biến động mạnh hơn.</span>
            </div>
            <div className="right"><span className="p-tag" id="sfHeatRange" /></div>
          </div>
          <div className="sf-heat-scroll"><table className="sf-heat" id="sfHeatTable" /></div>
          <div className="sf-heat-legend">
            <span className="num" id="sfHeatMin" />
            <div className="bar" />
            <span className="num" id="sfHeatMax" />
            <span style={{ marginLeft: 8 }}>% thay đổi mỗi kỳ</span>
          </div>
        </section>

        <section className="panel" style={{ marginTop: 16 }}>
          <div className="p-hd">
            <div>
              <h2>Tỷ trọng thanh khoản từng ngành</h2>
              <span className="sub">% GTGD ước tính của ngành trên tổng 10 ngành mỗi kỳ — xếp theo tỷ trọng kỳ gần nhất, cao xuống thấp.</span>
            </div>
            <div className="right"><span className="p-tag" id="sfSmRange" /></div>
          </div>
          <div className="p-body tight"><div className="sf-grid" id="sfGrid" /></div>
        </section>

        <section className="panel" style={{ marginTop: 16 }}>
          <div className="p-hd">
            <div>
              <h2>Bản đồ xoay vòng ngành (RRG)</h2>
              <span className="sub">Trục ngang = sức mạnh tương đối so với VN-Index · Trục dọc = tốc độ đổi chiều của sức mạnh đó. Bấm một ngành để làm nổi bật vệt di chuyển.</span>
            </div>
            <div className="right"><span className="p-tag" id="sfRrgRange" /></div>
          </div>
          <div className="p-body tight">
            <div className="sf-rrg-layout">
              <div className="sf-rrg-svg-wrap"><svg id="sfRrgSvg" viewBox="0 0 640 440" /></div>
              <div className="sf-rrg-list" id="sfRrgList" />
            </div>
          </div>
        </section>

        <section className="panel" style={{ marginTop: 16 }} id="sfTableSection">
          <div className="p-hd">
            <div>
              <h2>Bảng dữ liệu</h2>
              <span className="sub">Toàn bộ số liệu đã tính cho kỳ đang chọn.</span>
            </div>
          </div>
          <div className="sf-table-scroll"><table className="sf-data" id="sfDataTable" /></div>
        </section>

        <Footer>
          Dòng tiền ngành · Dữ liệu phi lợi nhuận, chỉ phục vụ tham khảo/nghiên cứu — không phải khuyến nghị đầu tư.
          Nguồn: VCI (qua thư viện mã nguồn mở <code>vnstock</code>), chỉ số ngành do HOSE tự tính. GTGD là ước tính, không phải số khớp lệnh chính thức.
          Sinh lúc <span id="sfGenAt" /> ICT.
        </Footer>
      </main>

      <div id="sfTooltip" />
    </>
  );
}
