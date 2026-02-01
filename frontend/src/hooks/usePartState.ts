/**
 * Custom hook for managing per-part state in the question sample flow.
 * 
 * Handles:
 * - Per-part state management (prepTime, recordTime, isRecording, etc.)
 * - Timer refs (prep timer, record timer)
 * - Timeout refs (upload, evaluate)
 * - Abort controller for transcription API
 * - Completion tracking
 * - State updates and cleanup
 */

import { useState, useEffect, useRef, useCallback, Dispatch, SetStateAction, MutableRefObject } from "react";
import { RecordingStage } from "../screens/QuestionSample/sections";
import { UseAudioRecorderReturn } from "./useAudioRecorder";
import { Question as APIQuestion } from "../types/api";

// State for each individual part
export interface PartState {
    prepTime: number;
    recordTime: number;
    isRecording: boolean;
    recordingStage: RecordingStage;
    canvasData: string | null; // Base64 data URL of the canvas
    isPrepTimerPaused: boolean; // Whether the prep timer is paused
    sessionId: string | null; // Transcription session ID
    transcriptionResult: string | null; // Final transcription result
}

// Upload progress tracking
export interface ChunkUploadProgress {
    chunkIndex: number;
    status: "pending" | "uploading" | "processing" | "completed" | "failed";
    error?: string;
}

// Default state for a new/unstarted part
export const getDefaultPartState = (): PartState => ({
    prepTime: 0,
    recordTime: 0,
    isRecording: false,
    recordingStage: "ready",
    canvasData: null,
    isPrepTimerPaused: false,
    sessionId: null,
    transcriptionResult: null,
});

export interface UsePartStateParams {
    partStateKey: string;
    questionListId: number;
    currentPartIndex: number;
    currentQuestion: APIQuestion | undefined;
    audioRecorder: UseAudioRecorderReturn;
}

export interface UsePartStateReturn {
    // State
    partStates: Record<string, PartState>;
    setPartStates: Dispatch<SetStateAction<Record<string, PartState>>>;
    currentState: PartState;
    prepTime: number;
    recordTime: number;
    isRecording: boolean;
    recordingStage: RecordingStage;
    isPrepTimerPaused: boolean;
    sessionId: string | null;
    transcriptionResult: string | null;
    completedUpToIndex: number;
    isPrepTimeExceeded: boolean;

    // Chunk progress
    chunkUploadProgress: Record<string, ChunkUploadProgress[]>;
    setChunkUploadProgress: Dispatch<SetStateAction<Record<string, ChunkUploadProgress[]>>>;
    isTranscribing: boolean;
    setIsTranscribing: Dispatch<SetStateAction<boolean>>;

    // Refs
    transcriptionAbortControllerRef: MutableRefObject<AbortController | null>;
    uploadedChunkIndicesRef: MutableRefObject<Set<number>>;
    prepTimerRef: MutableRefObject<ReturnType<typeof setInterval> | null>;
    recordTimerRef: MutableRefObject<ReturnType<typeof setTimeout> | null>;
    uploadTimeoutRef: MutableRefObject<ReturnType<typeof setTimeout> | null>;
    evaluateTimeoutRef: MutableRefObject<ReturnType<typeof setTimeout> | null>;

    // Helpers
    updateCurrentPartState: (updates: Partial<PartState> | ((prev: PartState | undefined) => Partial<PartState>)) => void;
    setCompletedUpToIndex: Dispatch<SetStateAction<number>>;
    clearAllTimeouts: () => void;
}

/**
 * Hook for managing per-part state in the question sample flow
 */
