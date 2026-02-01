# ============================================
# MemoryBun - Full EC2 Deployment Script
# ============================================
# This script pulls the latest images from ECR and restarts services on EC2.
#
# Usage: 
#   .\scripts\ec2-deploy.ps1              # Pull all and restart
#   .\scripts\ec2-deploy.ps1 -Service frontend  # Deploy single service
# ============================================

param(
    [string]$Service = "",
    [string]$KeyPath = "C:\Users\lxyas\Downloads\MemoryBun\memorybun-key.pem",
    [string]$EC2Host = "13.51.230.228",
    [string]$EC2User = "ec2-user"
)

# Configuration
$AWS_ACCOUNT_ID = "093827726637"
$AWS_REGION = "eu-north-1"
$ECR = "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
$EC2_CONNECTION = "${EC2User}@${EC2Host}"
$REMOTE_DIR = "~/memorybun"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  MemoryBun EC2 Deployment" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Check if key file exists
if (-not (Test-Path $KeyPath)) {
    Write-Host "ERROR: SSH key not found at: $KeyPath" -ForegroundColor Red
    exit 1
}

function Run-SSHCommand {
    param([string]$cmd)
    ssh -i $KeyPath $EC2_CONNECTION $cmd
    return $LASTEXITCODE
}

# Step 1: Authenticate Docker to ECR
Write-Host "[1/3] Authenticating Docker to ECR..." -ForegroundColor Yellow
$authCmd = "aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR"
Run-SSHCommand $authCmd | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: ECR authentication failed." -ForegroundColor Red
    exit 1
}
Write-Host "ECR login successful`n" -ForegroundColor Green

# Step 2: Pull images
Write-Host "[2/3] Pulling latest images from ECR..." -ForegroundColor Yellow
if ($Service -ne "") {
    # Pull single service
    $pullCmd = "cd $REMOTE_DIR && docker-compose pull $Service"
    Write-Host "  Pulling $Service..." -ForegroundColor Cyan
} else {
    # Pull all services
    $pullCmd = "cd $REMOTE_DIR && docker-compose pull"
    Write-Host "  Pulling all services..." -ForegroundColor Cyan
}
Run-SSHCommand $pullCmd
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to pull images." -ForegroundColor Red
    exit 1
}
Write-Host "Pull complete`n" -ForegroundColor Green

# Step 3: Restart services
Write-Host "[3/3] Restarting services..." -ForegroundColor Yellow
if ($Service -ne "") {
    $restartCmd = "cd $REMOTE_DIR && docker-compose up -d $Service"
    Write-Host "  Restarting $Service..." -ForegroundColor Cyan
} else {
    $restartCmd = "cd $REMOTE_DIR && docker-compose up -d"
    Write-Host "  Restarting all services..." -ForegroundColor Cyan
}
Run-SSHCommand $restartCmd
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to restart services." -ForegroundColor Red
    exit 1
}

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "  Deployment Complete!" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green

# Show running containers
Write-Host "Checking running containers..." -ForegroundColor Cyan
Run-SSHCommand "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
Write-Host ""
