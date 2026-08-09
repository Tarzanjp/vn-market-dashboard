import { useEffect, useState } from "react";

/**
 * Fetches public/data/history/index.json → each listed year's .jsonl file →
 * public/data/events.json. Returns { rows, events, status }. `rows` is the
 * combined, date-sorted history (see automation/README.md for the schema);
 * `events` is the flat events log used to annotate the history chart.
 */
export function useHistory() {
  const [rows, setRows] = useState(null);
  const [events, setEvents] = useState(null);
  const [status, setStatus] = useState("loading");

  useEffect(() => {
    let cancelled = false;

    async function loadYear(year) {
      const res = await fetch(`data/history/${year}.jsonl`, { cache: "no-store" });
      if (!res.ok) return [];
      const text = await res.text();
      return text
        .split("\n")
        .filter((line) => line.trim())
        .map((line) => {
          try {
            return JSON.parse(line);
          } catch {
            return null;
          }
        })
        .filter(Boolean);
    }

    async function load() {
      try {
        const idxRes = await fetch("data/history/index.json", { cache: "no-store" });
        const idx = idxRes.ok ? await idxRes.json() : { years: [] };
        const years = idx.years || [];
        const perYear = await Promise.all(years.map(loadYear));
        const allRows = perYear
          .flat()
          .sort((a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : 0));

        const evRes = await fetch("data/events.json", { cache: "no-store" });
        const ev = evRes.ok ? await evRes.json() : [];

        if (cancelled) return;
        setRows(allRows);
        setEvents(Array.isArray(ev) ? ev : []);
        setStatus("ready");
      } catch {
        if (cancelled) return;
        setRows([]);
        setEvents([]);
        setStatus("ready");
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  return { rows, events, status };
}
