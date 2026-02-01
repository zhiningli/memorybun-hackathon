# State Transitions: Audio & Screenshot → Redis

This document describes how audio transcription and screenshot states transition until they reach Redis for grading.

## Overview

Two independent streams merge into a single Redis queue:
1. **Audio Transcription**: Processes chunks → Finalizes → Updates Redis
2. **Screenshot Upload**: Stores file → Updates Redis
3. **Redis**: Both ready → Enqueue to `grading:queue`

---

## 1. Audio Transcription State Flow

### Session States

```
┌─────────┐
│  NONE   │
└────┬────┘
     │ POST /session
     ▼
┌─────────┐
│ ACTIVE  │ ← Receiving/processing chunks
└────┬────┘
     │
     │ POST /finalize
     ▼
┌──────────┐
│COMPLETED │ ← Transcription ready
└────┬─────┘
     │
     │ Updates Redis: transcription_status = "completed"
     ▼
   Redis
```

### Chunk Processing

```
┌─────────┐
│ PENDING │ ← Enqueued
└────┬────┘
     │ Worker picks up
     ▼
┌─────────────┐
│ PROCESSING  │ ← Whisper transcribing
└────┬────────┘
     │
     │ Success
     ▼
┌──────────┐
│COMPLETED │ ← Text stored in session
└──────────┘
```

### Flow to Redis

1. **Upload Chunks** → Process with Whisper → Store text in memory
2. **Finalize Session** → `POST /session/{id}/finalize`
3. **Update Redis**:
   - Key: `session:{session_id}`
   - Field: `transcription_text` = full text
   - Field: `transcription_status` = `"completed"`
4. **Check Readiness** → If screenshot ready, enqueue to `grading:queue`

---

## 2. Screenshot State Flow

### Screenshot Processing

```
┌─────────┐
│  NONE   │
└────┬────┘
     │ POST /screenshot
     ▼
┌──────────────┐
│   STORED     │ ← Saved to filesystem
│   URL READY  │    URL: /api/v1/transcribe/screenshots/{id}.{ext}
└──────┬───────┘
       │
       │ Updates Redis: screenshot_status = "completed"
       ▼
     Redis
```

### Flow to Redis

1. **Upload Screenshot** → `POST /session/{id}/screenshot`
2. **Store File** → `backend/data/screenshots/{session_id}.{ext}`
3. **Update Redis**:
   - Key: `session:{session_id}`
   - Field: `screenshot_key` = Filename/key string
   - Field: `screenshot_status` = `"completed"`
4. **Check Readiness** → If transcription ready, enqueue to `grading:queue`

---

## 3. Grading Readiness in Redis

### Redis Session State

**Key**: `session:{session_id}` (Hash)

**Fields**:
- `transcription_text`: Full transcribed text
- `transcription_status`: `"pending"` | `"completed"`
- `screenshot_key`: Key/filename of screenshot file
- `screenshot_status`: `"pending"` | `"completed"`
- `student_id`: Student identifier (optional)
- `question_id`: Question identifier (optional)
- `grading_readiness_status`: Current readiness state
- `grading_published`: `"true"` | `"false"`

### Readiness States

```
┌─────────────────────────┐
│ WAITING_FOR_SCREENSHOT  │ ← Transcription ready first
└─────────────────────────┘
           │
           │ Screenshot arrives
           ▼
┌─────────────────────────┐
│ WAITING_FOR_AUDIO       │ ← Screenshot ready first
└─────────────────────────┘
           │
           │ Other component arrives
           ▼
┌─────────────────────────┐
│        READY            │ ← Both ready
└─────────────────────────┘
           │
           │ Atomic enqueue
           ▼
┌─────────────────────────┐
│       ENQUEUED          │ ← Task in grading:queue
└─────────────────────────┘
```

### State Transitions

**When Transcription Finalizes:**
1. Update Redis: `transcription_status = "completed"`
2. Check `screenshot_status`:
   - If `"completed"` → Set `grading_readiness_status = "ready"` → Enqueue
   - If not → Set `grading_readiness_status = "waiting_for_screenshot"`

**When Screenshot Uploads:**
1. Update Redis: `screenshot_status = "completed"`
2. Check `transcription_status`:
   - If `"completed"` → Set `grading_readiness_status = "ready"` → Enqueue
   - If not → Set `grading_readiness_status = "waiting_for_audio"`

**When Both Ready:**
1. Atomic check (Redis pipeline) → Both `"completed"`?
2. Create `GradingTask` (JSON):
   ```json
   {
     "session_id": "sess_abc123xyz",
     "student_id": "student_123",
     "question_id": "q_456",
     "transcription_text": "The student's transcribed answer...",
      "screenshot_key": "sess_abc123xyz.png",
     "created_at": "2025-01-18T14:00:00Z",
     "retry_count": 0,
     "max_retries": 3
   }
   ```
3. Enqueue to `grading:queue` (LPUSH)
4. Update Redis: `grading_published = "true"`, `grading_readiness_status = "enqueued"`

---

## 4. Complete Flow to Redis

```
Frontend
   │
   ├─→ POST /session → Session ACTIVE
   │
   ├─→ POST /chunk (audio) → Process → Store in memory
   │   │
   │   └─→ POST /finalize
   │       │
   │       └─→ Redis: session:{id}
   │           ├─ transcription_text = "..."
   │           └─ transcription_status = "completed"
   │
   └─→ POST /screenshot → Store file → Generate URL
       │
       └─→ Redis: session:{id}
            ├─ screenshot_key = "..."
           └─ screenshot_status = "completed"
   
   ┌─────────────────────────────────────┐
   │         Redis Check                │
   │  Both completed? → Enqueue task   │
   └─────────────────────────────────────┘
                    │
                    ▼
            ┌───────────────┐
            │ grading:queue │ ← Task ready for LLM
            └───────────────┘
```

---

## 5. Redis Data Structures

### Session State Hash
- **Key**: `session:{session_id}`
- **Type**: Hash
- **TTL**: 3600 seconds (1 hour)

### Grading Queue
- **Key**: `grading:queue`
- **Type**: List (FIFO)
- **Value**: JSON-serialized `GradingTask`
- **Operations**: 
  - Enqueue: `LPUSH` (add to left)
  - Dequeue: `BRPOP` (block from right)

---

## Key Points

1. **Audio** and **Screenshot** are independent - either can arrive first
2. Both update **Redis session state** when ready
3. **Grading publisher** checks if both ready and enqueues atomically
4. **Redis** is the coordination point between transcription and grading services
5. Tasks persist in `grading:queue` until grading service processes them
