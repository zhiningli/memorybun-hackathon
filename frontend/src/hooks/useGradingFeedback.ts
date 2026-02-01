/**
 * Hook for polling grading service feedback.
 * 
 * Polls the grading service every 2 seconds to check if
 * AI feedback is ready for a session.
 */

import { useState, useEffect, useRef, useCallback } from "react";
import { GradingStatus, GradingResultResponse } from "../types/api";
import { getGradingStatus, getGradingResult } from "../services/gradingApi";

interface UseGradingFeedbackOptions {
    /** Session ID to poll for */
    sessionId: string | null;
    /** Whether polling is enabled */
    enabled: boolean;
    /** Polling interval in milliseconds (default: 2000) */
    intervalMs?: number;
    /** Callback when grading completes */
    onComplete?: (result: GradingResultResponse) => void;
    /** Callback when grading fails */
    onError?: (error: Error) => void;
}

interface UseGradingFeedbackResult {
    /** Current grading status */
    status: GradingStatus | null;
    /** Full grading result (when completed) */
    result: GradingResultResponse | null;
    /** Whether currently polling */
    isPolling: boolean;
    /** Error if any */
    error: Error | null;
    /** Reset the hook state */
    reset: () => void;
}

export function useGradingFeedback(
    options: UseGradingFeedbackOptions
): UseGradingFeedbackResult {
    const {
        sessionId,
        enabled,
        intervalMs = 2000,
        onComplete,
        onError,
    } = options;

    const [status, setStatus] = useState<GradingStatus | null>(null);
    const [result, setResult] = useState<GradingResultResponse | null>(null);
    const [isPolling, setIsPolling] = useState(false);
    const [error, setError] = useState<Error | null>(null);

    // Use refs to track the latest callbacks without causing re-renders
    const onCompleteRef = useRef(onComplete);
    const onErrorRef = useRef(onError);
    onCompleteRef.current = onComplete;
    onErrorRef.current = onError;

    // Abort controller for cleanup
    const abortControllerRef = useRef<AbortController | null>(null);

    const reset = useCallback(() => {
        setStatus(null);
        setResult(null);
        setIsPolling(false);
        setError(null);
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
            abortControllerRef.current = null;
        }
    }, []);

    useEffect(() => {
        // Don't poll if not enabled or no session ID
        if (!enabled || !sessionId) {
            return;
        }

        // Create abort controller for this polling session
        abortControllerRef.current = new AbortController();
        const signal = abortControllerRef.current.signal;

        let timeoutId: ReturnType<typeof setTimeout>;
        let isMounted = true;

        const poll = async () => {
            if (!isMounted || signal.aborted) return;

            setIsPolling(true);

            try {
                const statusResponse = await getGradingStatus(sessionId, signal);

                if (!isMounted || signal.aborted) return;

                setStatus(statusResponse.status);

                if (statusResponse.status === "completed") {
                    // Fetch full result
                    const fullResult = await getGradingResult(sessionId, signal);

                    if (!isMounted || signal.aborted) return;

                    setResult(fullResult);
                    setIsPolling(false);
                    onCompleteRef.current?.(fullResult);
                    return; // Stop polling
                }

                if (statusResponse.status === "failed") {
                    const err = new Error(statusResponse.message || "Grading failed");
                    setError(err);
                    setIsPolling(false);
                    onErrorRef.current?.(err);
                    return; // Stop polling
                }

                // Continue polling
                timeoutId = setTimeout(poll, intervalMs);
            } catch (err) {
                if (signal.aborted) return;

                const error = err instanceof Error ? err : new Error(String(err));
                setError(error);
                setIsPolling(false);
                onErrorRef.current?.(error);
            }
        };

        // Start polling
        poll();

        // Cleanup
        return () => {
            isMounted = false;
            clearTimeout(timeoutId);
            if (abortControllerRef.current) {
                abortControllerRef.current.abort();
            }
        };
    }, [sessionId, enabled, intervalMs]);

    return {
        status,
        result,
        isPolling,
        error,
        reset,
    };
}
