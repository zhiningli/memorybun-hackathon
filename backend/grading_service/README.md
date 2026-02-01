# Grading Service

LLM-based grading microservice for MemoryBun. Consumes grading tasks from Redis queue and processes student submissions through a pipeline architecture.

## Overview

The Grading Service provides:
- **Multimodal Grading**: Analyzes both student transcription (text) and screenshots (images)
- **Pipeline Architecture**: Modular stages for flexible grading workflows
- **Summary Generation**: Aggregates feedback across multiple sessions
- **Retry & DLQ**: Automatic retry with exponential backoff and dead-letter queue

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          GRADING SERVICE                                │
│                                                                         │
│   Redis Queues                                                          │
│   ├── grading:queue ─→ GradingWorker (2 workers)                       │
│   └── summary:queue ─→ SummaryWorker (1 worker)                        │
│                              │                                          │
│                              ↓                                          │
│   ┌──────────────────────────────────────────────────────────┐          │
│   │                    GRADING PIPELINE                      │          │
│   │                                                          │          │
│   │  TaskDecode → ContextFetch → PromptBuild → LLMGrade     │          │
│   │                    ↓               ↓          ↓          │          │
│   │             (Fetch Rubrics   (Construct   (Gemini 2.5    │          │
│   │              + Answers)       Prompts)     Multimodal)   │          │
│   │                                                          │          │
│   │                          Validate → Persist              │          │
│   └──────────────────────────────────────────────────────────┘          │
│                              │                                          │
│   ┌──────────────────────────────────────────────────────────┐          │
│   │                    SUMMARY PIPELINE                      │          │
│   │                                                          │          │
│   │  ContextFetch → PromptBuild → LLMSummary → Validate     │          │
│   │       ↓              ↓            ↓           ↓          │          │
│   │  (Fetch Session  (Build     (Gemini 1.5  (Validate      │          │
│   │   Results)        Prompt)    Flash)       & Persist)     │          │
│   └──────────────────────────────────────────────────────────┘          │
│                              │                                          │
│   ResultStore (Redis) ← Persisted Results                               │
│          ↓                                                              │
│   API Endpoints (FastAPI)                                               │
└─────────────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
grading_service/
├── api/
│   └── routes.py              # API endpoints (status, queue, DLQ, summary)
├── pipeline/
│   ├── base.py                # PipelineStageBase abstract class
│   ├── orchestrator.py        # Runs stages in sequence
│   ├── task_decode_stage.py   # Decode/validate task JSON
│   ├── context_fetch_stage.py # Fetch rubric/reference answer
│   ├── prompt_build_stage.py  # Build LLM prompts
│   ├── llm_grade_stage.py     # Multimodal LLM grading
│   ├── validate_stage.py      # Validate scores/feedback
│   ├── persist_stage.py       # Save to ResultStore
│   └── summary/               # Summary generation pipeline
│       ├── summary_orchestrator.py
│       ├── summary_context_fetch_stage.py
│       ├── summary_prompt_build_stage.py
│       ├── summary_llm_stage.py
│       ├── summary_validate_stage.py
│       └── summary_persist_stage.py
├── schemas/
│   ├── grading_state.py       # Pipeline state (flows between stages)
│   └── grading_result.py      # Final output model
├── services/
│   ├── grading_worker.py      # Background worker for grading queue
│   ├── summary_worker.py      # Background worker for summary
│   ├── grading_queue.py       # Queue with retry/DLQ support
│   ├── summary_queue.py       # Summary task queue
│   ├── result_store.py        # Store/retrieve results from Redis
│   ├── context_provider.py    # Orchestrates context fetching
│   ├── rubric_provider.py     # Caches rubrics from Question Service
│   ├── redis_client.py        # Redis connection wrapper
│   └── llm_providers/         # LLM provider implementations
│       ├── base.py            # Abstract base class
│       ├── factory.py         # Provider factory
│       └── gemini.py          # Google Gemini implementation
├── middleware/                # Cross-cutting concerns
│   ├── correlation.py         # Correlation ID middleware
│   ├── log_filter.py          # Correlation ID log filter
│   └── rate_limiter.py        # Rate limiting with slowapi
├── config.py                  # Settings (Redis, LLM, service URLs)
└── main.py                    # FastAPI app entry point
```

## Configuration

Configuration is managed via environment variables. See [DEPLOYMENT_VARS.md](../DEPLOYMENT_VARS.md) for full reference.

### LLM Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `MOCK_LLM_RESPONSE` | `True` | If `True`, returns dummy grading without calling LLM |
| `LLM_PROVIDER` | `gemini` | Provider: `gemini`, `openai`, `anthropic` |
| `LLM_MODEL` | `gemini-2.5-flash` | Model for grading (multimodal) |
| `GEMINI_API_KEY` | - | **Required** if using Gemini with real LLM |

### Summary LLM Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `SUMMARY_LLM_PROVIDER` | `gemini` | Provider for summary generation |
| `SUMMARY_LLM_MODEL` | `gemini-2.5-flash` | Model for summaries |

### Service Dependencies

| Variable | Default | Description |
|----------|---------|-------------|
| `QUESTION_SERVICE_URL` | `http://localhost:8000` | URL to fetch rubrics/answers |
| `TRANSCRIPTION_SERVICE_URL` | `http://localhost:8001` | URL for screenshot retrieval |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection string |

