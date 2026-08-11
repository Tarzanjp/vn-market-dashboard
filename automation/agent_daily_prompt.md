# Agent task: daily market fill for vn-market-site

Working directory MUST be: `C:\Users\shimo\OneDrive\ドキュメント\Private\Stock\vn-market-site` (or the repo root that contains `public/data/` and `automation/`).

## Goal

Produce and write `public/data/grok-fill.json` with the latest public Vietnam market session data for the non-profit dashboard. Do not invent numbers. Prefer official or widely cited public sources.

(The output file is still named `grok-fill.json` even when a Claude agent — rather
than the xAI Grok API — produces it; `automation/daily_update.py`'s merge logic
reads this one file regardless of which agent wrote it.)

**Critical — verify tool access before reporting any number.** In prior manual
testing, a differently-worded one-off prompt caused this exact agent to answer a
market-data question with a specific, plausible-looking, entirely fabricated
number while its own transcript literally said "Based on the web search..." even
though the tool-use logs showed zero real `WebSearch`/`WebFetch` calls happened.
So: before writing anything to `grok-fill.json`, confirm each `WebSearch`/`WebFetch`
call in this run actually returned real tool output (not just that you *narrated*
searching). If those tools are unavailable or return nothing usable in this
environment, do **not** fall back to answering from memory/training data — leave
the existing file untouched and say so plainly in your final reply (see `agent-daily.log`
for a real example of this happening safely — that's the correct behavior).

## Steps

1. Determine the latest HOSE trading session date (ICT). Use `WebSearch`/`WebFetch` if needed.
2. Collect what you can reliably find for that session:
   - VN-Index close, change, %
   - HOSE breadth if available (advancers/decliners/unchanged/ceiling/floor, turnover tỷ VND)
   - Margin debt total if publicly reported (daily or weekly — set freq)
   - USD/VND central rate if available
   - VN government bond yields if available
   - Foreign net buy/sell if available
3. Write file `public/data/grok-fill.json` as a pure JSON object (UTF-8), following the schema in `public/data/grok-fill.example.json` and `automation/README.md`.
4. Set `quality.*` to `proxy` for agent-sourced fields. Omit fields you cannot verify.
5. Put source names/URLs in `sourceNotes`.
6. Do NOT run git push unless the user/script asks; writing `grok-fill.json` is enough for the wrapper script.

## Task 2: curate `public/data/news.json` from `public/data/news-raw.json`

This task does **not** need `WebSearch`/`WebFetch` at all — `daily_update.py`
already fetched real RSS headlines (VnEconomy, Federal Reserve official feeds)
into `public/data/news-raw.json` *before* you ran, deterministically, no LLM
involved in that step. Your job here is pure **Read** + reasoning + **Write**,
which is exactly the toolset that actually works in this headless `--bare`
setup (see the WebSearch/WebFetch gap warning above — this task is designed
to route around it, not depend on it).

1. Read `public/data/news-raw.json` (`items`: array of `{title, link,
   description, publishedAt, category, source}`, already deduped and
   date-filtered — `category` is one of `vn-macro | fed | us-macro`).
2. Also read the existing `public/data/news.json` if it exists — carry
   forward any of its items that are still relevant (< 5 days old, not
   superseded by a newer raw item on the same topic) instead of discarding
   everything each run.
3. Select the **3–6 most market-relevant** items across both sources —
   skip routine noise (bank charter/M&A approvals, generic PR). Prioritize:
   items that would move VN-Index, USD/VND, or Vietnamese sector sentiment.
4. For each selected item, write a JSON object:
   ```json
   {
     "date": "2026-08-11",
     "time": "07:01",
     "category": "vn-macro",
     "impact": 2,
     "title": "...",
     "stats": [["Nhãn ngắn", "Giá trị", "up|down|dim"]],
     "bullets": ["...", "..."],
     "vnImpact": "1 đoạn giải thích kênh truyền dẫn tới VN...",
     "tags": ["...", "..."],
     "source": "Tên nguồn",
     "sourceUrl": "https://..."
   }
   ```
   - `time`: 24h ICT, from `publishedAt` (convert from the feed's UTC
     timestamp — ICT = UTC+7). Omit (`null`) if not meaningful.
   - `impact`: 1 (minor) to 3 (major, e.g. FOMC decision, VN-Index inflection).
   - `stats`: **optional**, only if the raw title/description already states
     2–4 clear numbers (e.g. a rate range, a CPI %, a headcount change). Do
     **not** invent numbers not present in `news-raw.json`'s title/description
     — if the raw item doesn't give you a number, leave `stats` empty (`[]`).
   - `bullets`: summarize/restructure only what's in the raw title +
     description. Do not add outside facts or figures you're recalling from
     training data — if you know more context, it can go in `vnImpact` as
     *reasoning* about mechanism (e.g. "Fed policy → US yields → DXY → USD/VND"),
     never as a new specific number you can't attribute to the raw item.
   - `vnImpact`: this is the one field where synthesis/reasoning is expected
     — connect the dot to Vietnam's market using established, general
     transmission channels (rates/DXY/USD/VND, export demand, risk sentiment).
     Keep it to established mechanisms, not speculative predictions stated as fact.
   - `tags`: 2–3 short labels (Vietnamese, matching the tone of existing tags
     like "Lợi suất TPCP Mỹ giảm", "USD mạnh").
5. Write the final array, sorted newest-first, to `public/data/news.json`:
   ```json
   {"generatedAtIct": "2026-08-11T16:10:00+07:00", "items": [ ... ]}
   ```
6. If `news-raw.json` is missing, empty, or unreadable: leave `news.json`
   untouched and say so in your final reply — same anti-fabrication rule as
   Task 1, do not synthesize cards from memory/training data.

## Output

After writing the files, reply with one short line covering both tasks:
`OK asof=YYYY-MM-DD fields=... news=N items` or `FAIL reason=...` (partial
success is fine — e.g. grok-fill written but news skipped because
news-raw.json was missing; say so explicitly).
