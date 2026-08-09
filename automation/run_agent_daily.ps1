# Backup/manual data pipeline using a local Grok CLI agent (not the GitHub Actions XAI_API_KEY path).
# Schedule via Windows Task Scheduler: 08:20 and 16:10 ICT.
# Requires: grok CLI logged in, git credentials, python, and (optionally) GitHub CLI `gh` for auto-PR.
#
# Role split: GitHub Actions (.github/workflows/data-update.yml) is the primary, scheduled
# pipeline and pushes straight to main. This script is a manual/backup tool — it NEVER pushes
# to main directly. It commits to a dated branch and opens a pull request instead, so a stale
# or bad local run can't silently race/overwrite the Actions pipeline.

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$LogDir = Join-Path $Root "automation"
$Log = Join-Path $LogDir "agent-daily.log"
function Write-Log($msg) {
  $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $msg
  Add-Content -Path $Log -Value $line -Encoding utf8
  Write-Host $line
}

Write-Log "=== agent daily start ==="

# 1) Grok agent research → public/data/grok-fill.json
$promptFile = Join-Path $Root "automation\agent_daily_prompt.md"
$grok = Get-Command grok -ErrorAction SilentlyContinue
if (-not $grok) {
  $grokPath = Join-Path $env:USERPROFILE ".grok\bin\grok.exe"
  if (Test-Path $grokPath) { $grok = $grokPath }
}

if ($grok) {
  Write-Log "Running Grok agent..."
  Write-Log "prompt-file: $promptFile"
  # Dùng --prompt-file (đừng kèm -p: -p bắt buộc có giá trị PROMPT)
  $grokExe = if ($grok -is [System.Management.Automation.CommandInfo]) { $grok.Source } else { "$grok" }
  $outFile = Join-Path $LogDir "agent-last-run.txt"
  try {
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & $grokExe --prompt-file $promptFile --yolo --cwd $Root --no-auto-update *>&1 |
      Tee-Object -FilePath $outFile | Out-Null
    # Tee-Object above already wrote UTF-16 by PowerShell default; re-save as UTF-8 so the
    # log is readable by normal tools (this was a real bug in earlier versions of this script).
    if (Test-Path $outFile) {
      $content = Get-Content -Path $outFile -Raw
      Set-Content -Path $outFile -Value $content -Encoding utf8
    }
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prevEap
    if ($code -ne 0) {
      Write-Log "Grok agent exit code: $code (see automation/agent-last-run.txt)"
    } else {
      Write-Log "Grok agent finished OK"
    }
  } catch {
    Write-Log "Grok agent error: $_"
  }
} else {
  Write-Log "WARN: grok CLI not found — skip agent fill (only free APIs)"
}

# 2) Free APIs + merge grok-fill (do NOT call XAI_API_KEY)
Write-Log "Running daily_update.py --no-grok"
try {
  py (Join-Path $Root "automation\daily_update.py") --no-grok
  Write-Log "daily_update OK"
} catch {
  Write-Log "daily_update FAIL: $_"
  exit 1
}

# 3) Commit to a dated branch and open a PR — never push straight to main from a local run.
$today = Get-Date -Format "yyyy-MM-dd"
$branch = "agent/data-$today"
$dataFiles = @(
  "public/data/live.json",
  "public/data/last-run.json",
  "public/data/grok-fill.json",
  "public/data/history",
  "public/data/events.json"
)

Write-Log "Git commit to branch $branch"
$prevEap2 = $ErrorActionPreference
$ErrorActionPreference = "Continue"

git rev-parse --verify $branch *>$null
if ($LASTEXITCODE -eq 0) {
  git checkout $branch *>$null
} else {
  git checkout -b $branch *>$null
}

git add -- $dataFiles
$st = git status --porcelain -- $dataFiles
if ($st) {
  git -c core.safecrlf=false commit -m "data: agent daily market snapshot"
  if ($LASTEXITCODE -ne 0) {
    Write-Log "Git commit failed exit=$LASTEXITCODE"
    git checkout - *>$null
    $ErrorActionPreference = $prevEap2
    exit 1
  }
  git push -u origin $branch
  if ($LASTEXITCODE -ne 0) {
    Write-Log "Git push failed exit=$LASTEXITCODE"
    git checkout - *>$null
    $ErrorActionPreference = $prevEap2
    exit 1
  }
  Write-Log "Pushed branch $branch"

  $ghCmd = Get-Command gh -ErrorAction SilentlyContinue
  if ($ghCmd) {
    gh pr create --title "data: agent daily market snapshot ($today)" `
      --body "Automated data snapshot from the local Grok CLI agent. Review before merging into main." `
      --base main --head $branch 2>&1 | ForEach-Object { Write-Log $_ }
  } else {
    Write-Log "gh CLI not found — open a PR manually: https://github.com/<owner>/<repo>/compare/main...$branch"
  }
} else {
  Write-Log "No data changes to commit"
}

git checkout - *>$null
$ErrorActionPreference = $prevEap2

Write-Log "=== agent daily done ==="
exit 0
