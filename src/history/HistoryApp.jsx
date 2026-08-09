import { useEffect, useRef } from "react";
import SiteHeader from "../components/layout/SiteHeader.jsx";
import Footer from "../components/layout/Footer.jsx";
import { useHistory } from "../hooks/useHistory.js";
import { initHistory } from "./historyEngine.js";
import "../styles/tokens.css";
import "../styles/layout.css";
import "./history.css";

export default function HistoryApp() {
  const { rows, events, status } = useHistory();
  const initedRef = useRef(false);

  useEffect(() => {
    if (status !== "ready" || initedRef.current) return;
    initedRef.current = true;
    initHistory(rows, events);
  }, [status, rows, events]);

  const hasData = rows && rows.length > 0;

  return (
    <>
      <SiteHeader active="history" subtitle="Lịch sử giá · lợi suất · sự kiện vĩ mô">
        <span className="pill">{hasData ? `${rows.length} phiên trong lịch sử` : "Đang tải…"}</span>
      </SiteHeader>

      <main className="wrap">
        <div className="page-hd">
          <div>
            <h2>Lịch sử &amp; Tương quan</h2>
            <p>Đối chiếu VN-Index, lợi suất trái phiếu Mỹ–Việt, DXY, margin, USD/VND với các sự kiện vĩ mô theo thời gian</p>
          </div>
        </div>

        <div className="notice">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="7" stroke="#E08A00" strokeWidth="1.4" /><path d="M8 4.6v4.2M8 11.2v.6" stroke="#E08A00" strokeWidth="1.6" strokeLinecap="round" /></svg>
          <div>
            <b>Về dữ liệu lịch sử.</b> Lợi suất Kho bạc Mỹ và DXY được backfill ~2 năm từ nguồn công khai (US Treasury, Yahoo Finance).
            VN-Index, lợi suất TPCP VN, dư nợ margin, USD/VND, độ rộng HOSE <b>chưa có nguồn lịch sử miễn phí đáng tin cậy</b> — các chuỗi này
            tích luỹ dần mỗi ngày kể từ khi tính năng này triển khai, giống cách các panel <span className="dtag dtag-proxy">Proxy</span> khác trên site hoạt động.
            Sự kiện được ghi nhận thủ công/qua agent nghiên cứu — xem <code>automation/README.md</code>.
          </div>
        </div>

        <section className="panel" style={{ marginTop: 20 }}>
          <div className="p-hd">
            <h2>Biểu đồ chồng lớp (chỉ số hoá base=100)</h2>
            <span className="sub">Bật/tắt chuỗi ở chú giải · di chuột để xem giá trị theo ngày</span>
            <div className="right">
              <div className="seg" id="histRangeSeg">
                <button data-r="3T" aria-pressed="false">3T</button>
                <button data-r="6T" aria-pressed="false">6T</button>
                <button data-r="1N" aria-pressed="true">1N</button>
                <button data-r="all" aria-pressed="false">Tối đa</button>
              </div>
            </div>
          </div>
          <div className="legend" id="seriesLegend" />
          <div className="p-body tight">
            <div className="chart" id="historyChart" />
          </div>
        </section>

        <section className="panel" style={{ marginTop: 16 }}>
          <div className="p-hd">
            <h2>Bảng tương quan</h2>
            <span className="sub">Pearson trên thay đổi ngày-qua-ngày của các chuỗi đang bật</span>
          </div>
          <div className="p-body" id="corrTable" />
        </section>

        <section className="panel" style={{ marginTop: 16 }}>
          <div className="p-hd">
            <h2>Sự kiện vĩ mô</h2>
            <span className="sub">Đánh dấu trên biểu đồ phía trên</span>
            <div className="right">
              <div className="seg" id="eventCatSeg">
                <button data-c="all" aria-pressed="true">Tất cả</button>
                <button data-c="fed" aria-pressed="false">Fed</button>
                <button data-c="us-macro" aria-pressed="false">Vĩ mô Mỹ</button>
                <button data-c="vn-macro" aria-pressed="false">Vĩ mô VN</button>
                <button data-c="geopolitical" aria-pressed="false">Địa chính trị</button>
              </div>
            </div>
          </div>
          <div className="p-body" id="eventsList" />
        </section>

        <Footer>
          Lịch sử &amp; Tương quan · Dữ liệu tham khảo, không phải khuyến nghị đầu tư.
          Tương quan thống kê không hàm ý quan hệ nhân quả.
        </Footer>
      </main>
    </>
  );
}
