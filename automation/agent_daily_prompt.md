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

## Output

After writing the file, reply with one short line: `OK asof=YYYY-MM-DD fields=...` or `FAIL reason=...`.
