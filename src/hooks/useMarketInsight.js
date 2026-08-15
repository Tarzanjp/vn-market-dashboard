import { useJsonFetch } from "./useJsonFetch.js";

/**
 * Fetches public/data/vn-insight.json — basis hợp đồng tương lai VN30F1M so
 * với VN30 giao ngay + giao dịch cổ đông lớn/nội bộ 30 mã VN30 (nguồn VCI
 * qua vnstock, xem automation/vn_insight/). `data` là null khi đang tải hoặc
 * lỗi; component gọi hook này tự quyết định hiển thị trạng thái thiếu dữ liệu.
 */
export function useMarketInsight() {
  return useJsonFetch("data/vn-insight.json");
}
