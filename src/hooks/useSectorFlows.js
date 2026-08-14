import { useEffect, useState } from "react";

/**
 * Fetches public/data/sector-flows.json — 10 chỉ số ngành ICB cấp 1 của HOSE
 * (nguồn VCI qua vnstock, xem automation/sector_flows/). Returns the raw
 * payload plus a `status` flag; `data` is null while loading so callers can
 * render a loading state instead of crashing on missing fields.
 */
export function useSectorFlows() {
  const [data, setData] = useState(null);
  const [status, setStatus] = useState("loading");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const res = await fetch("data/sector-flows.json", { cache: "no-store" });
        if (!res.ok) {
          if (cancelled) return;
          setStatus("error");
          return;
        }
        const json = await res.json();
        if (cancelled) return;
        setData(json);
        setStatus("ready");
      } catch {
        if (cancelled) return;
        setStatus("error");
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  return { data, status };
}
