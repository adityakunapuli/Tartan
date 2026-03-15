# daily_refresh.ps1
$ErrorActionPreference = "Stop"

# Get script directory to ensure we run from the project root
$ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location -Path $ScriptPath

# Log output to a file in logs directory
$LogDir = Join-Path $ScriptPath "logs"
if (!(Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }
$LogFile = Join-Path $LogDir "daily_refresh.log"

Start-Transcript -Path $LogFile -Append

try {
    Write-Host "Starting Daily Refresh..."
    $Date = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "Timestamp: $Date"

    # Activate Virtual Environment
    $VenvPath = Join-Path $ScriptPath ".venv\Scripts\Activate.ps1"
    if (Test-Path $VenvPath) {
        Write-Host "Activating virtual environment..."
        . $VenvPath
    } else {
        Write-Warning "Virtual environment not found at .venv\Scripts\Activate.ps1. Assuming Python is in PATH."
    }

    # 1. Sync Data
    Write-Host "Step 1: Syncing Data (main.py)..."
    python main.py
    if ($LASTEXITCODE -ne 0) { throw "Sync failed with exit code $LASTEXITCODE" }

    # 2. Categorize
    Write-Host "Step 2: Categorizing Transactions..."
    python -m services.llm_categorizer
    if ($LASTEXITCODE -ne 0) { throw "Categorization failed with exit code $LASTEXITCODE" }

    # 3. Report
    Write-Host "Step 3: Generating Report..."
    python -m reports.portfolio_summary
    if ($LASTEXITCODE -ne 0) { throw "Reporting failed with exit code $LASTEXITCODE" }

    Write-Host "Daily Refresh Completed Successfully."
} catch {
    Write-Error "An error occurred: $_"
} finally {
    Stop-Transcript
}