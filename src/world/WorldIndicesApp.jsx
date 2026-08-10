import { useEffect, useRef } from "react";
import SiteHeader from "../components/layout/SiteHeader.jsx";
import Footer from "../components/layout/Footer.jsx";
import { initWorldIndices } from "./worldEngine.js";
import "../styles/tokens.css";
import "../styles/layout.css";
import "./world.css";

export default function WorldIndicesApp() {
  const initedRef = useRef(false);

  useEffect(() => {
    if (initedRef.current) return;
    initedRef.current = true;
    initWorldIndices();
  }, []);

  return (
    <>
      <SiteHeader active="world" subtitle="Hệ thống theo dõi thị trường tài chính">
        <span className="pill"><span className="dot live" /><span id="openCount">—</span></span>
        <span className="pill"><span className="num" id="clock">--:--:--</span> ICT</span>
      </SiteHeader>

      <main className="wrap">
        <div className="page-hd">
          <div>
            <h2>Thị trường thế giới</h2>
            <p>Góc nhìn chuyên gia CK Việt Nam · Chứng khoán theo khu vực · Tiền tệ · Hàng hoá · Tiền số</p>
          </div>
        </div>

        <div className="notice">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="7" stroke="#E08A00" strokeWidth="1.4" /><path d="M8 4.6v4.2M8 11.2v.6" stroke="#E08A00" strokeWidth="1.6" strokeLinecap="round" /></svg>
          <div>
            <b>Trạng thái dữ liệu.</b> Giá đóng cửa phiên gần nhất là số liệu tham chiếu. Các mục gắn nhãn <span className="t-note">chờ dữ liệu</span> chưa được nối nguồn. Bố cục xếp theo thứ tự quét bảng của chuyên gia CK Việt Nam: <b>Châu Á (JP · Hang Seng trước)</b> → <b>Hoa Kỳ</b> → <b>Châu Âu</b>; hàng hoá ưu tiên dầu → vàng → thép/đồng → nông sản XK.
          </div>
        </div>

        <div className="toolbar">
          <div className="seg" id="grpSeg" role="group" aria-label="Lọc theo nhóm thị trường">
            <button data-g="all" aria-pressed="true">Tất cả</button>
            <button data-g="stock" aria-pressed="false">Chứng khoán</button>
            <button data-g="fx" aria-pressed="false">Tiền tệ</button>
            <button data-g="cmd" aria-pressed="false">Hàng hoá</button>
            <button data-g="crypto" aria-pressed="false">Tiền số</button>
          </div>
          <div className="tool-right">
            <span className="count" id="count" />
            <div className="seg" id="viewSeg" role="group" aria-label="Kiểu hiển thị">
              <button data-v="grid" aria-pressed="true">Lưới</button>
              <button data-v="list" aria-pressed="false">Danh sách</button>
            </div>
          </div>
        </div>

        <p className="tvnote" id="tvNote">
          Biểu đồ trực tiếp do <a href="https://www.tradingview.com/" target="_blank" rel="noopener">TradingView</a> cung cấp, cập nhật theo thời gian thực.
          Giá số trong ô là số đóng cửa/tham chiếu gần nhất; biểu đồ nhỏ mới là dữ liệu realtime.
          Bấm vào ô bất kỳ để mở biểu đồ đầy đủ trên TradingView.
        </p>

        <div id="gridView"><div className="tiles" id="tiles" /></div>

        <div id="listView" hidden>
          <div className="panel"><div className="scroll">
            <table>
              <thead><tr>
                <th className="sortable" data-k="name">Thị trường <span className="ar">▾</span></th>
                <th>Nhóm</th>
                <th className="sortable" data-k="v">Giá trị <span className="ar">▾</span></th>
                <th className="sortable" data-k="c">Thay đổi <span className="ar">▾</span></th>
                <th className="sortable" data-k="p">±% <span className="ar">▾</span></th>
                <th>Trạng thái</th>
                <th>Giờ giao dịch (ICT)</th>
              </tr></thead>
              <tbody id="listBody" />
            </table>
          </div></div>
        </div>

        <Footer>
          Thông tin thị trường · Dữ liệu chỉ phục vụ tham khảo và nghiên cứu, không phải khuyến nghị đầu tư.
          Giá đóng cửa các thị trường được ghi nhận theo múi giờ địa phương nên thời điểm chốt số liệu giữa các khu vực lệch nhau.
          Bố cục tham chiếu ý tưởng từ <a href="https://sekai-kabuka.com/pc-index.html" target="_blank" rel="noopener">sekai-kabuka.com</a>.
          Biểu đồ và dữ liệu thời gian thực do <a href="https://www.tradingview.com/" target="_blank" rel="noopener">TradingView</a> cung cấp.
        </Footer>
      </main>
    </>
  );
}
