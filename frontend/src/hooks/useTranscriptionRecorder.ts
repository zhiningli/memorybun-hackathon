/**
 * Custom hook for transcription recording orchestration.
 * 
 * Uses useAudioRecorder internally and manages the full transcription flow:
 * - Start/stop recording
 * - Create transcription sessions
 * - Stream audio chunks to backend
 * - Poll for chunk status
 * - Finalize and retrieve transcription results
 * 
 * Provides a clean API for the UI to control recording and display status.
 */

import { useState, useRef, useCallback, useEffect } from "react";
import { useAudioRecorder, UseAudioRecorderReturn } from "./useAudioRecorder";
import { RecordingStage } from "../screens/QuestionSample/sections";
import {
    createSession,
    uploadChunk,
    pollChunkStatus,
    finalizeSession,
    getSessionResult,
    uploadScreenshot,
} from "../services/transcriptionApi";
import { isRecordingDurationValid, getRecordingTooShortMessage } from "../config/recording";

// Status of the transcription recorder
export type TranscriptionStatus =
    | "idle"           // Not started
    | "requesting_permission"  // Requesting microphone permission
    | "ready"          // Ready to record (permission granted)
    | "creating_session"  // Creating transcription session
    | "recording"      // Recording in progress
    | "uploading"      // Uploading remaining chunks
    | "processing"     // Processing/transcribing
    | "completed"      // Transcription completed successfully
    | "too_short"      // Recording was too short, needs retry
    | "error";         // Error occurred

// Error types for UI handling
export type TranscriptionErrorType =
    | "permission_denied"
    | "no_microphone"
    | "not_supported"
    | "network_error"
    | "session_error"
    | "processing_error"
    | "no_audio"
    | "recording_too_short"
    | "unknown";

export interface TranscriptionError {
    type: TranscriptionErrorType;
    message: string;
}

// Chunk upload progress
export interface ChunkProgress {
    chunkIndex: number;
    status: "pending" | "uploading" | "processing" | "completed" | "failed";
    error?: string;
}

export interface UseTranscriptionRecorderParams {
    /** Question ID for the transcription session */
    questionId?: string;
    /** Student ID for the transcription session */
    studentId?: string;
    /** Whisper model to use (default: "base") */
    model?: "tiny" | "base" | "small" | "medium" | "large";
    /** Callback to capture screenshot when recording stops */
    captureScreenshot?: () => Promise<Blob | null>;
    /** Callback when transcription completes successfully */
    onComplete?: (transcription: string) => void;
    /** Callback when an error occurs */
    onError?: (error: TranscriptionError) => void;
}

export interface UseTranscriptionRecorderReturn {
    // Status
    status: TranscriptionStatus;
    recordingStage: RecordingStage;
    isRecording: boolean;

    // Progress
    sessionId: string | null;
    chunks: ChunkProgress[];
    transcriptionResult: string | null;

    // Error handling
    error: TranscriptionError | null;
    hasPermission: boolean;
    isSupported: boolean;

    // Actions
    requestPermission: () => Promise<boolean>;
    startRecording: () => Promise<void>;
    stopRecording: () => Promise<void>;
    markCompleted: () => void;
    reset: () => void;

    // Internal access (for advanced use cases)
    audioRecorder: UseAudioRecorderReturn;
}

/**
 * Hook for orchestrating transcription recording
 */
