# Automation — data pipeline ops guide

This folder is the single source of truth for how `public/data/live.json` gets
filled in every day. It replaces the four separate runbooks that used to live
under `docs/` (`AGENT-AUTO.md`, `FULL-AUTO-SETUP.md`, `PROMPT-GROK-DAILY.md`,
`FIX-PAGES-404.md`) — the content below is their consolidated, updated version.

## Two pipelines, one clear role split

| | **GitHub Actions** (`.github/workflows/data-update.yml`) | **Local agent** (`run_agent_daily.ps1`) |
|--|--|--|
| Role | **Primary — system of record** | Manual / backup only |
| Runs where | GitHub cloud, on a schedule | Your PC, via Windows Task Scheduler |
| Writes to `main` | **Directly** (auto-commit) | **Never** — pushes a branch and opens a PR |
| Grok source | xAI API (`XAI_API_KEY` secret, paid) | Local `grok` CLI (Grok Build subscription) |
| When to use | Always on, no setup after secrets are added | Run manually when Actions data looks stale, or as an extra source for margin/breadth/yields fields the free APIs can't supply |

This split exists because both scripts used to push straight to `main` and
would occasionally race each other (see `git log` history mixing "data: daily
market snapshot (auto)" and "data: agent daily market snapshot" commits). The
local agent no longer pushes directly — it commits to `agent/data-YYYY-MM-DD`
and opens a pull request (via `gh pr create` if the GitHub CLI is installed,
otherwise it prints a compare URL) so a bad or stale local run can't silently
overwrite the Actions pipeline.

## What `daily_update.py` does

`automation/daily_update.py` (stdlib-only Python 3, no dependencies to install):

1. **Free, no-key sources (always run):**
   - US Treasury daily yield curve (CSV)
   - VN-Index price via Yahoo Finance (`^VNINDEX.VN`, falls back to other symbols)
   - DXY (US Dollar Index) via Yahoo Finance
   - CNN Fear & Greed Index
2. **Optional xAI Grok API fill** — only if `XAI_API_KEY` is set — for fields the
   free sources can't provide: `margin`, `vnYields`, `breadth`, `usdVnd`, `foreign`.
3. **Merge `public/data/grok-fill.json`** — a human- or agent-edited file (see
   below) — into whatever the API calls produced.
4. **Writes `public/data/live.json`** (the file the React app fetches at
   runtime) and `public/data/last-run.json` (a small ok/asof/quality summary).

Run it locally:

```powershell
cd C:\Users\shimo\Downloads\vn-market-site
py automation/daily_update.py            # free APIs + Grok API if XAI_API_KEY is set
py automation/daily_update.py --no-grok  # free APIs only, skip the xAI API call
py automation/apply_grok_fill.py         # merge public/data/grok-fill.json only, no network fetch
```

## Merge policy (why a field says "live" vs "proxy")

| Field | If the free API already marked it `live` | Otherwise |
|--|--|--|
| `usYields`, `vnIndex`, `dxy`, `fgUs` | **Never overwritten** by Grok | Grok fills it in, `quality=proxy` |
| `margin`, `vnYields`, `breadth`, `usdVnd`, `foreign` | *(no free API exists for these)* | Grok fills it in, `quality=proxy` |

The dashboard UI reflects this directly — panels are labeled **Mẫu** (sample) /
**Proxy** / **Nội suy** (interpolated) so numbers are never presented as an
official live feed.

## Filling in `grok-fill.json` by hand

When you don't want to run the local agent, you can paste a prompt into any
Grok/LLM chat session and save the JSON it returns to `public/data/grok-fill.json`:

1. Ask for the latest HOSE session's VN-Index, breadth, margin debt, USD/VND
   central rate, VN government bond yields, and foreign net buy/sell — sourced,
   not invented — matching the schema in `public/data/grok-fill.example.json`.
   Require `quality` values of `proxy|live|stale|missing` only, and instruct it
   not to overwrite fields already `live` from the API context.
2. Save the returned JSON as `public/data/grok-fill.json`.
3. Run `py automation/daily_update.py` (merges it with fresh API data) or
   `py automation/apply_grok_fill.py` (merge-only, no network calls).
4. Commit and push (or let the local agent script do steps 3–4 via a PR).

## Local agent setup (Windows Task Scheduler)

Prerequisites: `grok` CLI installed and logged in, `git` credentials configured,
Python on PATH, optionally `gh` (GitHub CLI) authenticated for auto-PR creation.

```powershell
powershell -ExecutionPolicy Bypass -File automation\run_agent_daily.ps1
```

Then create two Task Scheduler triggers (08:20 and 16:10 ICT):

| Field | Value |
|-------|-------|
| Program | `powershell.exe` |
| Arguments | `-ExecutionPolicy Bypass -File "C:\Users\shimo\Downloads\vn-market-site\automation\run_agent_daily.ps1"` |
| Start in | `C:\Users\shimo\Downloads\vn-market-site` |

The script logs to `automation/agent-daily.log` (gitignored) and the last Grok
CLI run's output to `automation/agent-last-run.txt` (also gitignored, and now
written as UTF-8 — earlier versions wrote UTF-16 via `Tee-Object`'s default
encoding, which made the log unreadable as plain text).

## Enabling the GitHub Actions xAI fill (optional)

1. Get an API key at https://console.x.ai/.
2. Repo → **Settings → Secrets and variables → Actions** → New repository
   secret → `XAI_API_KEY`. Optionally add a repo variable `XAI_MODEL`
   (default `grok-3-latest`).
3. **Settings → Actions → General → Workflow permissions** → **Read and write**.
4. **Actions → Daily market data update → Run workflow** to test.

Without a key, the Actions pipeline still auto-updates US yields, VN-Index,
DXY, and US Fear & Greed — everything else stays at its last known value
(sample/proxy) until filled via the local agent or a manual `grok-fill.json`.

## Deploy pipeline

`.github/workflows/deploy.yml` builds the Vite app (`npm ci && npm run build`)
and publishes `dist/` to the `gh-pages` branch via `peaceiris/actions-gh-pages`
(`force_orphan: true`, so history on that branch is squashed on every deploy).
It's triggered on every push to `main`, so a data-only commit from
`data-update.yml` automatically triggers a fresh rebuild+republish.

GitHub Pages must be configured once as **Settings → Pages → Source: Deploy
from a branch → `gh-pages` / `/(root)`**. Keeping data-fetch and
deploy as two separate workflows (rather than one Jekyll-processed `main`
branch deploy) avoids a prior incident where a Jekyll auto-deploy and the
Actions deploy raced each other and produced an intermittent 404 — if you ever
see that again, double check Pages isn't also set to deploy from `main`.
