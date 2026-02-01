# MemoryBun EC2 Deployment Guide

A comprehensive guide to deploying MemoryBun on AWS EC2 with HTTPS support.

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Part 1: EC2 Instance Setup](#part-1-ec2-instance-setup)
4. [Part 2: Docker & ECR Setup](#part-2-docker--ecr-setup)
5. [Part 3: Domain & HTTPS Setup](#part-3-domain--https-setup)
6. [Part 4: Nginx Configuration](#part-4-nginx-configuration)
7. [Part 5: S3 Integration](#part-5-s3-integration)
8. [Troubleshooting](#troubleshooting)
9. [Quick Reference](#quick-reference)

---

## Overview

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        AWS Cloud                                 │
│  ┌─────────────┐    ┌─────────────────────────────────────────┐ │
│  │    ALB      │    │           EC2 (t3.micro)                │ │
│  │  (HTTPS)    │───▶│  ┌─────────────────────────────────┐    │ │
│  │  Port 443   │    │  │         Docker Compose          │    │ │
│  └─────────────┘    │  │  ┌─────────┐ ┌───────────────┐  │    │ │
│        │            │  │  │Frontend │ │Question Svc   │  │    │ │
│        │            │  │  │ (nginx) │ │  :8000        │  │    │ │
│  ┌─────────────┐    │  │  │ :8080   │ └───────────────┘  │    │ │
│  │ Route 53 /  │    │  │  └─────────┘ ┌───────────────┐  │    │ │
│  │ Namecheap   │    │  │              │Transcription  │  │    │ │
│  │   DNS       │    │  │              │  :8001        │  │    │ │
│  └─────────────┘    │  │              └───────────────┘  │    │ │
│                     │  │  ┌─────────┐ ┌───────────────┐  │    │ │
│  ┌─────────────┐    │  │  │ Redis   │ │Grading Svc    │  │    │ │
│  │    ACM      │    │  │  │ :6379   │ │  :8002        │  │    │ │
│  │ (SSL Cert)  │    │  │  └─────────┘ └───────────────┘  │    │ │
│  └─────────────┘    │  └─────────────────────────────────┘    │ │
│                     └─────────────────────────────────────────┘ │
│  ┌─────────────┐    ┌─────────────┐                            │
│  │    ECR      │    │     S3      │                            │
│  │  (Images)   │    │  (Storage)  │                            │
│  └─────────────┘    └─────────────┘                            │
└─────────────────────────────────────────────────────────────────┘
```

### Services

| Service | Port | Description |
|---------|------|-------------|
| Frontend (Nginx) | 8080 | React app + reverse proxy |
| Question Service | 8000 | Questions, answers, rubrics API |
| Transcription Service | 8001 | Whisper-based audio transcription |
| Grading Service | 8002 | LLM-based answer grading |
| Redis | 6379 | Task queue and caching |

### Cost Estimate (AWS Free Tier)

| Resource | Free Tier | After 12 months |
|----------|-----------|-----------------|
| EC2 t3.micro | 750 hrs/month | ~$8/month |
| ALB | 750 hrs + 15 LCUs | ~$16-20/month |
| ECR | 500 MB storage | Pay per use |
| S3 | 5 GB storage | Pay per use |

---

## Prerequisites

- AWS Account with Free Tier eligibility
- AWS CLI installed and configured
- Docker Desktop installed
- Domain name (purchased from Namecheap, Route 53, etc.)

---

## Part 1: EC2 Instance Setup

### 1.1 Launch EC2 Instance

1. Go to **AWS Console** → **EC2** → **Launch Instance**

2. Configure:
   | Setting | Value |
   |---------|-------|
   | Name | `memorybun` |
   | AMI | Amazon Linux 2023 |
   | Instance type | `t3.micro` (Free Tier) |
   | Key pair | Create new: `memorybun-key.pem` |
   | Network | Allow SSH, HTTP, HTTPS |

3. **Download the key pair** (`memorybun-key.pem`) to a safe location

### 1.2 Configure Security Group

Add these **inbound rules**:

| Type | Port | Source | Description |
|------|------|--------|-------------|
| SSH | 22 | My IP | SSH access |
| HTTP | 80 | 0.0.0.0/0 | HTTP redirect |
| HTTPS | 443 | 0.0.0.0/0 | HTTPS (via ALB) |
| Custom TCP | 8000 | 0.0.0.0/0 | Question API |
| Custom TCP | 8001 | 0.0.0.0/0 | Transcription API |
| Custom TCP | 8002 | 0.0.0.0/0 | Grading API |
| Custom TCP | 8080 | 0.0.0.0/0 | Frontend |

### 1.3 Allocate Elastic IP

1. Go to **EC2** → **Elastic IPs** → **Allocate Elastic IP address**
2. Select the new IP → **Actions** → **Associate Elastic IP address**
3. Select your `memorybun` instance → **Associate**

**Note:** Record your Elastic IP (e.g., `13.51.230.228`)

### 1.4 Create IAM Role for EC2

1. Go to **IAM** → **Roles** → **Create role**
2. Select **AWS service** → **EC2** → **Next**
3. Add policies:
   - `AmazonEC2ContainerRegistryReadOnly` (for ECR access)
   - `AmazonS3FullAccess` (for S3 access, or create custom policy)
4. Name: `memorybun-ec2-role`
5. Create role

6. **Attach to instance:**
   - Go to **EC2** → Select instance → **Actions** → **Security** → **Modify IAM role**
   - Select `memorybun-ec2-role` → **Update**

### 1.5 SSH into EC2

```bash
ssh -i "C:\Users\Zhining\Downloads\memorybun-key.pem" ec2-user@13.51.230.228
```

### 1.6 Install Docker on EC2

```bash
# Update system
sudo yum update -y

# Install Docker
sudo yum install -y docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker ec2-user

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Logout and login again for group changes
exit
```

### 1.7 Create Swap File (Important for t3.micro!)

The t3.micro has only 1GB RAM. Create a swap file to prevent OOM errors:

```bash
# Create 2GB swap file
sudo dd if=/dev/zero of=/swapfile bs=1M count=2048
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Make swap permanent
echo '/swapfile swap swap defaults 0 0' | sudo tee -a /etc/fstab

# Verify
free -h
```

---

## Part 2: Docker & ECR Setup

### 2.1 Create ECR Repositories

On your **local machine**, run:

```bash
# Create repositories for each service
aws ecr create-repository --repository-name memorybun/frontend --region eu-north-1
aws ecr create-repository --repository-name memorybun/question-service --region eu-north-1
aws ecr create-repository --repository-name memorybun/transcription-service --region eu-north-1
aws ecr create-repository --repository-name memorybun/grading-service --region eu-north-1
```

### 2.2 Build and Push Images

Use the deployment script (`scripts/deploy-to-ecr.ps1`):

```powershell
.\scripts\deploy-to-ecr.ps1
```

Or manually:

```bash
# Login to ECR
aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin 093827726637.dkr.ecr.eu-north-1.amazonaws.com

# Build all images
docker-compose build

# Tag and push each image
docker tag memorybun-frontend:latest 093827726637.dkr.ecr.eu-north-1.amazonaws.com/memorybun/frontend:latest
docker push 093827726637.dkr.ecr.eu-north-1.amazonaws.com/memorybun/frontend:latest

# Repeat for other services...
```

### 2.3 Setup on EC2

SSH into EC2 and create the project directory:

```bash
mkdir -p ~/memorybun
cd ~/memorybun
```

Create `docker-compose.yml`:

```bash
nano docker-compose.yml
```

Paste:

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  question-service:
    image: 093827726637.dkr.ecr.eu-north-1.amazonaws.com/memorybun/question-service:latest
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  transcription-service:
    image: 093827726637.dkr.ecr.eu-north-1.amazonaws.com/memorybun/transcription-service:latest
    ports:
      - "8001:8001"
    environment:
      - REDIS_URL=redis://redis:6379/0
      - STORAGE_TYPE=FILESYSTEM
      - WHISPER_PRELOAD_MODEL=base
      - WHISPER_COMPUTE_TYPE=int8
    depends_on:
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  grading-service:
    image: 093827726637.dkr.ecr.eu-north-1.amazonaws.com/memorybun/grading-service:latest
    ports:
      - "8002:8002"
    environment:
      - REDIS_URL=redis://redis:6379/0
      - QUESTION_SERVICE_URL=http://question-service:8000
      - TRANSCRIPTION_SERVICE_URL=http://transcription-service:8001
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - MOCK_LLM_RESPONSE=false
    depends_on:
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8002/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    image: 093827726637.dkr.ecr.eu-north-1.amazonaws.com/memorybun/frontend:latest
    ports:
      - "8080:80"
    depends_on:
      - question-service
      - transcription-service
      - grading-service
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost/"]
      interval: 30s
      timeout: 10s
      retries: 3
```

Create `.env` file:

```bash
nano .env
```

Add:

```
GEMINI_API_KEY=your-gemini-api-key-here
```

### 2.4 Login to ECR and Pull Images

```bash
aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin 093827726637.dkr.ecr.eu-north-1.amazonaws.com

docker-compose pull
```

### 2.5 Start Services

```bash
docker-compose up -d
```

Verify all services are running:

```bash
docker-compose ps
```

---

## Part 3: Domain & HTTPS Setup

### 3.1 Purchase Domain

Purchase a domain from:
- **Namecheap**: ~$10/year for .com
- **Route 53**: ~$12/year for .com
- **DuckDNS**: Free subdomain (limited features)

Example: `memorybun.com`

### 3.2 Request SSL Certificate (ACM)

1. Go to **AWS Console** → **Certificate Manager**
2. Ensure you're in the same region as your EC2 (eu-north-1)
3. Click **Request a certificate** → **Request public certificate**
4. Domain names:
   - `memorybun.com`
   - `*.memorybun.com` (wildcard)
5. Validation method: **DNS validation**
6. Click **Request**

### 3.3 Validate Certificate

1. Click into the pending certificate
2. Copy the **CNAME records**
3. Add them to your domain's DNS settings

For **Namecheap**:
1. Go to **Domain List** → **memorybun.com** → **Manage** → **Advanced DNS**
2. Add CNAME record:
   - Host: `_xxxxxx` (from ACM)
   - Value: `_yyyyyy.acm-validations.aws.` (from ACM)

Wait 5-30 minutes for validation. Status becomes "Issued".

### 3.4 Create Target Group

1. Go to **EC2** → **Target Groups** → **Create target group**
2. Settings:
   | Setting | Value |
   |---------|-------|
   | Target type | Instances |
   | Name | `memorybun-tg` |
   | Protocol | HTTP |
   | Port | 8080 |
   | VPC | (your default VPC) |
   | Health check path | `/` |

3. Register your EC2 instance as a target

### 3.5 Create Application Load Balancer

1. Go to **EC2** → **Load Balancers** → **Create Load Balancer**
2. Choose **Application Load Balancer**
3. Settings:
   | Setting | Value |
   |---------|-------|
   | Name | `memorybun-alb` |
   | Scheme | Internet-facing |
   | IP type | IPv4 |

4. **Network mapping**: Select at least 2 availability zones

5. **Security group**: Create new with rules:
   | Type | Port | Source |
   |------|------|--------|
   | HTTP | 80 | 0.0.0.0/0 |
   | HTTPS | 443 | 0.0.0.0/0 |

6. **Listeners**:
   - HTTPS:443 → Forward to `memorybun-tg`
   - Select your ACM certificate

7. Create the load balancer

### 3.6 Add HTTP to HTTPS Redirect

1. Go to your ALB → **Listeners** tab
2. Add listener:
   - Protocol: HTTP
   - Port: 80
   - Action: Redirect to HTTPS (port 443)

### 3.7 Point Domain to ALB

1. Get your **ALB DNS name** (e.g., `memorybun-alb-xxxxx.eu-north-1.elb.amazonaws.com`)
2. Add DNS records:

For **Namecheap**:
| Type | Host | Value |
|------|------|-------|
| CNAME | www | `memorybun-alb-xxxxx.eu-north-1.elb.amazonaws.com` |

For root domain, you may need an ALIAS record or use Route 53.

### 3.8 Verify HTTPS

Wait for DNS propagation (5-10 minutes), then test:

```
https://www.memorybun.com
```

---

## Part 4: Nginx Configuration

### 4.1 Frontend Nginx Config

The frontend uses Nginx to:
1. Serve the React app
2. Proxy API requests to backend services

**File: `frontend/.nginx.conf`**

```nginx
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    # ===========================================
    # API Proxy Configuration (for Cloud/Docker)
    # ===========================================
    
    # Question Service API
    location /api/v1/questions {
        proxy_pass http://question-service:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect http://question-service:8000/ /;
    }

    location /api/v1/question-lists {
        proxy_pass http://question-service:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect http://question-service:8000/ /;
    }

    location /api/v1/answers {
        proxy_pass http://question-service:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api/v1/rubrics {
        proxy_pass http://question-service:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Transcription Service API
    location /api/v1/transcribe {
        proxy_pass http://transcription-service:8001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        client_max_body_size 50M;
    }

    # Grading Service API
    location /api/v1/grading {
        proxy_pass http://grading-service:8002;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api/v1/summary {
        proxy_pass http://grading-service:8002;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # ===========================================
    # Static Blob Storage (Question Images)
    # ===========================================
    
    # ^~ gives priority over regex locations
    location ^~ /blob/ {
        proxy_pass http://question-service:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # ===========================================
    # Static File Serving
    # ===========================================

    # Handle React Router (SPA routing)
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### 4.2 Frontend API Configuration

Update API base URLs to use relative paths (for nginx proxy):

**`frontend/src/services/api.ts`:**
```typescript
export const API_BASE_URL =
  (import.meta as any).env?.VITE_API_BASE_URL || "";
```

**`frontend/src/services/transcriptionApi.ts`:**
```typescript
export const TRANSCRIPTION_API_BASE_URL =
  (import.meta as any).env?.VITE_TRANSCRIPTION_API_URL || "";
```

**`frontend/src/services/gradingApi.ts`:**
```typescript
export const GRADING_API_BASE_URL =
  (import.meta as any).env?.VITE_GRADING_API_URL || "";
```

### 4.3 Local Development Environment

Create `frontend/.env.development`:
```
VITE_API_BASE_URL=http://localhost:8000
VITE_TRANSCRIPTION_API_URL=http://localhost:8001
VITE_GRADING_API_URL=http://localhost:8002
```

---

## Part 5: S3 Integration

### 5.1 Create S3 Bucket

1. Go to **AWS Console** → **S3** → **Create bucket**
2. Settings:
   - Bucket name: `memorybun-assets`
   - Region: eu-north-1 (same as EC2)
   - Block all public access: Uncheck if you need public URLs
3. Create bucket

### 5.2 Add S3 Permissions to IAM Role

1. Go to **IAM** → **Roles** → `memorybun-ec2-role`
2. **Add permissions** → **Create inline policy**
3. JSON:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::memorybun-assets",
                "arn:aws:s3:::memorybun-assets/*"
            ]
        }
    ]
}
```

### 5.3 Configure Transcription Service for S3

Update `docker-compose.yml` on EC2:

```yaml
transcription-service:
  environment:
    - STORAGE_TYPE=S3
    - AWS_S3_BUCKET=memorybun-assets
    - AWS_REGION=eu-north-1
    # No AWS keys needed - uses IAM role!
```

### 5.4 Restart Services

```bash
docker-compose down
docker-compose up -d
```

---

## Troubleshooting

### Common Issues

#### 1. "502 Bad Gateway"

**Cause:** ALB can't reach EC2.

**Fix:**
1. Check target group health
2. Verify EC2 security group allows port 8080
3. Ensure Docker containers are running

```bash
docker-compose ps
docker-compose up -d
```

#### 2. "Health checks failed" in Target Group

**Cause:** ALB health check can't reach the frontend.

**Fix:**
1. Verify port 8080 is open in EC2 security group
2. Check Docker containers are running
3. Test locally: `curl http://localhost:8080/`

#### 3. "Failed to fetch" API errors

**Cause:** Frontend can't reach backend APIs.

**Fix:**
1. Ensure nginx proxy rules are configured
2. Check API URLs use relative paths (empty base URL)
3. Rebuild and redeploy frontend

#### 4. 307 Redirect errors

**Cause:** FastAPI trailing slash redirects.

**Fix:** Add trailing slashes to API URLs in frontend:
```typescript
fetch(`${API_BASE_URL}/api/v1/question-lists/`)  // Note the trailing /
```

#### 5. Images not loading (404 for /blob/)

**Cause:** Nginx regex location matching before /blob/ prefix.

**Fix:** Use `^~` prefix in nginx:
```nginx
location ^~ /blob/ {
    proxy_pass http://question-service:8000;
    ...
}
```

#### 6. Out of Memory (OOM) errors

**Cause:** t3.micro only has 1GB RAM.

**Fix:** Create a swap file:
```bash
sudo dd if=/dev/zero of=/swapfile bs=1M count=2048
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile swap swap defaults 0 0' | sudo tee -a /etc/fstab
```

#### 7. Microphone not working

**Cause:** Browsers require HTTPS for microphone access.

**Fix:** Set up HTTPS using ALB + ACM (see Part 3).

---

## Quick Reference

### SSH Command

```bash
ssh -i "C:\Users\Zhining\Downloads\memorybun-key.pem" ec2-user@13.51.230.228
```

### Deploy Frontend Updates

```powershell
# Local: Build and push
docker-compose build frontend
docker tag memorybun-frontend:latest 093827726637.dkr.ecr.eu-north-1.amazonaws.com/memorybun/frontend:latest
docker push 093827726637.dkr.ecr.eu-north-1.amazonaws.com/memorybun/frontend:latest

# EC2: Pull and restart
docker-compose pull frontend
docker-compose up -d --force-recreate frontend
```

### Deploy All Services

```powershell
# Local: Use deployment script
.\scripts\deploy-to-ecr.ps1

# EC2: Pull all and restart
docker-compose pull
docker-compose up -d --force-recreate
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f frontend
docker-compose logs -f grading-service
```

### Restart Services

```bash
docker-compose down
docker-compose up -d
```

### Check Service Health

```bash
docker-compose ps

# Test endpoints
curl http://localhost:8080/          # Frontend
curl http://localhost:8000/health    # Question Service
curl http://localhost:8001/health    # Transcription Service
curl http://localhost:8002/health    # Grading Service
```

### URLs

| Environment | URL |
|-------------|-----|
| Production | https://www.memorybun.com |
| Direct EC2 | http://13.51.230.228:8080 |

---

## Appendix: Key Files Modified

### Frontend

| File | Changes |
|------|---------|
| `.nginx.conf` | Added API proxy rules, blob proxy with `^~` |
| `src/services/api.ts` | Changed base URL to empty string |
| `src/services/transcriptionApi.ts` | Changed base URL to empty string |
| `src/services/gradingApi.ts` | Changed base URL to empty string |
| `.env.development` | Added localhost URLs for dev |

### Backend

| File | Changes |
|------|---------|
| `transcription_service/requirements.txt` | Migrated to faster-whisper |
| `transcription_service/Dockerfile` | Removed PyTorch, simplified |
| `transcription_service/services/audio_transcription_service.py` | Migrated to faster-whisper API |
| `transcription_service/config.py` | Added whisper_compute_type setting |

---

*Last updated: January 11, 2026*
