# Cloud Migration Plan (AWS)

**Target Strategy**: AWS ECS (Elastic Container Service) with Fargate (Serverless Containers).
**Assumptions**: Single instance for Question Service (Baked-in JSON). S3 for Transcription assets.

---

## Architecture Overview

| Service | Port | Description |
|---------|------|-------------|
| **Frontend** | 80 (internal) → 8080 (host) | React SPA served via nginx |
| **Question Service** | 8000 | Questions, answers, rubrics API |
| **Transcription Service** | 8001 | Audio/screenshot processing |
| **Grading Service** | 8002 | LLM-based grading pipeline |
| **Redis** | 6379 | Session storage & task queue |

---

## Phase 1: Preparation (Local)
**Goal**: Get images ready for the cloud.

### Prerequisites
- **AWS CLI**: Install from https://awscli.amazonaws.com/AWSCLIV2.msi
- **Docker Desktop**: Running with Docker Compose v2

### Steps

1.  **Configure AWS CLI** (one-time setup):
    ```powershell
    aws configure
    # Enter: Access Key ID, Secret Access Key, Region (eu-north-1), Output (json)
    ```

2.  **Create ECR Repositories**:
    Go to AWS Console -> ECR (Elastic Container Registry) and create **4** private repositories:
    -   `memorybun/frontend`
    -   `memorybun/question-service`
    -   `memorybun/transcription-service`
    -   `memorybun/grading-service`

3.  **Authenticate Docker to ECR**:
    ```powershell
    aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin 093827726637.dkr.ecr.eu-north-1.amazonaws.com
    ```

4.  **Build all images** (using docker-compose):
    ```powershell
    cd C:\Users\Zhining\source\repos\MemoryBun
    docker-compose build
    ```

5.  **Tag for ECR** (maps local names to ECR repos):
    ```powershell
    $ECR = "093827726637.dkr.ecr.eu-north-1.amazonaws.com"
    
    docker tag memorybun-frontend:latest              $ECR/memorybun/frontend:latest
    docker tag memorybun-question-service:latest      $ECR/memorybun/question-service:latest
    docker tag memorybun-transcription-service:latest $ECR/memorybun/transcription-service:latest
    docker tag memorybun-grading-service:latest       $ECR/memorybun/grading-service:latest
    ```

6.  **Push to ECR**:
    ```powershell
    docker push $ECR/memorybun/frontend:latest
    docker push $ECR/memorybun/question-service:latest
    docker push $ECR/memorybun/transcription-service:latest
    docker push $ECR/memorybun/grading-service:latest
    ```

---

## Phase 2: Infrastructure Setup (AWS Console)
**Goal**: Create the environment to run containers.

1.  **Networking**:
    -   Use the default VPC for simplicity.
    -   Create a Security Group allowing inbound traffic on:
        -   `80` or `8080` (Frontend - public access)
        -   `8000`, `8001`, `8002` (Backend services - internal or ALB)
        -   `6379` (Redis - internal only)

2.  **Redis (ElastiCache or Container)**:
    -   *Easiest*: Create a simple Redis container in your ECS Task (defined below).
    -   *Production*: Create an AWS ElastiCache (Redis) cluster in the VPC.
    -   *Action*: For now, let's assume valid **Redis Container** inside ECS for MVP simplicity (Sidecar pattern).

3.  **IAM Roles**:
    -   Create a **Task Execution Role** (allows ECS to pull images).
    -   Create a **Task Role** (allows containers to talk to S3). Attach `AmazonS3FullAccess` (or scoped policy) to this role.

4.  **S3 Bucket**:
    -   Create bucket: `memorybun-assets`
    -   Enable public read access for screenshots (or use CloudFront for CDN).

---

## Phase 3: Deployment (ECS)
**Goal**: Launch the services.

1.  **Create ECS Cluster**:
    -   Name: `memorybun-cluster` (Fargate).

2.  **Create Task Definition** (The Blueprint):
    -   Create a single Task Definition containing ALL **5** containers (Frontend, Question, Transcription, Grading, Redis) so they can talk via `localhost` (Sidecar pattern).
    -   *Note: If splitting into separate tasks, you need CloudMap/Service Discovery.*
    
    **Container Definitions**:
    | Container | Image | Port | Memory | CPU |
    |-----------|-------|------|--------|-----|
    | frontend | `memorybun/frontend` | 80 | 256 MB | 128 |
    | question-service | `memorybun/question-service` | 8000 | 512 MB | 256 |
    | transcription-service | `memorybun/transcription-service` | 8001 | 2048 MB | 1024 |
    | grading-service | `memorybun/grading-service` | 8002 | 512 MB | 256 |
    | redis | `redis:7-alpine` | 6379 | 256 MB | 128 |

    **Environment Variables** (for backend services):
    -   `STORAGE_TYPE` = `S3`
    -   `S3_BUCKET` = `memorybun-assets`
    -   `REDIS_URL` = `redis://localhost:6379/0` (if running Redis in same task)
    -   `QUESTION_SERVICE_URL` = `http://localhost:8000`
    -   `TRANSCRIPTION_SERVICE_URL` = `http://localhost:8001`
    -   `GEMINI_API_KEY` = [Use AWS Secrets Manager or paste key]
    -   `MOCK_LLM_RESPONSE` = `False`

3.  **Run Service**:
    -   Launch an ECS Service using the Task Definition.
    -   Assign a Public IP (for MVP) or use an Application Load Balancer (production).

4.  **Application Load Balancer (Recommended for Production)**:
    -   Create an ALB with target groups for each service.
    -   Route `/api/questions/*` → Question Service (8000)
    -   Route `/api/transcription/*` → Transcription Service (8001)
    -   Route `/api/grading/*` → Grading Service (8002)
    -   Route `/*` → Frontend (80)

---

## Phase 4: Validation
**Goal**: Verify system health.

1.  **Check Logs**: Go to CloudWatch Logs for the ECS task. Look for "Application startup complete".

2.  **Health Checks**:
    -   Visit `http://[PUBLIC_IP]:80/` or `http://[PUBLIC_IP]/` (Frontend)
    -   Visit `http://[PUBLIC_IP]:8000/health` (Question Service)
    -   Visit `http://[PUBLIC_IP]:8001/health` (Transcription Service)
    -   Visit `http://[PUBLIC_IP]:8002/health` (Grading Service)

3.  **Functional Test**:
    -   Load the frontend in a browser.
    -   Navigate through question list.
    -   Start a practice session and verify audio/screenshot uploads work.
    -   Complete a session and verify grading results appear.

4.  **S3 Verification**: Check that screenshots appear in `memorybun-assets` bucket under the expected prefix.

---

## Summary Checklist
- [ ] AWS CLI installed & configured locally?
- [ ] Docker running?
- [ ] Gemini/OpenAI API Keys ready?
- [ ] ECR repositories created (4 total)?
- [ ] S3 bucket created with correct permissions?
- [ ] IAM roles configured (Task Execution + Task Role)?

---

## Notes

### Frontend Configuration
The frontend is built as a static React app served by nginx. The nginx configuration (`.nginx.conf`) handles:
-   SPA routing (fallback to `index.html`)
-   API proxying to backend services (if configured)

### Resource Requirements
**Minimum Fargate Task Size**: 4 vCPU, 8 GB RAM (to accommodate all 5 containers, especially Whisper model in transcription-service).

### Cost Optimization Tips
1.  Use Fargate Spot for non-production environments.
2.  Consider splitting transcription-service to a separate task (scales independently).
3.  Use ElastiCache Redis for production (more reliable than container Redis).
