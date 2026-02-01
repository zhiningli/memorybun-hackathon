# PowerShell script to start Transcription Service
# Port: 8001

$ErrorActionPreference = "Stop"
$Port = 8001

# Get the script's directory and service directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$serviceDir = Join-Path (Split-Path -Parent $scriptDir) "transcription_service"

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  Starting Transcription Service (Port $Port)" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

# Cleanup function to kill processes on the port
function Stop-ProcessesOnPort {
    param([int]$TargetPort)
    
    $processes = Get-NetTCPConnection -LocalPort $TargetPort -ErrorAction SilentlyContinue | 
        Select-Object -ExpandProperty OwningProcess -Unique
    
    if ($processes) {
        Write-Host "`nCleaning up existing processes on port $TargetPort..." -ForegroundColor Yellow
        foreach ($procId in $processes) {
            try {
                $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
                if ($proc) {
                    Write-Host "  Stopping: $($proc.ProcessName) (PID: $procId)" -ForegroundColor Yellow
                    Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
                }
            } catch {
                # Process may have already exited
            }
        }
        # Give processes time to fully terminate
        Start-Sleep -Seconds 1
        Write-Host "  Port $TargetPort cleaned up." -ForegroundColor Green
    }
}

# Clean up any existing processes on the port
Stop-ProcessesOnPort -TargetPort $Port

# Check if virtual environment exists
$venvPath = Join-Path $serviceDir "venv"
if (-Not (Test-Path $venvPath)) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    Push-Location $serviceDir
    python -m venv venv
    Pop-Location
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
$activateScript = Join-Path $venvPath "Scripts\Activate.ps1"
. $activateScript

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  Starting Transcription Service (Port $Port)" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

# Cleanup function to kill processes on the port
function Stop-ProcessesOnPort {
    param([int]$TargetPort)
    
    $processes = Get-NetTCPConnection -LocalPort $TargetPort -ErrorAction SilentlyContinue | 
        Select-Object -ExpandProperty OwningProcess -Unique
    
    if ($processes) {
        Write-Host "`nCleaning up existing processes on port $TargetPort..." -ForegroundColor Yellow
        foreach ($procId in $processes) {
            try {
                $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
                if ($proc) {
                    Write-Host "  Stopping: $($proc.ProcessName) (PID: $procId)" -ForegroundColor Yellow
                    Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
                }
            } catch {
                # Process may have already exited
            }
        }
        # Give processes time to fully terminate
        Start-Sleep -Seconds 1
        Write-Host "  Port $TargetPort cleaned up." -ForegroundColor Green
    }
}

# Clean up any existing processes on the port
Stop-ProcessesOnPort -TargetPort $Port

# Install dependencies
Write-Host "`nInstalling dependencies..." -ForegroundColor Yellow
Write-Host "Note: This may take a while due to PyTorch/Whisper dependencies..." -ForegroundColor Yellow
Push-Location $serviceDir
pip install -r requirements.txt --quiet
Pop-Location

# Start the service
Write-Host "`nStarting Transcription Service on port $Port..." -ForegroundColor Green
Write-Host "API Docs: http://localhost:$Port/docs" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop the service gracefully." -ForegroundColor Gray
Write-Host ""

try {
    Push-Location $serviceDir
    uvicorn main:app --host 0.0.0.0 --port $Port --reload --log-level debug
} finally {
    Pop-Location
    Write-Host "`nTranscription Service stopped." -ForegroundColor Yellow
}

