# daily_refresh.ps1
$ErrorActionPreference = "Stop"

# Always run from the project root (one level up from scripts/)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location -Path $ProjectRoot

# Log output to a file in logs directory
$LogDir = Join-Path $ProjectRoot "logs"
if (!(Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }
$LogFile = Join-Path $LogDir "daily_refresh.log"

Start-Transcript -Path $LogFile -Append

try {
    Write-Host "Starting Daily Refresh..."
    $Date = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "Timestamp: $Date"
    Write-Host "Working Directory: $ProjectRoot"

    # 1. Sync Data
    Write-Host "Step 1: Syncing Data..."
    uv run python -m modules.plaid_integration.sync
    if ($LASTEXITCODE -ne 0) { throw "Sync failed with exit code $LASTEXITCODE" }

    # 2. Categorize
    Write-Host "Step 2: Categorizing Transactions..."
    uv run python -m modules.analytics.categorizer
    if ($LASTEXITCODE -ne 0) { throw "Categorization failed with exit code $LASTEXITCODE" }

    # 3. Report
    Write-Host "Step 3: Generating Report..."
    uv run python -m reports.portfolio_summary
    if ($LASTEXITCODE -ne 0) { throw "Reporting failed with exit code $LASTEXITCODE" }

    Write-Host "Daily Refresh Completed Successfully."
} catch {
    Write-Error "An error occurred: $_"
} finally {
    Stop-Transcript
}