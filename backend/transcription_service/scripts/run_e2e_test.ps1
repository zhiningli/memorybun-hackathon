# PowerShell script to run E2E integration tests
# Usage: 
#   .\scripts\run_e2e_test.ps1 --audio-file-path .\data\test_audio_recording_full.webm
#   .\scripts\run_e2e_test.ps1 --audio-file-path .\data\test.webm --test parallel --screenshot-file-path .\data\screenshot.png

param(
    [Parameter(Mandatory=$true)]
    [string]$AudioFilePath,
    
    [string]$ApiUrl = "http://localhost:8001",
    
    [ValidateSet("grading", "parallel")]
    [string]$Test = "grading",
    
    [string]$ScreenshotFilePath = $null,
    
    [ValidateSet("audio_first", "screenshot_first", "simultaneous", "all")]
    [string]$Scenario = "all",
    
    [switch]$TestScreenshot,
    
    [switch]$NoVerifyRedis
)

# Get script directory (parent of scripts folder)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ServiceDir = Split-Path -Parent $ScriptDir

# Change to service directory
Set-Location $ServiceDir

# Activate virtual environment
if (Test-Path ".\venv\Scripts\Activate.ps1") {
    . .\venv\Scripts\Activate.ps1
} else {
    Write-Host "Error: Virtual environment not found. Please create venv first." -ForegroundColor Red
    exit 1
}

# Build command arguments based on test type
if ($Test -eq "parallel") {
    # Parallel streams test
    $args = @(
        "scripts\test_parallel_streams_e2e.py",
        "--audio-file-path", $AudioFilePath,
        "--api-url", $ApiUrl,
        "--scenario", $Scenario
    )
    
    if ($ScreenshotFilePath) {
        $args += "--screenshot-file-path", $ScreenshotFilePath
    }
    
    if ($NoVerifyRedis) {
        $args += "--no-verify-redis"
    }
} else {
    # Grading integration test (original)
    $args = @(
        "scripts\test_grading_integration_e2e.py",
        "--audio-file-path", $AudioFilePath,
        "--api-url", $ApiUrl
    )
    
    if ($TestScreenshot) {
        $args += "--test-screenshot"
    }
    
    if ($NoVerifyRedis) {
        $args += "--no-verify-redis"
    }
}

# Run the script
Write-Host "Running E2E test: $Test" -ForegroundColor Cyan
Write-Host "Command: python $($args -join ' ')" -ForegroundColor Gray
Write-Host ""
python $args

