/**
 * Transcription Service API client
 * 
 * Handles communication with the transcription service backend for audio transcription.
 * Supports streaming audio chunks and retrieving transcription results.
 */

import {
  TranscriptionSession,
  ChunkUploadResponse,
  ChunkStatusResponse,
  SessionResultResponse,
  WhisperModel,
} from "../types/api";

// Transcription API base URL - empty string means same origin (nginx proxies to backend)
// For local development, set VITE_TRANSCRIPTION_API_URL=http://localhost:8001
export const TRANSCRIPTION_API_BASE_URL =
  (import.meta as any).env?.VITE_TRANSCRIPTION_API_URL || "";

// Default Whisper model to use
export const DEFAULT_WHISPER_MODEL: WhisperModel =
  ((import.meta as any).env?.VITE_TRANSCRIPTION_MODEL as WhisperModel) || "base";

/**
 * Create a new transcription session
 * @param model - Whisper model to use (defaults to "base")
 * @param questionId - Optional question identifier
 * @param studentId - Optional student identifier
 * @param signal - Optional AbortSignal to cancel the request
 * @returns Transcription session with session_id
 */
export async function createSession(
  model: WhisperModel = DEFAULT_WHISPER_MODEL,
  questionId?: string,
  studentId?: string,
  signal?: AbortSignal
): Promise<TranscriptionSession> {
  const body: {
    model: WhisperModel;
    question_id?: string;
    student_id?: string;
  } = {
    model,
  };

  if (questionId) {
    body.question_id = questionId;
  }
  if (studentId) {
    body.student_id = studentId;
  }

  const response = await fetch(`${TRANSCRIPTION_API_BASE_URL}/api/v1/transcribe/session`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
    signal,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(
      `Failed to create transcription session: ${response.statusText}. ${errorText}`
    );
  }

  return response.json();
}

/**
 * Upload an audio chunk to the transcription service
 * @param sessionId - Session identifier from createSession
 * @param chunkIndex - 0-based index of this chunk
 * @param audioBlob - Audio blob (WebM/Opus format)
 * @param signal - Optional AbortSignal to cancel the request
 * @returns Chunk upload response with task_id
 */
export async function uploadChunk(
  sessionId: string,
  chunkIndex: number,
  audioBlob: Blob,
  signal?: AbortSignal
): Promise<ChunkUploadResponse> {
  const formData = new FormData();
  formData.append("chunk_index", chunkIndex.toString());
  formData.append("audio_file", audioBlob, "chunk.webm");

  const response = await fetch(
    `${TRANSCRIPTION_API_BASE_URL}/api/v1/transcribe/session/${sessionId}/audio/chunk`,
    {
      method: "POST",
      body: formData,
      signal,
    }
  );

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(
      `Failed to upload chunk ${chunkIndex}: ${response.statusText}. ${errorText}`
    );
  }

  return response.json();
}

/**
 * Check the processing status of a chunk
 * @param sessionId - Session identifier
 * @param chunkIndex - Index of the chunk to check
 * @param signal - Optional AbortSignal to cancel the request
 * @returns Chunk status response
 */
export async function getChunkStatus(
  sessionId: string,
  chunkIndex: number,
  signal?: AbortSignal
): Promise<ChunkStatusResponse> {
  const response = await fetch(
    `${TRANSCRIPTION_API_BASE_URL}/api/v1/transcribe/session/${sessionId}/audio/chunk/${chunkIndex}/status`,
    {
      method: "GET",
      signal,
    }
  );

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error(`Chunk ${chunkIndex} not found for session ${sessionId}`);
    }
    const errorText = await response.text();
    throw new Error(
      `Failed to get chunk status: ${response.statusText}. ${errorText}`
    );
  }

  return response.json();
}

/**
 * Get the accumulated transcription result for a session
 * Can be called at any time to retrieve current transcription progress
 * @param sessionId - Session identifier
 * @param signal - Optional AbortSignal to cancel the request
 * @returns Session result with accumulated transcription text
 */
