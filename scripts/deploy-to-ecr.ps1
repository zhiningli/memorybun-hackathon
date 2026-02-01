# ============================================
# MemoryBun - Deploy to AWS ECR
# ============================================
# Usage: 
#   .\scripts\deploy-to-ecr.ps1           # Build and push all
#   .\scripts\deploy-to-ecr.ps1 -SkipBuild # Push only (if already built)
# ============================================

param(
    [switch]$SkipBuild
)

# Configuration
$AWS_ACCOUNT_ID = "093827726637"
$AWS_REGION = "eu-north-1"
$ECR = "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

# Service mappings: local image name -> ECR repo name
$services = @{
    "memorybun-frontend"              = "memorybun/frontend"
    "memorybun-question-service"      = "memorybun/question-service"
    "memorybun-transcription-service" = "memorybun/transcription-service"
    "memorybun-grading-service"       = "memorybun/grading-service"
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  MemoryBun ECR Deployment Script" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Step 1: Authenticate Docker to ECR
Write-Host "[1/4] Authenticating Docker to ECR..." -ForegroundColor Yellow
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: ECR login failed. Check your AWS credentials." -ForegroundColor Red
    exit 1
}
Write-Host "ECR login successful`n" -ForegroundColor Green

# Step 2: Build images (optional)
if (-not $SkipBuild) {
    Write-Host "[2/4] Building all images with docker-compose..." -ForegroundColor Yellow
    docker-compose build
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Build failed." -ForegroundColor Red
        exit 1
    }
    Write-Host "Build complete`n" -ForegroundColor Green
} else {
    Write-Host "[2/4] Skipping build (using existing images)`n" -ForegroundColor Gray
}

# Step 3: Tag images for ECR
Write-Host "[3/4] Tagging images for ECR..." -ForegroundColor Yellow
foreach ($local in $services.Keys) {
    $remote = $services[$local]
    Write-Host "  Tagging $local -> $ECR/$remote"
    docker tag "${local}:latest" "$ECR/${remote}:latest"
}
Write-Host "All images tagged`n" -ForegroundColor Green

# Step 4: Push to ECR
Write-Host "[4/4] Pushing images to ECR..." -ForegroundColor Yellow
foreach ($local in $services.Keys) {
    $remote = $services[$local]
    Write-Host "`n  Pushing $remote..." -ForegroundColor Cyan
    docker push "$ECR/${remote}:latest"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to push $remote" -ForegroundColor Red
        exit 1
    }
}

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "  All images pushed to ECR!" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green

# Show pushed images
Write-Host "ECR Repositories:" -ForegroundColor Cyan
foreach ($local in $services.Keys) {
    $remote = $services[$local]
    Write-Host "  - $ECR/$remote:latest"
}
Write-Host ""
