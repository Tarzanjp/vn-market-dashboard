import { useJsonFetch } from "./useJsonFetch.js";

/**
 * Fetches public/data/live.json (written daily by automation/daily_update.py).
 * Returns { live, status } — live stays null until the fetch resolves so callers
 * can wait before running data-dependent logic (see dashboard/world engines,
 * which read prev.get(...)-style fallbacks the same way the old inline script did).
 *
 * Unlike useSectorFlows/useCashout, a fetch failure here surfaces as "ready"
 * with live=null rather than "error" — dashboardEngine.js already has its
 * own null-data handling and has never distinguished the two states.
 */
export function useLiveMarketData() {
  const { data, status } = useJsonFetch("data/live.json");
  return { live: data, status: status === "error" ? "ready" : status };
}
