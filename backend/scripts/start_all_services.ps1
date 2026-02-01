# PowerShell script to start all microservices
# Starts each service in a new PowerShell window

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Split-Path -Parent $scriptDir

# Activate backend-level virtual environment if it exists
$backendVenvPath = Join-Path $backendDir "venv"
if (Test-Path $backendVenvPath) {
    Write-Host "Activating backend virtual environment..." -ForegroundColor Yellow
    $activateScript = Join-Path $backendVenvPath "Scripts\Activate.ps1"
    if (Test-Path $activateScript) {
        . $activateScript
    }
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Starting All MemoryBun Microservices" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Cleanup function to kill processes on a port
function Stop-ProcessesOnPort {
    param([int]$TargetPort)
    
    $processes = Get-NetTCPConnection -LocalPort $TargetPort -ErrorAction SilentlyContinue | 
        Select-Object -ExpandProperty OwningProcess -Unique
    
    if ($processes) {
        Write-Host "Cleaning up port $TargetPort..." -ForegroundColor Yellow
        foreach ($procId in $processes) {
            try {
                Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
            } catch {
                # Process may have already exited
            }
        }
        Start-Sleep -Milliseconds 500
    }
}

# Clean up all ports before starting
Write-Host "Cleaning up any existing services..." -ForegroundColor Yellow
Stop-ProcessesOnPort -TargetPort 8000
Stop-ProcessesOnPort -TargetPort 8001
Stop-ProcessesOnPort -TargetPort 8002
Write-Host ""

Write-Host "Services:" -ForegroundColor Yellow
Write-Host "  - Question Service:      http://localhost:8000" -ForegroundColor White
Write-Host "  - Transcription Service: http://localhost:8001" -ForegroundColor White
Write-Host "  - Grading Service:       http://localhost:8002" -ForegroundColor White
Write-Host ""

# Start Question Service in new window
$questionScript = Join-Path $scriptDir "start_question_service.ps1"
Start-Process powershell -ArgumentList "-NoExit", "-File", $questionScript

# Wait a moment before starting next service
Start-Sleep -Seconds 2

# Start Transcription Service in new window
$transcriptionScript = Join-Path $scriptDir "start_transcription_service.ps1"
Start-Process powershell -ArgumentList "-NoExit", "-File", $transcriptionScript

# Wait a moment before starting next service
Start-Sleep -Seconds 2

# Start Grading Service in new window
$gradingScript = Join-Path $scriptDir "start_grading_service.ps1"
Start-Process powershell -ArgumentList "-NoExit", "-File", $gradingScript

Write-Host "All services are starting in separate windows..." -ForegroundColor Green
Write-Host ""
Write-Host "API Documentation:" -ForegroundColor Cyan
Write-Host "  - Question Service:      http://localhost:8000/docs" -ForegroundColor White
Write-Host "  - Transcription Service: http://localhost:8001/docs" -ForegroundColor White
Write-Host "  - Grading Service:       http://localhost:8002/docs" -ForegroundColor White
Write-Host ""
Write-Host "To stop all services, close the PowerShell windows or press Ctrl+C in each." -ForegroundColor Gray