export function useTranscriptionRecorder({
    questionId,
    studentId,
    model = "base",
    captureScreenshot,
    onComplete,
    onError,
}: UseTranscriptionRecorderParams = {}): UseTranscriptionRecorderReturn {
    // Use the audio recorder hook internally
    const audioRecorder = useAudioRecorder();

    // State
    const [status, setStatus] = useState<TranscriptionStatus>("idle");
    const [sessionId, setSessionId] = useState<string | null>(null);
    const [chunks, setChunks] = useState<ChunkProgress[]>([]);
    const [transcriptionResult, setTranscriptionResult] = useState<string | null>(null);
    const [error, setError] = useState<TranscriptionError | null>(null);

    // Refs
    const abortControllerRef = useRef<AbortController | null>(null);
    const uploadedChunkIndicesRef = useRef<Set<number>>(new Set());
    const recordingStartTimeRef = useRef<number | null>(null);

    // Derived state
    const hasPermission = audioRecorder.permissionStatus === "granted";
    const isSupported = audioRecorder.isSupported;
    const isRecording = status === "recording";

    // Map status to RecordingStage for compatibility
    const recordingStage: RecordingStage = (() => {
        switch (status) {
            case "idle":
            case "requesting_permission":
            case "ready":
            case "creating_session":
                return "ready";
            case "recording":
                return "recording";
            case "uploading":
                return "uploading";
            case "processing":
                return "evaluating";
            case "completed":
                return "successful";
            case "too_short":
                return "too_short";
            case "error":
                return "ready";
            default:
                return "ready";
        }
    })();

    /**
     * Create an error object
     */
    const createError = useCallback((type: TranscriptionErrorType, message: string): TranscriptionError => {
        return { type, message };
    }, []);

    /**
     * Handle and report an error
     */
    const handleError = useCallback((err: unknown, defaultType: TranscriptionErrorType = "unknown") => {
        let errorType: TranscriptionErrorType = defaultType;
        let errorMessage = "An unknown error occurred";

        if (err instanceof Error) {
            errorMessage = err.message;

            // Detect error type from message
            if (err.name === "NotAllowedError" || errorMessage.includes("permission")) {
                errorType = "permission_denied";
                errorMessage = "Microphone permission denied. Please allow microphone access and try again.";
            } else if (err.name === "NotFoundError" || errorMessage.includes("microphone")) {
                errorType = "no_microphone";
                errorMessage = "No microphone found. Please connect a microphone and try again.";
            } else if (errorMessage.includes("network") || errorMessage.includes("fetch") || errorMessage.includes("Failed to fetch")) {
                errorType = "network_error";
                errorMessage = "Network error. Please check your connection and try again.";
            } else if (errorMessage.includes("session")) {
                errorType = "session_error";
            } else if (errorMessage.includes("No audio")) {
                errorType = "no_audio";
            } else if (errorMessage.includes("Recording too short") || errorMessage.includes("too short")) {
                errorType = "recording_too_short";
            }
        }

        const errorObj = createError(errorType, errorMessage);
        setError(errorObj);
        setStatus("error");
        onError?.(errorObj);
    }, [createError, onError]);

    /**
     * Upload a single chunk
     */
    const uploadChunkAsync = useCallback(async (chunk: Blob, chunkIndex: number, currentSessionId: string) => {
        if (!currentSessionId) {
            console.error("No session ID available for chunk upload");
            return;
        }

        // Update progress to uploading
        setChunks((prev) => {
            const updated = [...prev];
            updated[chunkIndex] = { chunkIndex, status: "uploading" };
            return updated;
        });

        try {
            // Upload chunk
            await uploadChunk(currentSessionId, chunkIndex, chunk, abortControllerRef.current?.signal);

            // Update progress to processing
            setChunks((prev) => {
                const updated = [...prev];
                updated[chunkIndex] = { chunkIndex, status: "processing" };
                return updated;
            });

            // Poll for chunk completion
            const chunkStatus = await pollChunkStatus(
                currentSessionId,
                chunkIndex,
                {
                    intervalMs: 1000,
                    maxAttempts: 60,
                    signal: abortControllerRef.current?.signal,
                }
            );

            // Update progress based on result
            setChunks((prev) => {
                const updated = [...prev];
                if (chunkStatus.status === "completed") {
                    updated[chunkIndex] = { chunkIndex, status: "completed" };
                } else {
                    updated[chunkIndex] = {
                        chunkIndex,
                        status: "failed",
                        error: chunkStatus.error || "Unknown error",
                    };
                }
                return updated;
            });
        } catch (err) {
            console.error(`Error uploading chunk ${chunkIndex}:`, err);
            setChunks((prev) => {
                const updated = [...prev];
                updated[chunkIndex] = {
                    chunkIndex,
                    status: "failed",
                    error: err instanceof Error ? err.message : "Upload failed",
                };
                return updated;
            });
        }
    }, []);

    /**
     * Request microphone permission
     */
    const requestPermission = useCallback(async (): Promise<boolean> => {
        if (!isSupported) {
            handleError(new Error("Audio recording is not supported in this browser"), "not_supported");
            return false;
        }

        setStatus("requesting_permission");
        setError(null);

        try {
            const granted = await audioRecorder.requestPermission();
            if (granted) {
                setStatus("ready");
                return true;
            } else {
                handleError(new Error("Microphone permission denied"), "permission_denied");
                return false;
            }
        } catch (err) {
            handleError(err, "permission_denied");
            return false;
        }
    }, [isSupported, audioRecorder, handleError]);

    /**
     * Start recording
     */
    const startRecording = useCallback(async () => {
        try {
            setError(null);

            // Check if supported
            if (!isSupported) {
                throw createError("not_supported", "Audio recording is not supported in this browser. Please use Chrome or a modern browser.");
            }

            // Request permission if needed
            if (!hasPermission) {
                setStatus("requesting_permission");
                const granted = await audioRecorder.requestPermission();
                if (!granted) {
                    // Reset to idle state since recording won't start
                    setStatus("idle");
                    throw new Error("Microphone permission denied");
                }
            }

            // Create abort controller
            abortControllerRef.current = new AbortController();

            // Reset chunk tracking
            uploadedChunkIndicesRef.current = new Set();
            setChunks([]);
            setTranscriptionResult(null);

            // Create transcription session
            setStatus("creating_session");
            let session;
            try {
                session = await createSession(
                    model,
                    questionId,
                    studentId,
                    abortControllerRef.current.signal
                );
            } catch (sessionErr) {
                if (sessionErr instanceof Error && sessionErr.message.includes("Failed to fetch")) {
                    throw new Error("Cannot connect to transcription service. Please check if the service is running.");
                }
                throw sessionErr;
            }

            setSessionId(session.session_id);

            // Start recording and track start time
            await audioRecorder.startRecording();
            recordingStartTimeRef.current = Date.now();
            setStatus("recording");
        } catch (err) {
            handleError(err);
            audioRecorder.reset();
            // Re-throw so caller knows recording failed and doesn't update UI state
            throw err;
        }
    }, [isSupported, hasPermission, audioRecorder, model, questionId, studentId, createError, handleError]);

    /**
     * Stop recording and finalize transcription
     */
    const stopRecording = useCallback(async () => {
        try {
            // Calculate recording duration
            const recordingDuration = recordingStartTimeRef.current 
                ? (Date.now() - recordingStartTimeRef.current) / 1000 
                : 0;

            // Validate minimum recording duration
            if (!isRecordingDurationValid(recordingDuration)) {
                // Reset recording state without proceeding
                audioRecorder.stopRecording();
                audioRecorder.reset();
                recordingStartTimeRef.current = null;
                
                // Set to "too_short" status to show retry button
                setStatus("too_short");
                const errorMessage = getRecordingTooShortMessage();
                const tooShortError = {
                    type: "recording_too_short" as const,
                    message: errorMessage,
                };
                setError(tooShortError);
                onError?.(tooShortError);
                return; // Exit early, don't throw
            }

            // Stop the audio recorder
            audioRecorder.stopRecording();
            setStatus("uploading");

            if (!sessionId) {
                throw new Error("No session ID available. Recording may not have started properly.");
            }

            // Wait for any in-flight uploads
            await new Promise((resolve) => setTimeout(resolve, 500));

            // Get current chunks
            const currentChunks = audioRecorder.getChunks();
            const uploadedIndices = uploadedChunkIndicesRef.current;

            if (currentChunks.length === 0) {
                throw new Error("No audio recorded. Please try recording again.");
            }

            // Upload any remaining chunks
            const uploadPromises: Promise<void>[] = [];
            for (let i = 0; i < currentChunks.length; i++) {
                if (!uploadedIndices.has(i)) {
                    uploadedIndices.add(i);
                    uploadPromises.push(
                        uploadChunkAsync(currentChunks[i], i, sessionId).catch((err) => {
                            console.error(`Failed to upload chunk ${i}:`, err);
                        })
                    );
                }
            }

            await Promise.allSettled(uploadPromises);

            // Wait for all chunks to complete processing
            setStatus("processing");

            const chunkStatusPromises = currentChunks.map((_, index) =>
                pollChunkStatus(sessionId, index, {
                    intervalMs: 1000,
                    maxAttempts: 60,
                    signal: abortControllerRef.current?.signal,
                }).catch((err) => {
                    console.error(`Failed to get status for chunk ${index}:`, err);
                    return { status: "failed" as const, error: err instanceof Error ? err.message : "Unknown error" };
                })
            );

            const allChunksCompleted = await Promise.allSettled(chunkStatusPromises);

            // Check for failures
            const failedChunks = allChunksCompleted.filter(
                (result) =>
                    result.status === "rejected" ||
                    (result.status === "fulfilled" && result.value.status === "failed")
            );

            if (failedChunks.length === allChunksCompleted.length) {
                const errorMessages = failedChunks
                    .map((result) => {
                        if (result.status === "rejected") {
                            return result.reason?.message || "Unknown error";
                        }
                        return result.value.error || "Processing failed";
                    })
                    .filter(Boolean);
                throw new Error(`All chunks failed to process: ${errorMessages.join(", ")}`);
            }

            // Finalize session
            const finalResult = await finalizeSession(
                sessionId,
                abortControllerRef.current?.signal
            ).catch(async (finalizeErr) => {
                console.error("Failed to finalize session:", finalizeErr);
                return getSessionResult(sessionId, abortControllerRef.current?.signal).catch(() => {
                    throw new Error("Failed to retrieve transcription result");
                });
            });

            // Upload screenshot if capture function is provided
            if (captureScreenshot) {
                try {
                    const screenshotBlob = await captureScreenshot();
                    if (screenshotBlob) {
                        console.log(`[Session ${sessionId}] Uploading screenshot: ${screenshotBlob.size} bytes`);
                        await uploadScreenshot(sessionId, screenshotBlob, abortControllerRef.current?.signal);
                        console.log(`[Session ${sessionId}] Screenshot uploaded successfully`);
                    } else {
                        console.warn(`[Session ${sessionId}] No screenshot captured (null blob)`);
                    }
                } catch (screenshotErr) {
                    // Log error but don't fail the transcription
                    console.error(`[Session ${sessionId}] Failed to upload screenshot:`, screenshotErr);
                }
            }

            const transcription = finalResult.full_text || "Transcription unavailable";
            setTranscriptionResult(transcription);
            // Set to processing status (maps to "evaluating" stage)
            // QuestionSample will call markCompleted() when grading is done
            setStatus("processing");
            onComplete?.(transcription);
        } catch (err) {
            handleError(err, "processing_error");
        }
    }, [sessionId, audioRecorder, uploadChunkAsync, captureScreenshot, handleError, onComplete]);

    /**
     * Reset the recorder state
     */
    const reset = useCallback(() => {
        // Abort any ongoing operations
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
            abortControllerRef.current = null;
        }

        // Reset audio recorder
        audioRecorder.reset();

        // Reset state
        setStatus("idle");
        setSessionId(null);
        setChunks([]);
        setTranscriptionResult(null);
        setError(null);
        uploadedChunkIndicesRef.current = new Set();
        recordingStartTimeRef.current = null;
    }, [audioRecorder]);

    /**
     * Mark the session as completed (after grading is done)
     */
    const markCompleted = useCallback(() => {
        setStatus("completed");
    }, []);

    // Effect to stream chunks during recording
    useEffect(() => {
        if (status !== "recording" || !sessionId || audioRecorder.chunks.length === 0) {
            return;
        }

        const currentChunks = audioRecorder.chunks;
        const uploadedIndices = uploadedChunkIndicesRef.current;

        // Upload new chunks
        currentChunks.forEach((chunk, index) => {
            if (!uploadedIndices.has(index)) {
                uploadedIndices.add(index);
                uploadChunkAsync(chunk, index, sessionId).catch((err) => {
                    console.error(`Error uploading chunk ${index}:`, err);
                });
            }
        });
    }, [status, sessionId, audioRecorder.chunks.length, uploadChunkAsync]);

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            if (abortControllerRef.current) {
                abortControllerRef.current.abort();
            }
            audioRecorder.stopRecording();
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    return {
        // Status
        status,
        recordingStage,
        isRecording,

        // Progress
        sessionId,
        chunks,
        transcriptionResult,

        // Error handling
        error,
        hasPermission,
        isSupported,

        // Actions
        requestPermission,
        startRecording,
        stopRecording,
        markCompleted,
        reset,

        // Internal access
        audioRecorder,
    };
}
