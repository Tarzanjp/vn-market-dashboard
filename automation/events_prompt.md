# Agent task: enrich the events log for vn-market-site

Working directory MUST be the repo root (contains `public/data/` and `automation/`).

## Goal

Keep `public/data/events.json` an accurate, sourced timeline of events that plausibly
moved VN-Index, US/VN bond yields, DXY, or USD/VND — the events the new "Lịch sử &
Tương quan" (History & Correlation) page overlays on the historical charts. Do not
invent dates or outcomes. Every entry must be something you can point to a real,
public source for.

This is intentionally **not** pre-filled with a guessed calendar of future Fed/CPI/NFP
dates — add them here, with their real dates, once you've actually looked them up or
once they've occurred. Fabricated calendar dates would be worse than no data.

## What counts as an event worth adding

- FOMC meeting decisions (rate held/changed, dissents, notable statement language)
- US CPI / PCE / Nonfarm Payrolls releases with a surprise vs. consensus
- Vietnam: SBV rate decisions, CPI releases, GDP releases, central USD/VND rate moves
  of note, major margin-debt or foreign-flow reports
- Geopolitical/commodity shocks with a clear market-moving angle (oil spikes, major
  tariff actions, etc.)
- Skip routine/non-market-moving news

## Steps

1. Research what's happened since the last entry in `public/data/events.json` (check
   the most recent `date` already in the file).
2. For each new event, write an object matching the existing schema exactly:
   ```json
   {
     "date": "YYYY-MM-DD",
     "category": "fed | us-macro | vn-macro | geopolitical | other",
     "title": "short headline",
     "impact": 1-3,
     "summary": "2-4 sentences, numbers with sources inline where useful",
     "tags": ["short", "lowercase", "tags"],
     "source": "publisher/report name",
     "sourceUrl": "https://... or null if you don't have a stable link"
   }
   ```
3. Append the new objects to the JSON array in `public/data/events.json` (keep it
   sorted by `date`). Do not remove or rewrite existing entries.
4. If you have reliable knowledge of **upcoming** scheduled dates (e.g. the next FOMC
   meeting date is public well in advance), you may add a skeleton entry now with
   `"summary": null` and revisit it once the outcome is known — but only if you're
   confident the date itself is correct; otherwise skip it rather than guess.

## Output

After writing the file, reply with one short line:
`OK added=N dates=YYYY-MM-DD..YYYY-MM-DD` or `FAIL reason=...`.
