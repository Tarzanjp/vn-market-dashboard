# Thông tin thị trường — VN market dashboard

**Live:** https://tarzanjp.github.io/vn-market-dashboard/

A free, non-profit dashboard tracking the Vietnam stock market (breadth,
margin debt, sentiment, VN↔US bond yields), a companion world-markets page
(indices, FX, commodities, crypto via embedded TradingView widgets), and a
historical data + event-correlation page.

## Project layout

```
src/
  dashboard/    Market dashboard page (components + ported chart engine)
  world/        World indices page (components + ported chart engine)
  history/      History & Correlation page (overlay chart + Pearson correlation table)
  components/   Shared layout (header, nav, ticker tape, footer)
  hooks/        useLiveMarketData / useHistory — fetch public/data/*.json
  styles/       Shared design tokens + base layout CSS
  data/         Static instrument list for the world-indices page
public/data/    Data pipeline input/output (live.json, history/, events.json, grok-fill.json, …)
automation/     Data pipeline scripts + ops guide (see automation/README.md)
.github/workflows/
  data-update.yml       Daily data fetch → public/data/live.json + history → commit to main
  deploy.yml            npm run build → publish dist/ to the gh-pages branch
  backfill-history.yml  Manual-only: (re)populate public/data/history/ from free historical sources
```

Three pages — `index.html`, `the-gioi.html`, `lich-su.html` — are each a
separate Vite build entry mounting its own React root, keeping every page URL
stable while sharing components, styles, and data-fetching hooks.

## Local development

```powershell
npm install
npm run dev       # http://localhost:5173
npm run build     # outputs dist/
npm run preview   # serve the production build locally
```

The dev server serves `public/data/live.json` as-is, so you're always looking
at whatever the pipeline last generated (or the committed sample data if
you've never run it locally).

## Data automation

See **[automation/README.md](automation/README.md)** for the full pipeline
guide — what feeds `public/data/live.json`, the GitHub Actions vs. local-agent
role split, the Grok merge policy, and how to fill in fields the free APIs
don't cover.

Quick version: `.github/workflows/data-update.yml` runs on a schedule
(08:15 and 16:00 ICT, weekdays) and is the system of record; it fetches free
sources (US Treasury yields, VN-Index, DXY, CNN Fear & Greed) plus an optional
paid xAI Grok fill for fields with no free API (margin debt, VN bond yields,
breadth, USD/VND, foreign flows). A local Windows agent
(`automation/run_agent_daily.ps1`) is available as a manual backup — it opens
a pull request rather than pushing to `main` directly.

## History & Correlation

The third page (`lich-su.html`) charts real accumulated history — VN-Index,
US/VN bond yields, DXY, margin, USD/VND, rebased to an index-100 overlay so
wildly different units are visually comparable — with sourced macro events
(Fed decisions, CPI/NFP releases, VN-specific news) marked on the timeline,
plus a Pearson correlation table between whichever series are toggled on.
This replaced the old dashboard behavior where "history" charts were actually
a seeded PRNG faking a plausible past around the latest real snapshot.

Not everything is backfillable for free — see
**[automation/README.md](automation/README.md#historical-data--event-correlation-lịch-sử--tương-quan-page)**
for exactly which fields have real multi-year history today (US Treasury
yields, DXY) versus which only start accumulating going forward (VN-Index and
everything Vietnam-specific — there's no free historical API for them).

## Deploying

Pushing to `main` (whether from a normal commit or an automated data update)
triggers `.github/workflows/deploy.yml`, which builds the app and publishes
`dist/` to the `gh-pages` branch. One-time setup: **Settings → Pages →
Source: Deploy from a branch → `gh-pages` / `/(root)`**.

Other free static hosts work too, since the build output is a plain static
site — point Cloudflare Pages or Netlify at `npm run build` with output
directory `dist`.

## Data quality labeling

Every panel that isn't backed by a live feed is explicitly labeled **Mẫu**
(sample), **Proxy**, or **Nội suy** (interpolated) — this is a deliberate
product decision, not a placeholder to remove. Numbers are for reference only
and are never presented as an official real-time feed.
