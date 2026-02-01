# Question Service

Content management microservice for MemoryBun. Manages questions, answers, rubrics, and question lists.

## Overview

The Question Service provides the content foundation for the MemoryBun application:

- **Questions**: Practice problems with metadata (difficulty, category, hints)
- **Question Lists**: Curated sets of questions (public or course-specific)
- **Answers**: Reference answers with optional image support
- **Rubrics**: Grading criteria used by the Grading Service

## Architecture

```
question_service/
├── main.py                # FastAPI app (port 8000)
├── config.py              # Settings (data directory)
├── api/
│   ├── dependencies.py    # FastAPI dependencies
│   └── routers/           # API route modules
│       ├── questions.py   # Question endpoints
│       ├── question_lists.py  # List endpoints
│       ├── answers.py     # Answer endpoints
│       └── rubrics.py     # Rubric endpoints
├── services/
│   ├── question_service.py   # Core business logic
│   ├── answer_service.py     # Answer management
│   └── rubric_service.py     # Rubric management
├── schemas/               # Pydantic models
│   ├── question.py
│   ├── answer.py
│   └── rubric.py
├── middleware/            # Cross-cutting concerns
│   ├── correlation.py     # Correlation ID middleware
│   └── log_filter.py      # Correlation ID log filter
└── data/                  # JSON data files (MVP)
    ├── questions.json
    ├── question_lists.json
    ├── question_list_items.json
    ├── rubrics.json
    ├── answers.json
    └── blob/              # Static assets (images)
```

## Data Persistence

For the current MVP, data is loaded from JSON files in `data/`:

| File | Description |
|------|-------------|
| `questions.json` | All question definitions |
| `question_lists.json` | List metadata |
| `question_list_items.json` | Question-to-list mappings |
| `rubrics.json` | Grading rubrics by category |
| `answers.json` | Reference answers |

## Static Assets

Images (questions, hints, answers) are served from `data/blob/` via the `/blob` endpoint:

```
GET http://localhost:8000/blob/question_image_123.jpg
GET http://localhost:8000/blob/answer_graph_456.png
```

## API Endpoints

All API endpoints are prefixed with `/api/v1`.

### Questions & Lists

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/question-lists/` | GET | Get all question lists |
| `/question-lists/{id}/questions` | GET | Get questions in a list |
| `/questions/{id}` | GET | Get single question details |

### Answers

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/answers/` | GET | Get answers (supports `question_id` filter) |

### Rubrics

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/rubrics/` | GET | Get rubrics (supports `category` filter) |

### System

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health check |
| `/` | GET | Root info |

### Admin API (Protected)

The Admin API provides CRUD operations for managing content. All endpoints require the `X-API-Key` header with the configured admin key.

**Authentication:**
```bash
# Include in all admin requests
-H "X-API-Key: your-admin-api-key"
```

#### Questions

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/admin/questions` | POST | Create a new question |
| `/api/v1/admin/questions/{id}` | PUT | Update an existing question |
| `/api/v1/admin/questions/{id}` | DELETE | Delete a question |

#### Answers

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/admin/answers` | POST | Create a new answer |
| `/api/v1/admin/answers/{id}` | PUT | Update an existing answer |
| `/api/v1/admin/answers/{id}` | DELETE | Delete an answer |

#### Rubrics

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/admin/rubrics` | POST | Create a new rubric |
| `/api/v1/admin/rubrics/{id}` | PUT | Update an existing rubric |
| `/api/v1/admin/rubrics/{id}` | DELETE | Delete a rubric |

#### Question Lists

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/admin/question-lists` | POST | Create a new question list with items (aggregate pattern) |
| `/api/v1/admin/question-lists/{id}` | PUT | Update a question list |
| `/api/v1/admin/question-lists/{id}` | DELETE | Delete a question list (cascade deletes items) |

> **Note:** Creating a question list validates that all referenced question IDs exist and that weightage values sum to 1.0.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DATA_DIR` | `data` | Directory containing JSON data files |
| `ADMIN_API_KEY` | `secret` | API key for admin endpoints (change in production!) |

## Running

```bash
cd backend/question_service
pip install -r requirements.txt
python main.py
# Or: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

- **Swagger Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Metrics**: http://localhost:8000/metrics

## Correlation IDs

All requests are tagged with a correlation ID for distributed tracing:
- **Header**: `X-Correlation-ID` or `X-Request-ID`
- **Log Format**: `%(correlation_id)s` included in all log messages

## Prometheus Metrics

Metrics are exposed at `/metrics` for Prometheus scraping:
- Request latency, count, and size histograms
- Instrumented via `prometheus-fastapi-instrumentator`

## Testing

```bash
cd backend/question_service
pytest
```

## Service Dependencies

The Question Service is called by:
- **Grading Service**: Fetches rubrics and reference answers for grading

The Question Service has no external dependencies (no Redis, no other services).
