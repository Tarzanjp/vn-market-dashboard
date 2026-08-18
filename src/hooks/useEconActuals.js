import { useJsonFetch } from "./useJsonFetch.js";

/**
 * Fetches public/data/econ-actuals.json — actual/forecast/previous figures
 * for the hand-maintained CAL entries in dashboardEngine.js, keyed by each
 * CAL row's `date`. Written by the local agent (Task 3 of
 * automation/agent_daily_prompt.md) when a raw news item explicitly states
 * a number for one of the pending scheduled releases, or by hand the same
 * way grok-fill.json is. Tolerant of the file not existing yet or being
 * empty — dashboardEngine.js's CAL render already shows "—" for anything
 * not found here, same pattern as useNews.js.
 */
export function useEconActuals() {
  const { data, status } = useJsonFetch("data/econ-actuals.json");
  const items = data?.items && typeof data.items === "object" ? data.items : {};
  return { items, status: status === "error" ? "ready" : status };
}