export function usePartState({
    partStateKey,
    questionListId,
    currentPartIndex,
    currentQuestion,
    audioRecorder,
}: UsePartStateParams): UsePartStateReturn {
    // Store state for ALL parts (persists when navigating between parts)
    const [partStates, setPartStates] = useState<Record<string, PartState>>({});

    // Track the highest completed part index
    const [completedUpToIndex, setCompletedUpToIndex] = useState(-1);

    // Track chunk upload progress per part
    const [chunkUploadProgress, setChunkUploadProgress] = useState<Record<string, ChunkUploadProgress[]>>({});
    const [isTranscribing, setIsTranscribing] = useState(false);

    // Get current part's state (or default if not yet started)
    const currentState = partStates[partStateKey] || getDefaultPartState();
    const { prepTime, recordTime, isRecording, recordingStage, isPrepTimerPaused, sessionId, transcriptionResult } = currentState;

    // Refs for timeouts/intervals
    const uploadTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const evaluateTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const prepTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const recordTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const transcriptionAbortControllerRef = useRef<AbortController | null>(null);
    const uploadedChunkIndicesRef = useRef<Set<number>>(new Set());

    // Track previous questionListId for reset detection
    const prevQuestionListId = useRef(questionListId);

    // Cleanup function to clear all timeouts
    const clearAllTimeouts = useCallback(() => {
        if (uploadTimeoutRef.current) {
            clearTimeout(uploadTimeoutRef.current);
            uploadTimeoutRef.current = null;
        }
        if (evaluateTimeoutRef.current) {
            clearTimeout(evaluateTimeoutRef.current);
            evaluateTimeoutRef.current = null;
        }
        if (prepTimerRef.current) {
            clearInterval(prepTimerRef.current);
            prepTimerRef.current = null;
        }
        if (recordTimerRef.current) {
            clearTimeout(recordTimerRef.current);
            recordTimerRef.current = null;
        }
    }, []);

    // Helper to update current part's state
    const updateCurrentPartState = useCallback((updates: Partial<PartState> | ((prev: PartState | undefined) => Partial<PartState>)) => {
        setPartStates(prev => {
            const currentPart = prev[partStateKey] || getDefaultPartState();
            const newUpdates = typeof updates === 'function' ? updates(currentPart) : updates;
            return {
                ...prev,
                [partStateKey]: {
                    ...currentPart,
                    ...newUpdates,
                },
            };
        });
    }, [partStateKey]);

    // Reset ALL state when questionListId changes
    useEffect(() => {
        if (prevQuestionListId.current !== questionListId) {
            clearAllTimeouts();

            // Abort any ongoing transcription requests
            if (transcriptionAbortControllerRef.current) {
                transcriptionAbortControllerRef.current.abort();
                transcriptionAbortControllerRef.current = null;
            }

            // Reset audio recorder
            audioRecorder.reset();

            // Reset state
            setPartStates({});
            setCompletedUpToIndex(-1);
            setChunkUploadProgress({});
            setIsTranscribing(false);
            uploadedChunkIndicesRef.current = new Set();

            prevQuestionListId.current = questionListId;
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [questionListId, clearAllTimeouts]); // audioRecorder accessed via closure

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            clearAllTimeouts();

            if (transcriptionAbortControllerRef.current) {
                transcriptionAbortControllerRef.current.abort();
            }

            // Only stop recording on unmount, don't reset (which clears chunks)
            audioRecorder.stopRecording();
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []); // Only run on mount/unmount

    // Create abort controller for transcription API calls
    useEffect(() => {
        transcriptionAbortControllerRef.current = new AbortController();
        // Reset uploaded chunk indices when part changes
        uploadedChunkIndicesRef.current = new Set();
        return () => {
            if (transcriptionAbortControllerRef.current) {
                transcriptionAbortControllerRef.current.abort();
            }
        };
    }, [partStateKey]);

    // Update completion tracking when a part is successfully completed
    useEffect(() => {
        if (recordingStage === "successful" && currentPartIndex > completedUpToIndex) {
            setCompletedUpToIndex(currentPartIndex);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [recordingStage, currentPartIndex]); // Removed completedUpToIndex to prevent infinite loop

    // Timer count UP for preparation (only when in "ready" state, not recording, and not paused)
    useEffect(() => {
        if (prepTimerRef.current) {
            clearInterval(prepTimerRef.current);
            prepTimerRef.current = null;
        }

        if (!isRecording && recordingStage === "ready" && !isPrepTimerPaused) {
            prepTimerRef.current = setInterval(() => {
                updateCurrentPartState((prev) => ({ prepTime: (prev?.prepTime || 0) + 1 }));
            }, 1000);
        }

        return () => {
            if (prepTimerRef.current) {
                clearInterval(prepTimerRef.current);
                prepTimerRef.current = null;
            }
        };
    }, [isRecording, recordingStage, isPrepTimerPaused, partStateKey, updateCurrentPartState]);

    // Check if prep time limit exceeded
    const isPrepTimeExceeded = currentQuestion ? prepTime >= currentQuestion.think_time_limit_seconds : false;

    return {
        // State
        partStates,
        setPartStates,
        currentState,
        prepTime,
        recordTime,
        isRecording,
        recordingStage,
        isPrepTimerPaused,
        sessionId,
        transcriptionResult,
        completedUpToIndex,
        isPrepTimeExceeded,

        // Chunk progress
        chunkUploadProgress,
        setChunkUploadProgress,
        isTranscribing,
        setIsTranscribing,

        // Refs
        transcriptionAbortControllerRef,
        uploadedChunkIndicesRef,
        prepTimerRef,
        recordTimerRef,
        uploadTimeoutRef,
        evaluateTimeoutRef,

        // Helpers
        updateCurrentPartState,
        setCompletedUpToIndex,
        clearAllTimeouts,
    };
}
