# MemoryBun Backend

FastAPI microservices backend for MemoryBun - a spaced repetition learning application.

## Quick Start (Docker - Recommended)

The fastest way to get the entire backend running:

```bash
cd backend
docker-compose up --build
```

This starts **all services** with a single command:
- **Question Service**: http://localhost:8000
- **Transcription Service**: http://localhost:8001
- **Grading Service**: http://localhost:8002
- **Redis**: localhost:6379
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3001 (admin/memorybun)

**First build may take 10-15 minutes** (Whisper/PyTorch downloads).  
Subsequent starts are fast: `docker-compose up`

**Useful Commands:**
```bash
# Start in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Rebuild after code changes
docker-compose up --build
```

---

## Architecture

The backend consists of three independent microservices, shared infrastructure, and monitoring stack:

| Service | Port | Description |
|---------|------|-------------|
| **Question Service** | 8000 | Content management - questions, answers, rubrics, question lists |
| **Transcription Service** | 8001 | Audio transcription (Whisper), screenshots, grading task enqueue |
| **Grading Service** | 8002 | LLM-based grading pipeline with orchestrator pattern |
| **Redis** | 6379 | Message queue, session state, result storage |
| **Prometheus** | 9090 | Metrics collection and time-series database |
| **Grafana** | 3001 | Metrics visualization and dashboards |

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Shared Infrastructure                     │
│                                                              │
│  Redis (Docker) - Port 6379                                 │
│  - Grading task queue (grading:queue)                       │
│  - Summary task queue (summary:queue)                       │
│  - Session state (session:{id})                             │
│  - Grading results (grading:result:{session_id})            │
└──────────────────────────┬──────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
┌───────┴────────┐  ┌───────┴────────┐  ┌───────┴────────┐
│ Question      │  │ Transcription  │  │ Grading        │
│ Service       │  │ Service         │  │ Service        │
│ Port 8000     │  │ Port 8001       │  │ Port 8002      │
│               │  │                 │  │                │
│ - Questions   │  │ - Audio         │  │ - Pipeline     │
│ - Answers     │  │   Transcription │  │   Orchestrator │
│ - Rubrics     │←─│ - Screenshots   │  │ - LLM Grading  │
│ - Lists       │  │ - Redis Session │  │ - Summary Gen  │
│ - Static Blob │  │   State         │  │ - Retry/DLQ    │
│               │  │ - Enqueue Tasks │→─│ - Gemini 2.5   │
└───────▲───────┘  └────────┬────────┘  └───────┬────────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
              Context Fetch (HTTP): Rubrics, Answers
                            │
                      /metrics endpoints
                            │
┌───────────────────────────┴───────────────────────────────┐
│                    Monitoring Stack                        │
│                                                            │
│  Prometheus (Port 9090) ────► Grafana (Port 3001)         │
│  - Scrapes /metrics           - Dashboards                │
│  - 60s interval               - Visualizations            │
└────────────────────────────────────────────────────────────┘
```

### Service Communication

1. **Transcription → Redis**: Enqueues grading tasks when transcription + screenshot are both ready
2. **Grading ← Redis**: Workers poll `grading:queue` for new tasks
3. **Grading → Question Service**: Fetches rubrics and reference answers via HTTP
4. **Grading → Transcription Service**: Fetches screenshots for multimodal grading

---

## Manual Setup (Alternative)

If you prefer to run services without Docker, each microservice has its own virtual environment.

### Prerequisites

- **Python 3.8+**
- **Docker** - Required for Redis
- **FFmpeg** - Required for Transcription Service audio processing

### Redis Setup

```powershell
# Start Redis using Docker Compose
cd backend
docker-compose up -d redis

# Verify Redis is running
docker exec -it memorybun-redis redis-cli ping
# Should return: PONG
```

Redis will be available at `localhost:6379`.

### Start All Services

```powershell
cd backend

# 1. Start Redis (required)
docker-compose up -d redis

# 2. Start all services
.\scripts\start_all_services.ps1
```

This starts all three services in separate PowerShell windows.

### Start Individual Services

```powershell
cd backend

# Question Service (port 8000)
.\scripts\start_question_service.ps1

# Transcription Service (port 8001)
.\scripts\start_transcription_service.ps1

