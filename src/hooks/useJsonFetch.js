import { useEffect, useState } from "react";

/**
 * Nền dùng chung cho mọi hook fetch 1 file JSON tĩnh dưới public/data/ —
 * useLiveMarketData/useSectorFlows/useCashout/useNews/useRegime đều bọc
 * quanh hook này thay vì tự lặp lại boilerplate fetch + cancelled-guard +
 * status machine (trước đây mỗi hook viết lại y hệt đoạn này).
 *
 * status: "loading" | "ready" | "error". "error" = fetch thất bại (404/
 * network) — hook gọi nó tự quyết định coi lỗi là "ready với dữ liệu rỗng"
 * hay giữ nguyên "error" tuỳ ngữ cảnh hiển thị (xem useNews.js/useLiveMarketData.js
 * để thấy 2 cách xử lý khác nhau trên cùng 1 nền).
 */
export function useJsonFetch(url) {
  const [data, setData] = useState(null);
  const [status, setStatus] = useState("loading");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const res = await fetch(url, { cache: "no-store" });
        if (!res.ok) {
          if (!cancelled) setStatus("error");
          return;
        }
        const json = await res.json();
        if (cancelled) return;
        setData(json);
        setStatus("ready");
      } catch {
        if (!cancelled) setStatus("error");
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [url]);

  return { data, status };
}
