# Startup script for MemoryBun Backend
# Checks environment variables before starting services

Write-Host "🔍 Verifying Environment Configuration..." -ForegroundColor Cyan

# Run the python check script
python scripts/check_env.py

# Check exit code of the python script
if ($LASTEXITCODE -ne 0) {
    Write-Host "⛔ Startup Aborted due to missing configuration." -ForegroundColor Red
    exit 1
}

Write-Host "🚀 Starting Backend Services..." -ForegroundColor Green
docker-compose up --build
