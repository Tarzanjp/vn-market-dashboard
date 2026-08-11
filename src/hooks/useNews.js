import { useEffect, useState } from "react";

/**
 * Fetches public/data/news.json — the curated news feed produced by the local
 * agent from public/data/news-raw.json (see automation/agent_daily_prompt.md).
 * Returns { items, generatedAtIct, status }. `items` is [] (not null) when the
 * file is missing/empty so callers can render an honest "chưa có tin" state
 * instead of crashing on a null map().
 */
export function useNews() {
  const [items, setItems] = useState(null);
  const [generatedAtIct, setGeneratedAtIct] = useState(null);
  const [status, setStatus] = useState("loading");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const res = await fetch("data/news.json", { cache: "no-store" });
        if (!res.ok) {
          if (cancelled) return;
          setItems([]);
          setStatus("ready");
          return;
        }
        const data = await res.json();
        if (cancelled) return;
        setItems(Array.isArray(data.items) ? data.items : []);
        setGeneratedAtIct(data.generatedAtIct || null);
        setStatus("ready");
      } catch {
        if (cancelled) return;
        setItems([]);
        setStatus("ready");
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  return { items, generatedAtIct, status };
}
