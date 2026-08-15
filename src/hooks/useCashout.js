import { useJsonFetch } from "./useJsonFetch.js";

/**
 * Fetches public/data/cashout-vn.json — GTGD toàn thị trường, khối ngoại
 * ròng, ma trận ngành, khối ngoại mua/bán 4 mã dẫn dắt (nguồn VCI qua
 * vnstock, xem automation/vn_cashout/). `data` là null khi đang tải hoặc
 * lỗi; component gọi hook này tự quyết định fallback về dữ liệu mẫu.
 */
export function useCashout() {
  return useJsonFetch("data/cashout-vn.json");
}
