# ============================================
# MemoryBun - EC2 SSH Connection Script
# ============================================
# Usage: 
#   .\scripts\ec2-connect.ps1                    # SSH into EC2
#   .\scripts\ec2-connect.ps1 -Command "ls"      # Run a single command
# ============================================

param(
    [string]$Command = "",
    [string]$KeyPath = "C:\Users\lxyas\Downloads\MemoryBun\memorybun-key.pem",
    [string]$EC2Host = "13.51.230.228",
    [string]$EC2User = "ec2-user"
)

# Configuration
$EC2_CONNECTION = "${EC2User}@${EC2Host}"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  MemoryBun EC2 Connection" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Check if key file exists
if (-not (Test-Path $KeyPath)) {
    Write-Host "ERROR: SSH key not found at: $KeyPath" -ForegroundColor Red
    Write-Host "`nPlease ensure your .pem file is at:" -ForegroundColor Yellow
    Write-Host "  $KeyPath" -ForegroundColor White
    Write-Host "`nOr specify a different path:" -ForegroundColor Yellow
    Write-Host "  .\scripts\ec2-connect.ps1 -KeyPath 'C:\path\to\your-key.pem'" -ForegroundColor White
    exit 1
}

Write-Host "Key file: $KeyPath" -ForegroundColor Gray
Write-Host "Connecting to: $EC2_CONNECTION" -ForegroundColor Gray
Write-Host ""

if ($Command -ne "") {
    # Run single command
    Write-Host "Running command: $Command`n" -ForegroundColor Yellow
    ssh -i $KeyPath $EC2_CONNECTION $Command
} else {
    # Interactive SSH session
    Write-Host "Opening interactive SSH session...`n" -ForegroundColor Yellow
    ssh -i $KeyPath $EC2_CONNECTION
}
