import { useJsonFetch } from "./useJsonFetch.js";

/**
 * Fetches public/data/news.json — the curated news feed produced by the local
 * agent from public/data/news-raw.json (see automation/agent_daily_prompt.md).
 * Returns { items, generatedAtIct, status }. `items` is [] (not null) once
 * settled — success or failure — so callers can render an honest "chưa có
 * tin" state instead of crashing on a null map(); stays null only while
 * "loading". Unlike useSectorFlows/useCashout, this hook never surfaces
 * "error" to its caller — a fetch failure here has always meant "show the
 * empty state", not "show an error state".
 */
export function useNews() {
  const { data, status } = useJsonFetch("data/news.json");
  const items = status === "loading" ? null : (Array.isArray(data?.items) ? data.items : []);
  const generatedAtIct = data?.generatedAtIct || null;
  return { items, generatedAtIct, status: status === "error" ? "ready" : status };
}
