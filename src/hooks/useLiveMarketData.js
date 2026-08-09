import { useEffect, useState } from "react";

/**
 * Fetches public/data/live.json (written daily by automation/daily_update.py).
 * Returns { live, status } — live stays null until the fetch resolves so callers
 * can wait before running data-dependent logic (see dashboard/world engines,
 * which read prev.get(...)-style fallbacks the same way the old inline script did).
 */
export function useLiveMarketData() {
  const [live, setLive] = useState(null);
  const [status, setStatus] = useState("loading");

  useEffect(() => {
    let cancelled = false;
    // Relative path (no leading slash): both pages live in the same directory,
    // and GitHub Pages serves this app from a subpath (/vn-market-dashboard/),
    // not the domain root, so an absolute "/data/live.json" would 404 there.
    fetch("data/live.json", { cache: "no-store" })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (cancelled) return;
        setLive(data || null);
        setStatus("ready");
      })
      .catch(() => {
        if (cancelled) return;
        setLive(null);
        setStatus("ready");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return { live, status };
}
