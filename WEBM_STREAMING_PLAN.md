# WebM Init Segment Streaming - Implementation Plan

## Problem Statement

MediaRecorder generates WebM chunks where **only chunk 0 has a valid EBML header**. Subsequent chunks are continuation data that ffmpeg cannot parse independently.

## Solution: Frontend Init Segment Prepend

Extract the WebM init segment from chunk 0, cache it in memory, and prepend it to chunks 1+ before uploading. **No backend changes required.**

---

## Architecture

```
Frontend                              Backend (NO CHANGES)
────────                              ────────────────────
┌──────────────────────────┐          ┌──────────────────┐
│ MediaRecorder            │          │ transcription-   │
│ ondataavailable          │          │ service          │
└────────┬─────────────────┘          │                  │
         │                            │ Receives valid   │
         ▼                            │ WebM every time  │
Chunk 0 ─┬─► Extract init segment     │                  │
         │   Cache in memory          └──────────────────┘
         │   Upload chunk 0 as-is ──────────────────────►
         │
Chunk 1+ ─► Prepend cached init segment
            Upload (init + chunk) ──────────────────────►
```

---

## Frontend Implementation

### File: `src/hooks/useAudioRecorder.ts`

#### 1. Add init segment extraction helper

```typescript
// Find offset of first Cluster element in WebM (where init segment ends)
const findClusterOffset = (data: Uint8Array): number => {
  const CLUSTER_ID = [0x1F, 0x43, 0xB6, 0x75];
  for (let i = 0; i < data.length - 4; i++) {
    if (data[i] === CLUSTER_ID[0] && 
        data[i+1] === CLUSTER_ID[1] &&
        data[i+2] === CLUSTER_ID[2] && 
        data[i+3] === CLUSTER_ID[3]) {
      return i;
    }
  }
  return data.length; // Fallback: entire chunk is init
};

// Extract WebM init segment from first chunk
const extractInitSegment = async (firstChunk: Blob): Promise<ArrayBuffer> => {
  const buffer = await firstChunk.arrayBuffer();
  const initEnd = findClusterOffset(new Uint8Array(buffer));
  return buffer.slice(0, initEnd);
};
```

#### 2. Add state for cached init segment

```typescript
// Inside useAudioRecorder hook
const initSegmentRef = useRef<ArrayBuffer | null>(null);
```

#### 3. Modify ondataavailable handler

```typescript
mediaRecorder.ondataavailable = async (event) => {
  const blob = event.data;
  if (blob.size === 0) return;
  
  let uploadBlob: Blob;
  
  if (chunkIndex === 0) {
    // Extract and cache init segment from first chunk
    initSegmentRef.current = await extractInitSegment(blob);
    // Send chunk 0 as-is (already has header)
    uploadBlob = blob;
  } else {
    // Prepend cached init segment to create valid WebM
    uploadBlob = new Blob(
      [initSegmentRef.current!, blob], 
      { type: 'audio/webm' }
    );
  }
  
  await uploadChunk(sessionId, chunkIndex, uploadBlob);
  chunkIndex++;
};
```

#### 4. Reset on new recording

```typescript
const startRecording = async () => {
  initSegmentRef.current = null; // Clear cached init segment
  chunkIndex = 0;
  // ... existing start logic
};
```

---

## Backend Changes

**None required!** ✅

Each chunk the backend receives is now a complete, valid WebM file.

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/hooks/useAudioRecorder.ts` | Add init extraction + prepend logic |

---

## Testing Plan

### Manual E2E Test
1. Set `RECORDING_TIMESLICE_MS = 30000` (30s)
2. Record for 90+ seconds (triggers 3+ chunks)
3. Verify each chunk processes successfully in logs
4. Finalize and verify accumulated transcription

### Verify in Logs
```
[worker-0] Processing sess_xxx_chunk_0 ← Works (has header)
[worker-0] Completed sess_xxx_chunk_0
[worker-0] Processing sess_xxx_chunk_1 ← Now works (prepended header)
[worker-0] Completed sess_xxx_chunk_1
```

---

## Estimated Effort

| Task | Time |
|------|------|
| Implement init extraction | 1 hour |
| Modify upload handler | 30 min |
| Testing | 1 hour |
| **Total** | **2-3 hours** |

---

## Trade-offs

| Aspect | Impact |
|--------|--------|
| Upload size | +1-4KB per chunk (~2% overhead) |
| Backend changes | None ✅ |
| Complexity | Frontend only |
| Reliability | High (standard WebM structure) |
