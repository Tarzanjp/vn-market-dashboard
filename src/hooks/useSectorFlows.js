import { useJsonFetch } from "./useJsonFetch.js";

/**
 * Fetches public/data/sector-flows.json — 10 chỉ số ngành ICB cấp 1 của HOSE
 * (nguồn VCI qua vnstock, xem automation/sector_flows/). `data` là null khi
 * đang tải hoặc lỗi; status "error" khi chưa có file/fetch thất bại.
 */
export function useSectorFlows() {
  return useJsonFetch("data/sector-flows.json");
}
