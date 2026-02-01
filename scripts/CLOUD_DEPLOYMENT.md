# MemoryBun Cloud Deployment Guide

This guide covers deploying MemoryBun to AWS (ECR + EC2).

## Architecture Overview

```
Local Machine                    AWS Cloud
┌─────────────────┐             ┌─────────────────────────────────────┐
│                 │   push      │  ECR (Elastic Container Registry)   │
│  Docker Images  │ ─────────►  │  - memorybun/frontend               │
│                 │             │  - memorybun/question-service       │
└─────────────────┘             │  - memorybun/transcription-service  │
                                │  - memorybun/grading-service        │
                                └───────────────┬─────────────────────┘
                                                │ pull
                                                ▼
                                ┌─────────────────────────────────────┐
                                │  EC2 Instance (13.51.230.228)       │
                                │  - Docker Compose                   │
                                │  - Redis                            │
                                │  - All MemoryBun services           │
                                └─────────────────────────────────────┘
```

## Prerequisites

### Local Machine
- Docker Desktop installed
- AWS CLI configured (`aws configure`)
- SSH key for EC2 at `~/.ssh/memorybun-ec2.pem`

### EC2 Instance
- IAM Role attached with `AmazonEC2ContainerRegistryReadOnly` or `AmazonEC2ContainerRegistryFullAccess`
- Docker and Docker Compose installed
- AWS CLI installed

## Configuration

| Setting | Value |
|---------|-------|
| AWS Account ID | `093827726637` |
| AWS Region | `eu-north-1` |
| ECR Registry | `093827726637.dkr.ecr.eu-north-1.amazonaws.com` |
| EC2 IP | `13.51.230.228` |
| EC2 User | `ubuntu` |
| SSH Key | `~/.ssh/memorybun-ec2.pem` |

## Quick Commands

### Full Deployment (Build → Push → Deploy)

```powershell
# Step 1: Build and push to ECR (from local)
.\scripts\deploy-to-ecr.ps1

# Step 2: Deploy to EC2 (pull and restart)
.\scripts\ec2-deploy.ps1
```

### Deploy Single Service

```powershell
# Build and push only question-service
docker-compose build question-service
.\scripts\deploy-to-ecr.ps1 -SkipBuild

# Deploy only question-service on EC2
.\scripts\ec2-deploy.ps1 -Service question-service
```

## Available Scripts

| Script | Description |
|--------|-------------|
| `deploy-to-ecr.ps1` | Build Docker images and push to ECR |
| `ec2-connect.ps1` | SSH into EC2 instance |
| `ec2-auth-ecr.ps1` | Authenticate EC2 Docker to ECR |
| `ec2-deploy.ps1` | Pull images from ECR and restart services on EC2 |

## Step-by-Step Deployment

### 1. Build and Push to ECR (Local Machine)

```powershell
# Authenticate local Docker to ECR
aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin 093827726637.dkr.ecr.eu-north-1.amazonaws.com

# Build all images
docker-compose build

# Tag and push (or use the script)
.\scripts\deploy-to-ecr.ps1
```

### 2. SSH into EC2

```powershell
# Using the script
.\scripts\ec2-connect.ps1

# Or manually
ssh -i ~/.ssh/memorybun-ec2.pem ubuntu@13.51.230.228
```

### 3. Authenticate EC2 Docker to ECR

```powershell
# Using the script (from local)
.\scripts\ec2-auth-ecr.ps1

# Or manually on EC2
aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin 093827726637.dkr.ecr.eu-north-1.amazonaws.com
```

### 4. Pull and Restart Services (On EC2)

```bash
# Navigate to project directory
cd ~/memorybun

# Pull latest images
docker-compose pull

# Restart services
docker-compose up -d

# Check status
docker ps
docker-compose logs -f
```

## Troubleshooting

### SSH Connection Timeout
1. Check EC2 Security Group allows port 22 from your IP
2. Verify EC2 instance is running
3. Check if your IP changed (update Security Group)

### ECR Authentication Failed
1. Ensure EC2 has IAM role with ECR permissions
2. Check AWS CLI is configured on EC2
3. Verify region is correct (eu-north-1)

### Images Not Pulling
1. Re-authenticate Docker to ECR (tokens expire after 12 hours)
2. Check ECR repository names match
3. Verify images were pushed successfully

### Service Not Starting
```bash
# Check logs
docker-compose logs <service-name>

# Check container status
docker ps -a

# Restart specific service
docker-compose restart <service-name>
```

## ECR Repositories

| Service | ECR Repository |
|---------|----------------|
| Frontend | `093827726637.dkr.ecr.eu-north-1.amazonaws.com/memorybun/frontend` |
| Question Service | `093827726637.dkr.ecr.eu-north-1.amazonaws.com/memorybun/question-service` |
| Transcription Service | `093827726637.dkr.ecr.eu-north-1.amazonaws.com/memorybun/transcription-service` |
| Grading Service | `093827726637.dkr.ecr.eu-north-1.amazonaws.com/memorybun/grading-service` |

## IAM Role Setup (If Not Already Done)

1. Go to **IAM Console** → **Roles** → **Create Role**
2. Select **AWS Service** → **EC2**
3. Add permission: `AmazonEC2ContainerRegistryFullAccess`
4. Name: `EC2-ECR-Access`
5. Go to **EC2 Console** → Select your instance
6. **Actions** → **Security** → **Modify IAM Role**
7. Select `EC2-ECR-Access` and save

## Security Notes

- Never commit `.pem` files to git
- ECR authentication tokens expire after 12 hours
- Keep Security Group SSH access restricted to your IP
- Consider using Elastic IP to prevent IP changes on EC2 restart
