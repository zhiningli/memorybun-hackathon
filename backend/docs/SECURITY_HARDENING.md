# Security Hardening - Implementation Summary

**Date**: 2026-01-11  
**Scope**: Backend Microservices (Question, Transcription, Grading)

---

## Changes Made

### 1. CORS Configuration (All 3 Services)

**Before**: Hardcoded `allow_origins=["*"]` in each service's `main.py`  
**After**: Configurable via `CORS_ORIGINS` environment variable

**Files Changed**:
- `question_service/config.py` - Added `cors_origins: List[str]`
- `transcription_service/config.py` - Added `cors_origins: List[str]`
- `grading_service/config.py` - Added `cors_origins: List[str]`
- `question_service/main.py` - Uses `settings.cors_origins`
- `transcription_service/main.py` - Uses `settings.cors_origins`
- `grading_service/main.py` - Uses `settings.cors_origins`

**Usage in Production**:
```bash
# Set allowed origins (JSON array format)
CORS_ORIGINS='["https://memorybun.com","https://www.memorybun.com"]'
```

---

### 2. Debug Mode Default (All 3 Services)

**Before**: `debug: bool = True` (unsafe default)  
**After**: `debug: bool = False` (secure default)

This ensures production deployments are secure by default. Set `DEBUG=True` only for local development.

---

### 3. Secret Values Protection (SecretStr)

**Before**: API keys stored as plain strings - could be accidentally logged  
**After**: Using Pydantic `SecretStr` - keys are masked in logs and `.repr()`

**Files Changed**:
- `grading_service/config.py`:
  - `gemini_api_key: Optional[SecretStr]`
  - `openai_api_key: Optional[SecretStr]`
- `question_service/config.py`:
  - `admin_api_key: SecretStr`

**Code that accesses secrets** was updated to use `.get_secret_value()`:
- `grading_service/services/llm_providers/gemini.py`
- `question_service/middleware/auth.py`

**Test files** updated to mock `SecretStr`:
- `grading_service/tests/test_services/test_llm_provider.py`
- `question_service/tests/test_api/test_admin_routes.py`

---

### 4. Non-Root Docker User (All 3 Services)

**Before**: Containers ran as `root` user  
**After**: Containers run as `appuser` (UID 1000)

**Changes in Each Dockerfile**:
```dockerfile
# Create non-root user for security
RUN useradd --create-home --shell /bin/bash --uid 1000 appuser

# Copy application code with correct ownership
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser
```

**Files Changed**:
- `question_service/Dockerfile`
- `transcription_service/Dockerfile`
- `grading_service/Dockerfile`

---

### 5. OCI Image Labels

Added standard OCI labels for image metadata:

```dockerfile
LABEL org.opencontainers.image.source="https://github.com/zhiningli/MemoryBun"
LABEL org.opencontainers.image.title="MemoryBun [Service] Service"
LABEL org.opencontainers.image.description="..."
```

---

### 6. Environment Configuration Template

Created `.env.example` file with:
- All configurable environment variables documented
- Security warnings and recommendations
- Instructions for generating secure keys

---

### 7. Enhanced .gitignore

Updated to prevent accidental secret commits:
```gitignore
.env
.env.local
.env.production
.env.*.local
```

---

## Production Deployment Checklist

After these changes, ensure you:

1. **Set environment variables for production**:
   ```bash
   DEBUG=False
   CORS_ORIGINS='["https://yourdomain.com"]'
   ADMIN_API_KEY=<generated-secure-key>
   GEMINI_API_KEY=<your-api-key>
   ```

2. **Use AWS Secrets Manager** for sensitive values instead of environment variables

3. **Enable HTTPS** via ALB/CloudFront with SSL termination

4. **Rebuild Docker images** to apply non-root user changes:
   ```bash
   docker-compose build --no-cache
   ```

---

## Remaining Recommendations

| Item | Priority | Description |
|------|----------|-------------|
| **Request Timeout** | Medium | Add `--timeout-keep-alive` to uvicorn |
| **Rate Limit Headers** | Low | Re-enable `headers_enabled=True` in rate limiter |
| **Content Security Policy** | Medium | Add CSP headers in nginx |
| **Database Migration** | High | Migrate Question Service from JSON to PostgreSQL |
