import SiteHeader from "../components/layout/SiteHeader.jsx";
import Footer from "../components/layout/Footer.jsx";
import "../styles/tokens.css";
import "../styles/layout.css";
import "./guide.css";

export default function GuideApp() {
  return (
    <>
      <SiteHeader active="guide" subtitle="Hướng dẫn đọc dashboard" />

      <main className="wrap">
        <div className="page-hd">
          <div>
            <h2>Hướng dẫn đọc</h2>
            <p>Cách nhìn tổng thể để nhận ra khuynh hướng thị trường — đọc từng tầng dữ liệu như một cái phễu, từ rộng xuống hẹp.</p>
          </div>
        </div>

        <section className="panel" style={{ marginTop: 16 }}>
          <div className="g-hd">
            <h2>Nguyên tắc chung</h2>
          </div>
          <div className="g-body">
            <p>
              Đừng nhìn từng con số riêng lẻ — khuynh hướng nằm ở <strong>sự khớp hay lệch pha
              giữa các lớp dữ liệu</strong>, không phải ở 1 con số đơn lẻ. Đọc theo 4 tầng dưới
              đây, đi từ tổng quát nhất xuống cụ thể nhất; mỗi tầng trả lời đúng 1 câu hỏi và
              giải thích "tại sao" cho tầng phía trên nó.
            </p>
            <p>
              Toàn bộ trang này chỉ dạy <strong>cách đọc dữ liệu</strong>. Hệ thống mô tả hiện
              trạng thị trường, không kết luận thay bạn nên mua hay bán — xem disclaimer ở
              cuối trang.
            </p>
          </div>
        </section>

        <section className="panel" style={{ marginTop: 16 }}>
          <div className="g-hd">
            <span className="tier">Tầng 1</span>
            <h2>Verdict tổng hợp</h2>
          </div>
          <div className="g-body">
            <p>
              Câu hỏi: <strong>"Thị trường đang đồng thuận hay lệch pha?"</strong> Xem ở trang{" "}
              <a href="buc-tranh-thi-truong.html">Bức tranh thị trường</a>.
            </p>
            <p>
              Verdict là trung bình của 4 điểm số thành phần (tầng 2) — nhưng nếu có{" "}
              <strong>cờ lệch pha (divergence)</strong>, cờ đó đè lên điểm trung bình thay vì bị
              trung bình hoá đi. Ví dụ: Liquidity cao + Positioning thấp cùng lúc là bất thường
              (thanh khoản còn ổn nhưng khối ngoại đang rút) — hệ thống gắn cờ cảnh báo thay vì
              lấy trung bình rồi kết luận yên tâm.
            </p>
            <p>
              <strong>Cách hiểu:</strong> verdict "đồng thuận" (4 điểm cùng hướng) đáng tin hơn
              nhiều so với verdict "trung tính" do 2 điểm cao + 2 điểm thấp triệt tiêu nhau —
              bản chất 2 tình huống rất khác nhau dù điểm trung bình có thể giống nhau. Luôn mở
              rộng xem có cờ divergence hay không trước khi tin vào điểm trung bình.
            </p>
          </div>
        </section>

        <section className="panel" style={{ marginTop: 16 }}>
          <div className="g-hd">
            <span className="tier">Tầng 2</span>
            <h2>4 điểm số thành phần</h2>
          </div>
          <div className="g-body">
            <p>Mỗi điểm trả lời một câu hỏi riêng — đọc tách bạch, đừng gộp chung:</p>
            <table className="g-table">
              <thead>
                <tr>
                  <th>Điểm số</th>
                  <th>Câu hỏi nó trả lời</th>
                  <th>Khoẻ mạnh</th>
                  <th>Thận trọng</th>
                  <th>Rủi ro</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><strong>Liquidity</strong><br />Thanh khoản</td>
                  <td>Tiền vào/ra thị trường nhiều hay ít so với lịch sử của chính nó (percentile GTGD)?</td>
                  <td className="num"><span className="g-band healthy">≥ 60</span></td>
                  <td className="num"><span className="g-band caution">30–60</span></td>
                  <td className="num"><span className="g-band danger">&lt; 30</span></td>
                </tr>
                <tr>
                  <td><strong>Positioning</strong><br />Định vị vốn</td>
                  <td>Khối ngoại đang mua ròng hay bán ròng trong 5 phiên gần nhất?</td>
                  <td className="num"><span className="g-band healthy">≥ 60</span></td>
                  <td className="num"><span className="g-band caution">40–60</span></td>
                  <td className="num"><span className="g-band danger">&lt; 40</span></td>
                </tr>
                <tr>
                  <td><strong>Momentum</strong><br />Động lượng ngành</td>
                  <td>Bao nhiêu % ngành ICB đang ở góc "Dẫn dắt/Cải thiện" trên bản đồ RRG?</td>
                  <td className="num"><span className="g-band healthy">≥ 60</span></td>
                  <td className="num"><span className="g-band caution">35–60</span></td>
                  <td className="num"><span className="g-band danger">&lt; 35</span></td>
                </tr>
                <tr>
                  <td><strong>Macro</strong><br />Bối cảnh vĩ mô</td>
                  <td>Tâm lý rủi ro toàn cầu (Fear&amp;Greed Mỹ, xu hướng DXY) đang thuận hay nghịch?</td>
                  <td className="num"><span className="g-band healthy">≥ 60</span></td>
                  <td className="num"><span className="g-band caution">40–60</span></td>
                  <td className="num"><span className="g-band danger">&lt; 40</span></td>
                </tr>
              </tbody>
            </table>
            <p>
              Ví dụ cách đọc: nếu Momentum khoẻ nhưng Positioning yếu, câu chuyện có thể là{" "}
              <em>"tiền trong nước đang xoay vòng giữa các ngành, trong khi dòng tiền quốc tế
              rút"</em> — một khuynh hướng cụ thể, khác hẳn nếu cả 4 điểm cùng thấp (rút toàn
              diện) hay cùng cao (hưng phấn toàn diện). Khi &lt; 20 phiên lịch sử, điểm hiện{" "}
              <code>—</code> (chưa đủ dữ liệu) thay vì một con số suy diễn.
            </p>
          </div>
        </section>

        <section className="panel" style={{ marginTop: 16 }}>
          <div className="g-hd">
            <span className="tier">Tầng 3</span>
            <h2>Ma trận ngành — tiền đang chảy vào/ra đâu</h2>
          </div>
          <div className="g-body">
            <p>
              Câu hỏi: <strong>"Trong khuynh hướng chung đó, tiền đang chảy vào/ra ngành cụ
              thể nào?"</strong> Xem ở mục <em>VN Core Sector Matrix</em> trang{" "}
              <a href="dong-tien-cashout.html">Dòng tiền &amp; Cashout</a> (5 nhóm ngành theo
              GTGD) hoặc đầy đủ 10 ngành ICB tại{" "}
              <a href="dong-tien-nganh.html">Dòng tiền ngành</a>.
            </p>
            <p>
              Nhãn phân loại kết hợp <strong>khối lượng</strong> (so với TB 5 phiên) và{" "}
              <strong>% thay đổi giá</strong> — giảm giá đơn thuần chưa đủ để coi là "tháo
              chạy":
            </p>
            <table className="g-table">
              <thead>
                <tr><th>Điều kiện</th><th>Nhãn</th><th>Ý nghĩa</th></tr>
              </thead>
              <tbody>
                <tr>
                  <td className="num">Vol Ratio &gt; 1.2 &amp; %Chg &gt; 0</td>
                  <td>🟢 Cash Inflow</td>
                  <td>Dòng tiền vào — khối lượng cao hơn bình thường kèm giá tăng</td>
                </tr>
                <tr>
                  <td className="num">Vol Ratio &gt; 1.2 &amp; %Chg &lt; 0</td>
                  <td>🔴 Cash Outflow</td>
                  <td>Tháo chạy thật — khối lượng cao hơn bình thường kèm giá giảm</td>
                </tr>
                <tr>
                  <td className="num">Còn lại</td>
                  <td>▪ Neutral</td>
                  <td>Biến động giá không đi kèm khối lượng bất thường — luân chuyển bình thường</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section className="panel" style={{ marginTop: 16 }}>
          <div className="g-hd">
            <span className="tier">Tầng 4</span>
            <h2>Bối cảnh định chế — cơ chế, không phải hướng</h2>
          </div>
          <div className="g-body">
            <p>
              Lớp này ở trang <a href="dong-tien-cashout.html">Dòng tiền &amp; Cashout</a> trả
              lời câu hỏi <strong>"cơ chế"</strong> chứ không phải "hướng" — nó giải thích tại
              sao khuynh hướng ở tầng 1-3 diễn ra theo cách đó, không tự nó là tín hiệu:
            </p>
            <table className="g-table">
              <thead><tr><th>Chỉ số</th><th>Đọc thế nào</th></tr></thead>
              <tbody>
                <tr>
                  <td><strong>Năng lực hấp thụ vốn</strong> (capacity)</td>
                  <td>Số phiên cần để giải ngân/rút một khoản vốn nếu tự giới hạn ≤15% GTGD/phiên. Số càng thấp → thanh khoản càng sâu (dễ dịch chuyển vốn lớn mà không tự đẩy giá); số càng cao → thị trường/mã đó càng "nông".</td>
                </tr>
                <tr>
                  <td><strong>Room ngoại sắp cạn</strong></td>
                  <td>Room = 0% nghĩa là khối ngoại bị <em>chặn cơ học</em> (phải giao dịch thoả thuận), không phải họ không muốn mua thêm — đừng nhầm giới hạn kỹ thuật với tín hiệu cầu.</td>
                </tr>
                <tr>
                  <td><strong>P/E · P/B · ROE bình quân nhóm dẫn dắt</strong></td>
                  <td>Định giá bình quân (theo tỷ trọng GTGD) của 10 mã đang dẫn dắt dòng tiền hôm nay — so với mức bạn quen thuộc để biết dòng tiền đang tập trung vào nhóm định giá cao hay thấp.</td>
                </tr>
                <tr>
                  <td><strong>Cô đặc vốn hoá</strong> (top 5/10 mã)</td>
                  <td>% tổng vốn hoá do vài mã lớn nhất nắm giữ — càng cao thì rủi ro tương quan càng lớn nếu phân bổ theo tỷ trọng vốn hoá (vài mã biến động mạnh sẽ kéo cả chỉ số).</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section className="panel" style={{ marginTop: 16, marginBottom: 20 }}>
          <div className="g-hd">
            <h2>Tóm lại</h2>
          </div>
          <div className="g-body">
            <div className="g-summary">
              <strong>Verdict + divergence</strong> → điểm nào lệch → <strong>ngành nào lệch</strong> → bối cảnh cơ chế (capacity/room/định giá) giải thích tại sao. Đi từ trên xuống, mỗi tầng trả lời "tại sao" cho tầng ngay phía trên nó.
            </div>
          </div>
        </section>

        <Footer>
          Trang này hướng dẫn cách đọc dữ liệu đã có trên dashboard — không thêm nguồn dữ liệu
          hay công thức mới, không tự cập nhật theo phiên. Ngưỡng band ở Tầng 2 lấy trực tiếp
          từ công thức đang chạy (<code>automation/vn_regime/compute_regime.py</code>), là
          ngưỡng v1 chưa hiệu chỉnh bằng backtest thật — xem trang Bức tranh thị trường để biết
          giới hạn cụ thể.
          Không sử dụng trực tiếp cho quyết định đầu tư.
        </Footer>
      </main>
    </>
  );
}
