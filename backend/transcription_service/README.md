# Transcription Service

Audio transcription microservice for MemoryBun using OpenAI Whisper. Supports chunked audio processing, screenshot uploads, and grading queue integration via Redis.

## Overview

The Transcription Service provides:

- **Audio Transcription**: Transcribe audio using OpenAI Whisper models
- **Screenshot Upload**: Store screenshots for multimodal grading
- **Grading Queue Integration**: Automatically enqueue grading tasks when both transcription and screenshot are ready
- **Session State Management**: Track progress via Redis

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   TRANSCRIPTION SERVICE                      │
│                                                              │
│   Frontend                                                   │
│      │                                                       │
│      ├─→ POST /session ─→ Create session                    │
│      ├─→ POST /audio/chunk ─→ Queue for transcription       │
│      ├─→ POST /screenshot ─→ Store + update Redis state     │
│      └─→ POST /audio/finalize ─→ Mark transcription ready   │
│                                                              │
│   ┌──────────────────┐    ┌──────────────────┐              │
│   │TranscriptionQueue│ ──→│TranscriptionWorker│              │
│   │  (In-memory)     │    │  (Whisper Model)  │              │
│   └──────────────────┘    └──────────────────┘              │
│                                   │                          │
│                                   ↓                          │
│   ┌──────────────────────────────────────────┐              │
│   │          GradingPublisher                 │              │
│   │  - Checks Redis session state             │              │
│   │  - If transcription + screenshot ready:   │              │
│   │    → Enqueue to grading:queue             │              │
│   └──────────────────────────────────────────┘              │
│                                   │                          │
│                                   ↓                          │
│                        Redis (grading:queue)                 │
└─────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
transcription_service/
├── main.py                    # FastAPI app (port 8001)
├── config.py                  # Settings (Redis, storage, Whisper)
├── api/
│   ├── routes.py             # Main router (session, debug)
│   ├── audio.py              # Audio chunk endpoints
│   ├── screenshot.py         # Screenshot upload endpoint
│   └── dependencies.py       # FastAPI dependencies
├── services/
│   ├── audio_transcription_service.py  # Core transcription logic
│   ├── transcription_queue.py          # In-memory task queue
│   ├── transcription_worker.py         # Background Whisper worker
│   ├── grading_publisher.py            # Enqueues grading tasks
│   ├── screenshot_service.py           # Screenshot storage
│   ├── redis_client.py                 # Redis connection
│   ├── redis_grading_queue.py          # Grading queue operations
│   └── storage/                         # Storage backends
│       ├── base.py                      # Abstract interface
│       ├── memory.py                    # In-memory storage
│       └── filesystem.py                # File system storage
├── schemas/
│   ├── transcription.py      # Request/response models
│   ├── screenshot.py         # Screenshot models
│   └── grading.py            # Grading task models
├── middleware/                # Cross-cutting concerns
│   ├── correlation.py         # Correlation ID middleware
│   ├── log_filter.py          # Correlation ID log filter
│   └── rate_limiter.py        # Rate limiting with slowapi
├── scripts/
│   └── audio_transcription_script.py  # CLI transcription tool
└── tests/
```

## Configuration

Configuration is managed via environment variables. See [DEPLOYMENT_VARS.md](../DEPLOYMENT_VARS.md).

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection string |
| `STORAGE_TYPE` | `FILESYSTEM` | `FILESYSTEM`, `MEMORY`, or `S3` |
| `WHISPER_PRELOAD_MODEL` | `None` | Pre-load model at startup (`tiny`, `base`, `small`) |

### S3 Storage Configuration (Cloud Deployment)

For cloud deployments, configure S3 storage:

| Variable | Default | Description |
|----------|---------|-------------|
| `STORAGE_TYPE` | - | Set to `S3` to enable S3 storage |
| `S3_BUCKET` | `None` | S3 bucket name (e.g., `memorybun-assets`) |
| `S3_REGION` | `us-east-1` | AWS region |
| `S3_PREFIX` | `screenshots` | Prefix for screenshot keys |
| `S3_AUDIO_PREFIX` | `audio` | Prefix for audio keys |

> See [docs/s3_setup_guide.md](docs/s3_setup_guide.md) for detailed S3 configuration and IAM setup.

## API Endpoints

### Session Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/transcribe/session` | POST | Create new transcription session |
| `/api/v1/transcribe/session/{session_id}` | DELETE | Delete session and free resources |

