# ============================================
# MemoryBun - Authenticate EC2 Docker to ECR
# ============================================
# This script SSHs into EC2 and authenticates Docker to ECR
# so you can pull images from your private ECR registry.
#
# Prerequisites:
#   - EC2 instance must have IAM role with ECR permissions
#   - AWS CLI must be installed on EC2
#   - Docker must be installed on EC2
#
# Usage: 
#   .\scripts\ec2-auth-ecr.ps1
# ============================================

param(
    [string]$KeyPath = "$env:USERPROFILE\.ssh\memorybun-ec2.pem",
    [string]$EC2Host = "13.51.230.228",
    [string]$EC2User = "ubuntu"
)

# Configuration
$AWS_ACCOUNT_ID = "093827726637"
$AWS_REGION = "eu-north-1"
$ECR = "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
$EC2_CONNECTION = "${EC2User}@${EC2Host}"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  MemoryBun EC2 ECR Authentication" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Check if key file exists
if (-not (Test-Path $KeyPath)) {
    Write-Host "ERROR: SSH key not found at: $KeyPath" -ForegroundColor Red
    Write-Host "`nPlease ensure your .pem file is at:" -ForegroundColor Yellow
    Write-Host "  $KeyPath" -ForegroundColor White
    exit 1
}

Write-Host "EC2 Host: $EC2Host" -ForegroundColor Gray
Write-Host "ECR Registry: $ECR" -ForegroundColor Gray
Write-Host ""

# SSH command to authenticate Docker to ECR
$authCommand = "aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR"

Write-Host "[1/1] Authenticating Docker to ECR on EC2..." -ForegroundColor Yellow
ssh -i $KeyPath $EC2_CONNECTION $authCommand

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n========================================" -ForegroundColor Green
    Write-Host "  ECR Authentication Successful!" -ForegroundColor Green
    Write-Host "========================================`n" -ForegroundColor Green
    
    Write-Host "You can now pull images on EC2:" -ForegroundColor Cyan
    Write-Host "  docker pull $ECR/memorybun/frontend:latest" -ForegroundColor White
    Write-Host "  docker pull $ECR/memorybun/question-service:latest" -ForegroundColor White
    Write-Host "  docker pull $ECR/memorybun/transcription-service:latest" -ForegroundColor White
    Write-Host "  docker pull $ECR/memorybun/grading-service:latest" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host "`nERROR: ECR authentication failed." -ForegroundColor Red
    Write-Host "Check that your EC2 instance has an IAM role with ECR permissions." -ForegroundColor Yellow
    exit 1
}