# Grading Service (port 8002)
.\scripts\start_grading_service.ps1
```

---

## Project Structure

```
backend/
├── question_service/       # Content management microservice
│   ├── main.py            # FastAPI app (port 8000)
│   ├── api/routers/       # API endpoints (questions, answers, rubrics)
│   ├── services/          # QuestionService, AnswerService, RubricService
│   ├── schemas/           # Pydantic models
│   └── data/              # JSON data files + blob storage
│
├── transcription_service/  # Audio transcription microservice
│   ├── main.py            # FastAPI app (port 8001)
│   ├── api/               # API routes (audio, screenshot)
│   ├── services/          # Transcription, Redis, Storage
│   │   ├── audio_transcription_service.py  # Whisper integration
│   │   ├── grading_publisher.py            # Enqueues grading tasks
│   │   ├── storage/                        # Memory/Filesystem backends
│   │   └── redis_client.py                 # Redis connection
│   └── schemas/           # Request/response models
│
├── grading_service/        # LLM grading microservice
│   ├── main.py            # FastAPI app (port 8002)
│   ├── api/routes.py      # Status, queue, DLQ, summary endpoints
│   ├── pipeline/          # Orchestrator pattern stages
│   │   ├── orchestrator.py         # Runs pipeline stages
│   │   ├── task_decode_stage.py    # Validate task JSON
│   │   ├── context_fetch_stage.py  # Fetch rubric/answers
│   │   ├── prompt_build_stage.py   # Construct LLM prompt
│   │   ├── llm_grade_stage.py      # Multimodal Gemini call
│   │   ├── validate_stage.py       # Score validation
│   │   ├── persist_stage.py        # Save to ResultStore
│   │   └── summary/                # Summary generation pipeline
│   ├── services/          # Workers, queues, LLM providers
│   │   ├── grading_worker.py       # Grading task consumer
│   │   ├── summary_worker.py       # Summary task consumer
│   │   ├── llm_providers/          # Gemini, OpenAI, Anthropic
│   │   └── result_store.py         # Redis result storage
│   └── schemas/           # GradingState, GradingResult
│
├── monitoring/            # Observability stack
│   ├── prometheus.yml     # Prometheus scrape configuration
│   └── grafana/           # Grafana provisioning
│       └── provisioning/  # Auto-provisioned datasources & dashboards
│
├── docker-compose.yml     # All services + Redis + Monitoring
├── scripts/               # PowerShell startup scripts
├── DEPLOYMENT_VARS.md     # Environment variable reference
├── REDIS_SETUP.md         # Redis setup and monitoring
└── requirements.txt       # Shared dependencies
```

---

## Service Documentation

Each microservice has its own detailed README:

- **[question_service/README.md](question_service/README.md)** - Content management APIs
- **[transcription_service/README.md](transcription_service/README.md)** - Audio transcription, screenshots, Redis integration
- **[grading_service/README.md](grading_service/README.md)** - LLM pipeline architecture, API reference

---

## Environment Variables

See **[DEPLOYMENT_VARS.md](DEPLOYMENT_VARS.md)** for complete reference.

### Key Variables

| Variable | Service | Description |
|----------|---------|-------------|
| `REDIS_URL` | All | Redis connection string |
| `GEMINI_API_KEY` | Grading | Google Gemini API key |
| `MOCK_LLM_RESPONSE` | Grading | Use dummy grading (saves credits) |
| `STORAGE_TYPE` | Transcription | `FILESYSTEM`, `MEMORY`, or `S3` |
| `S3_BUCKET` | Transcription | S3 bucket name (for cloud deployments) |
| `WHISPER_PRELOAD_MODEL` | Transcription | Pre-load model at startup |

---

## API Documentation

Once services are running, access interactive API documentation:

| Service | Swagger UI | ReDoc |
|---------|------------|-------|
| Question Service | http://localhost:8000/docs | http://localhost:8000/redoc |
| Transcription Service | http://localhost:8001/docs | http://localhost:8001/redoc |
| Grading Service | http://localhost:8002/docs | http://localhost:8002/redoc |

### Health Checks

Each service exposes a `/health` endpoint:

```bash
curl http://localhost:8000/health  # Question Service
curl http://localhost:8001/health  # Transcription (includes Redis status)
curl http://localhost:8002/health  # Grading (includes Redis + worker status)
```

---

## Monitoring

The backend includes a full observability stack with Prometheus and Grafana.

### Prometheus (Metrics Collection)

- **URL**: http://localhost:9090
- **Scrape Interval**: 60 seconds
- **Targets**: All 3 microservices via `/metrics` endpoint

Each service exposes Prometheus metrics at `/metrics`:
- `http://localhost:8000/metrics` - Question Service
- `http://localhost:8001/metrics` - Transcription Service
- `http://localhost:8002/metrics` - Grading Service

### Grafana (Dashboards)

- **URL**: http://localhost:3001
- **Default Credentials**: `admin` / `memorybun`

Pre-configured dashboards are auto-provisioned on startup via `monitoring/grafana/provisioning/`.

### Key Metrics

| Metric | Description |
|--------|-------------|
| `http_request_duration_seconds` | Request latency histogram |
| `http_requests_total` | Total request count by status code |
| `http_request_size_bytes` | Request payload sizes |
| `http_response_size_bytes` | Response payload sizes |

---

## Testing

Each service has its own test suite:

```powershell
# Question Service tests
cd backend\question_service
.\venv\Scripts\pytest.exe

# Transcription Service tests
cd backend\transcription_service
.\venv\Scripts\pytest.exe

# Grading Service tests
cd backend\grading_service
.\venv\Scripts\pytest.exe
```

---

## Related Documentation

- **[REDIS_SETUP.md](REDIS_SETUP.md)** - Redis setup, data structures, monitoring
- **[DEPLOYMENT_VARS.md](DEPLOYMENT_VARS.md)** - Environment variable reference
- **[USER_SESSION_FLOW.md](USER_SESSION_FLOW.md)** - End-to-end session flow
- **[GRADING_QUEUE_IMPLEMENTATION.md](GRADING_QUEUE_IMPLEMENTATION.md)** - Queue architecture
