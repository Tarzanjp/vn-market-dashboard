import { useEffect, useState } from "react";
import { useJsonFetch } from "./useJsonFetch.js";

/**
 * Fetches public/data/regime.json — verdict tổng hợp từ automation/vn_regime/
 * (Liquidity/Positioning/Momentum/Macro Score + divergence) via the shared
 * useJsonFetch base. Also fetches public/data/history/regime-<currentYear>.jsonl
 * for a trend sparkline — a second, JSONL-shaped fetch that useJsonFetch can't
 * express directly, so it stays as its own effect here, tolerating a thin/
 * missing history file (the engine only started accumulating recently)
 * without treating that as an error.
 */
export function useRegime() {
  const { data: regime, status } = useJsonFetch("data/regime.json");
  const [history, setHistory] = useState([]);

  useEffect(() => {
    if (status !== "ready" || !regime?.date) return;
    let cancelled = false;
    const year = regime.date.slice(0, 4);

    async function loadHistory() {
      try {
        const res = await fetch(`data/history/regime-${year}.jsonl`, { cache: "no-store" });
        if (!res.ok) return;
        const text = await res.text();
        const rows = text
          .split("\n")
          .filter((l) => l.trim())
          .map((l) => {
            try {
              return JSON.parse(l);
            } catch {
              return null;
            }
          })
          .filter(Boolean)
          .sort((a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : 0));
        if (!cancelled) setHistory(rows);
      } catch {
        // lịch sử là phần bổ sung — thiếu cũng không chặn hiển thị verdict
      }
    }

    loadHistory();
    return () => {
      cancelled = true;
    };
  }, [status, regime?.date]);

  return { regime, history, status };
}