### Audio Transcription

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/transcribe/session/{session_id}/audio/chunk` | POST | Upload audio chunk |
| `/api/v1/transcribe/session/{session_id}/audio/chunk/{index}/status` | GET | Check chunk status |
| `/api/v1/transcribe/session/audio/{session_id}` | GET | Get transcription result |
| `/api/v1/transcribe/session/audio/{session_id}/finalize` | POST | Finalize transcription |

### Screenshots

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/transcribe/session/{session_id}/screenshot` | POST | Upload screenshot |
| `/api/v1/transcribe/screenshots/{session_id}.{ext}` | GET | Retrieve screenshot |

### Debug & Monitoring

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/transcribe/debug/queue-status` | GET | Queue and worker status |
| `/api/v1/transcribe/device-info` | GET | CPU/GPU info |

## Workflow Example

```bash
# 1. Create session
curl -X POST http://localhost:8001/api/v1/transcribe/session \
  -H "Content-Type: application/json" \
  -d '{"model": "tiny", "question_id": "q_123"}'
# Returns: {"session_id": "sess_abc123", ...}

# 2. Upload audio chunks
curl -X POST http://localhost:8001/api/v1/transcribe/session/sess_abc123/audio/chunk \
  -F "chunk_index=0" \
  -F "audio_file=@chunk0.webm"

# 3. Upload screenshot
curl -X POST http://localhost:8001/api/v1/transcribe/session/sess_abc123/screenshot \
  -F "screenshot=@screenshot.png"

# 4. Finalize transcription
curl -X POST http://localhost:8001/api/v1/transcribe/session/audio/sess_abc123/finalize

# → Grading task is automatically enqueued to Redis
```

## Whisper Models

| Model | Size | Speed | Accuracy | Use Case |
|-------|------|-------|----------|----------|
| `tiny` | ~39 MB | Fastest | Good | Quick testing |
| `base` | ~74 MB | Fast | Better | General purpose |
| `small` | ~244 MB | Medium | Good | Balanced |
| `medium` | ~769 MB | Slow | Very Good | High quality |
| `large` | ~1550 MB | Slowest | Best | Maximum accuracy |

Models with `.en` suffix are English-only but faster.

## Supported Audio Formats

- WebM (Opus/Vorbis) - Chrome MediaRecorder native
- MP3, WAV, M4A, OGG

FFmpeg handles format conversion automatically.

## Rate Limiting

Rate limits are enforced using `slowapi` with Redis backend (fallback to in-memory).

| Endpoint | Rate Limit | Rationale |
|----------|------------|-----------|
| `POST /session` | 20/min | Session creation |
| `POST /session/*/audio/chunk` | 100/min | High frequency during recording |
| `POST /session/*/audio/finalize` | 20/min | Session finalization |
| `POST /session/*/screenshot` | 20/min | Screenshot uploads |
| `GET /session/*/audio/*` | 60/min | Status/result fetching |
| `GET /screenshots/*` | 60/min | Screenshot retrieval |
| `GET /debug/*` | 30/min | Debug monitoring |

## Correlation IDs

All requests are tagged with a correlation ID for distributed tracing:
- **Header**: `X-Correlation-ID` or `X-Request-ID`
- **Log Format**: `%(correlation_id)s` included in all log messages

## Prometheus Metrics

Metrics are exposed at `/metrics` for Prometheus scraping:
- Request latency, count, and size histograms
- Instrumented via `prometheus-fastapi-instrumentator`

## Running

```bash
cd backend/transcription_service
pip install -r requirements.txt
python main.py
# Or: uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

**Prerequisites:**
- **FFmpeg**: Required for audio processing
- **Redis**: Required for session state and grading queue

- **Swagger Docs**: http://localhost:8001/docs
- **Health Check**: http://localhost:8001/health (includes Redis status)

## Testing

```bash
cd backend/transcription_service
pytest
```

## CLI Transcription Script

For batch transcription:

```bash
cd backend/transcription_service
python scripts/audio_transcription_script.py \
  --audio-file-path ./data/recording.webm \
  --model base \
  --chunk-duration 30
```

## Health Check Response

```json
{
  "status": "healthy",
  "service": "transcription_service",
  "redis": "healthy"
}
```

## Related Documentation

- **[STATE_TRANSITIONS.md](STATE_TRANSITIONS.md)** - Session state flow
- **[BLOCKING_ANALYSIS.md](BLOCKING_ANALYSIS.md)** - Blocking I/O analysis
- **[docs/s3_setup_guide.md](docs/s3_setup_guide.md)** - S3 storage configuration
- **[../REDIS_SETUP.md](../REDIS_SETUP.md)** - Redis setup guide