export async function getSessionResult(
  sessionId: string,
  signal?: AbortSignal
): Promise<SessionResultResponse> {
  const response = await fetch(
    `${TRANSCRIPTION_API_BASE_URL}/api/v1/transcribe/session/${sessionId}/audio`,
    {
      method: "GET",
      signal,
    }
  );

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error(`Session ${sessionId} not found`);
    }
    const errorText = await response.text();
    throw new Error(
      `Failed to get session result: ${response.statusText}. ${errorText}`
    );
  }

  return response.json();
}

/**
 * Finalize a transcription session
 * Call this after all chunks have been uploaded to mark the session as complete
 * @param sessionId - Session identifier
 * @param signal - Optional AbortSignal to cancel the request
 * @returns Final session result with complete transcription
 */
export async function finalizeSession(
  sessionId: string,
  signal?: AbortSignal
): Promise<SessionResultResponse> {
  const response = await fetch(
    `${TRANSCRIPTION_API_BASE_URL}/api/v1/transcribe/session/${sessionId}/audio/finalize`,
    {
      method: "POST",
      signal,
    }
  );

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error(`Session ${sessionId} not found`);
    }
    const errorText = await response.text();
    throw new Error(
      `Failed to finalize session: ${response.statusText}. ${errorText}`
    );
  }

  return response.json();
}

/**
 * Poll for chunk status until it's completed or failed
 * @param sessionId - Session identifier
 * @param chunkIndex - Index of the chunk to poll
 * @param options - Polling options
 * @param options.intervalMs - Polling interval in milliseconds (default: 1000)
 * @param options.maxAttempts - Maximum number of polling attempts (default: 60)
 * @param options.signal - Optional AbortSignal to cancel polling
 * @returns Chunk status when completed or failed
 */
export async function pollChunkStatus(
  sessionId: string,
  chunkIndex: number,
  options: {
    intervalMs?: number;
    maxAttempts?: number;
    signal?: AbortSignal;
  } = {}
): Promise<ChunkStatusResponse> {
  const { intervalMs = 1000, maxAttempts = 60, signal } = options;

  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    if (signal?.aborted) {
      throw new Error("Polling cancelled");
    }

    const status = await getChunkStatus(sessionId, chunkIndex, signal);

    if (status.status === "completed" || status.status === "failed") {
      return status;
    }

    // Wait before next poll (except on last attempt)
    if (attempt < maxAttempts - 1) {
      await new Promise((resolve) => setTimeout(resolve, intervalMs));
    }
  }

  // If we've exhausted attempts, get final status
  const finalStatus = await getChunkStatus(sessionId, chunkIndex, signal);
  throw new Error(
    `Chunk ${chunkIndex} did not complete within ${maxAttempts} attempts. Status: ${finalStatus.status}`
  );
}

/**
 * Upload a screenshot for a transcription session
 * @param sessionId - Session identifier from createSession
 * @param imageBlob - Image blob (PNG, JPEG, or WebP format)
 * @param signal - Optional AbortSignal to cancel the request
 * @returns Screenshot upload response with readiness status
 */
export async function uploadScreenshot(
  sessionId: string,
  imageBlob: Blob,
  signal?: AbortSignal
): Promise<ScreenshotUploadResponse> {
  const formData = new FormData();

  // Determine file extension from MIME type
  const mimeToExt: Record<string, string> = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
  };
  const ext = mimeToExt[imageBlob.type] || "png";

  formData.append("screenshot", imageBlob, `screenshot.${ext}`);

  const response = await fetch(
    `${TRANSCRIPTION_API_BASE_URL}/api/v1/transcribe/session/${sessionId}/screenshot`,
    {
      method: "POST",
      body: formData,
      signal,
    }
  );

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(
      `Failed to upload screenshot: ${response.statusText}. ${errorText}`
    );
  }

  return response.json();
}
