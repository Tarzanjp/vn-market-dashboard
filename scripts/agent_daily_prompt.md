# Agent task: daily market fill for vn-market-site

Working directory MUST be: `C:\Users\shimo\Downloads\vn-market-site` (or the repo root that contains `data/` and `scripts/`).

## Goal

Produce and write `data/grok-fill.json` with the latest public Vietnam market session data for the non-profit dashboard. Do not invent numbers. Prefer official or widely cited public sources.

## Steps

1. Determine the latest HOSE trading session date (ICT). Use tools (web_search / open_page) if needed.
2. Collect what you can reliably find for that session:
   - VN-Index close, change, %
   - HOSE breadth if available (advancers/decliners/unchanged/ceiling/floor, turnover tỷ VND)
   - Margin debt total if publicly reported (daily or weekly — set freq)
   - USD/VND central rate if available
   - VN government bond yields if available
   - Foreign net buy/sell if available
3. Write file `data/grok-fill.json` as a pure JSON object (UTF-8), following the schema in `data/grok-fill.example.json` and `docs/PROMPT-GROK-DAILY.md`.
4. Set `quality.*` to `proxy` for Grok-sourced fields. Omit fields you cannot verify.
5. Put source names/URLs in `sourceNotes`.
6. Do NOT run git push unless the user/script asks; writing `grok-fill.json` is enough for the wrapper script.

## Output

After writing the file, reply with one short line: `OK asof=YYYY-MM-DD fields=...` or `FAIL reason=...`.