## API Endpoints

### Grading Status & Results

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/grading/session/{id}/status` | GET | Poll for grading status |
| `/api/v1/grading/session/{id}/result` | GET | Get full result with breakdown |

### Queue Monitoring

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/queue/metrics` | GET | Queue depth + worker status |
| `/api/v1/debug/queue-status` | GET | Detailed queue info |
| `/api/v1/debug/grade` | POST | Manual grading (bypasses queue) |

### Dead-Letter Queue Admin

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/admin/dlq/tasks` | GET | View failed tasks |
| `/api/v1/admin/dlq/requeue/{id}` | POST | Retry failed task |
| `/api/v1/admin/dlq/clear` | DELETE | Clear DLQ |
| `/api/v1/admin/dlq/metrics` | GET | DLQ monitoring |

### Summary Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/summary` | POST | Request summary generation |
| `/api/v1/summary/{question_id}/status` | GET | Poll summary status |
| `/api/v1/summary/{question_id}/result` | GET | Get summary result |

## Pipeline Features

### Multimodal Grading
The `LLMGradeStage` constructs multimodal prompts for Gemini, including:
- Student answer transcription (text)
- Screenshot image (visual context)
- Rubric criteria and reference answer

### Session Metadata
The pipeline processes session metadata including:
- **Thinking Time**: Time spent before recording
- **Speaking Time**: Duration of student's answer
- **Screenshots**: Visual context from the session

### Retry & DLQ
- **Retry Policy**: Exponential backoff (1s → 2s → 4s), max 3 retries
- **DLQ Key**: `grading:dead-letter`
- **Non-retryable**: Task decode errors go directly to DLQ

### Circuit Breaker

The service implements circuit breakers using `pybreaker` to protect against cascading failures from downstream services.

| Breaker | Target Service | Config |
|---------|----------------|--------|
| `question_service_breaker` | Question Service | `fail_max=3`, `reset_timeout=30s` |
| `transcription_service_breaker` | Transcription Service | `fail_max=3`, `reset_timeout=30s` |

**Protected Calls**:
- `rubric_provider.py` - Rubric fetching
- `context_provider.py` - Answer fetching  
- `context_fetch_stage.py` - Screenshot retrieval

### Rate Limiting

Rate limits are enforced using `slowapi` with Redis backend (fallback to in-memory).

| Endpoint | Rate Limit | Rationale |
|----------|------------|-----------|
| `POST /api/v1/grading/summarize` | 5/min | LLM cost protection |
| `POST /api/v1/debug/grade` | 3/min | Bypasses queue, runs LLM |
| `GET /api/v1/grading/session/*/status` | 60/min | Status polling |
| `GET /api/v1/grading/session/*/result` | 30/min | Result fetching |
| `GET /api/v1/admin/*` | 5-10/min | Admin operations |

### Correlation IDs

All requests are tagged with a correlation ID for distributed tracing:
- **Header**: `X-Correlation-ID` or `X-Request-ID`
- **Log Format**: `%(correlation_id)s` included in all log messages
- **Propagation**: IDs are forwarded to downstream service calls

### Prometheus Metrics

Metrics are exposed at `/metrics` for Prometheus scraping:
- Request latency, count, and size histograms
- Instrumented via `prometheus-fastapi-instrumentator`

## Running

```bash
cd backend/grading_service
pip install -r requirements.txt
python main.py
# Or: uvicorn main:app --host 0.0.0.0 --port 8002 --reload
```

- **Swagger Docs**: http://localhost:8002/docs
- **Health Check**: http://localhost:8002/health (shows Redis + worker status)

## Testing

```bash
cd backend/grading_service
pytest
```

## Health Check Response

```json
{
  "status": "healthy",
  "service": "grading_service",
  "redis": "healthy",
  "grading_worker": "running",
  "grading_worker_count": 2,
  "summary_worker": "running",
  "summary_worker_count": 1
}
```
