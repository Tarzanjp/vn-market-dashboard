# Full daily pipeline with Grok AGENT (not XAI_API_KEY on GitHub)
# Schedule via Windows Task Scheduler: 08:20 and 16:10 ICT
# Requires: grok CLI logged in, git credentials, python

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$LogDir = Join-Path $Root "data"
$Log = Join-Path $LogDir "agent-daily.log"
function Write-Log($msg) {
  $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $msg
  Add-Content -Path $Log -Value $line -Encoding UTF8
  Write-Host $line
}

Write-Log "=== agent daily start ==="

# 1) Grok agent research → data/grok-fill.json
$promptFile = Join-Path $Root "scripts\agent_daily_prompt.md"
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
      Tee-Object -FilePath $outFile
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prevEap
    if ($code -ne 0) {
      Write-Log "Grok agent exit code: $code (see data/agent-last-run.txt)"
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
  py (Join-Path $Root "scripts\daily_update.py") --no-grok
  Write-Log "daily_update OK"
} catch {
  Write-Log "daily_update FAIL: $_"
  exit 1
}

# 3) Commit + push (triggers Pages deploy)
# Native git ghi warning CRLF ra stderr — không coi là fatal với $ErrorActionPreference Stop
Write-Log "Git commit/push"
$prevEap2 = $ErrorActionPreference
$ErrorActionPreference = "Continue"
git add -- data/live.js data/snapshot-latest.json data/last-run.json data/grok-fill.json
$st = git status --porcelain -- data
if ($st) {
  git -c core.safecrlf=false commit -m "data: agent daily market snapshot"
  if ($LASTEXITCODE -ne 0) {
    Write-Log "Git commit failed exit=$LASTEXITCODE"
    $ErrorActionPreference = $prevEap2
    exit 1
  }
  git push origin main
  if ($LASTEXITCODE -ne 0) {
    Write-Log "Git push failed exit=$LASTEXITCODE"
    $ErrorActionPreference = $prevEap2
    exit 1
  }
  Write-Log "Pushed to origin/main"
} else {
  Write-Log "No data changes to commit"
}
$ErrorActionPreference = $prevEap2

Write-Log "=== agent daily done ==="
exit 0
