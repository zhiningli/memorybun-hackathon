/**
 * Grading Service API client
 *
 * Handles communication with the grading service backend for AI-powered
 * answer evaluation and feedback.
 */

import {
    GradingStatus,
    GradingStatusResponse,
    GradingResultResponse,
} from "../types/api";

// Grading service base URL - empty string means same origin (nginx proxies to backend)
// For local development, set VITE_GRADING_API_URL=http://localhost:8002
export const GRADING_API_BASE_URL =
    (import.meta as any).env?.VITE_GRADING_API_URL || "";

/**
 * Get grading status for a session.
 * Use this for polling to check if grading is complete.
 *
 * @param sessionId - Session identifier from transcription
 * @param signal - Optional AbortSignal to cancel the request
 * @returns Grading status with optional score/feedback if completed
 */
export async function getGradingStatus(
    sessionId: string,
    signal?: AbortSignal
): Promise<GradingStatusResponse> {
    const response = await fetch(
        `${GRADING_API_BASE_URL}/api/v1/grading/session/${sessionId}/status`,
        { signal }
    );

    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(
            `Failed to get grading status: ${response.statusText}. ${errorText}`
        );
    }

    return response.json();
}

/**
 * Get full grading result for a session.
 * Call after status indicates "completed".
 *
 * @param sessionId - Session identifier from transcription
 * @param signal - Optional AbortSignal to cancel the request
 * @returns Full grading result with score breakdown
 */
export async function getGradingResult(
    sessionId: string,
    signal?: AbortSignal
): Promise<GradingResultResponse> {
    const response = await fetch(
        `${GRADING_API_BASE_URL}/api/v1/grading/session/${sessionId}/result`,
        { signal }
    );

    if (!response.ok) {
        if (response.status === 404) {
            throw new Error("Grading result not found");
        }
        const errorText = await response.text();
        throw new Error(
            `Failed to get grading result: ${response.statusText}. ${errorText}`
        );
    }

    return response.json();
}

/**
 * Poll for grading status until completed or failed.
 *
 * @param sessionId - Session identifier
 * @param options - Polling options
 * @returns Final status when completed or failed
 */
export async function pollGradingStatus(
    sessionId: string,
    options: {
        intervalMs?: number;
        maxAttempts?: number;
        signal?: AbortSignal;
        onStatusChange?: (status: GradingStatus) => void;
    } = {}
): Promise<GradingStatusResponse> {
    const { intervalMs = 2000, maxAttempts = 60, signal, onStatusChange } = options;

    let attempts = 0;
    let lastStatus: GradingStatus | null = null;

    while (attempts < maxAttempts) {
        if (signal?.aborted) {
            throw new Error("Polling aborted");
        }

        const status = await getGradingStatus(sessionId, signal);

        // Notify on status change
        if (status.status !== lastStatus) {
            lastStatus = status.status as GradingStatus;
            onStatusChange?.(lastStatus);
        }

        // Terminal states - stop polling
        if (status.status === "completed" || status.status === "failed") {
            return status;
        }

        // Wait before next poll
        await new Promise((resolve) => setTimeout(resolve, intervalMs));
        attempts++;
    }

    throw new Error(`Grading timed out after ${maxAttempts} attempts`);
}

// ============================================
// SUMMARY REPORT API
// ============================================

import {
    CreateSummaryResponse,
    SummaryStatusResponse,
    SummaryResultResponse
} from "../types/api";

/**
 * Trigger summary generation for a question list session.
 *
 * @param sessionIds - List of session IDs to summarize
 * @returns Summary task creation response
 */
export async function createSummary(
    sessionIds: string[]
): Promise<CreateSummaryResponse> {
    const response = await fetch(
        `${GRADING_API_BASE_URL}/api/v1/grading/summarize`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                session_ids: sessionIds,
            }),
        }
    );

    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(
            `Failed to create summary: ${response.statusText}. ${errorText}`
        );
    }

    return response.json();
}

/**
 * Get status of a summary generation task.
 *
 * @param summaryId - Summary task ID
 * @returns Status of the summary task
 */
export async function getSummaryStatus(
    summaryId: string
): Promise<SummaryStatusResponse> {
    const response = await fetch(
        `${GRADING_API_BASE_URL}/api/v1/grading/summary/${summaryId}/status`
    );

    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(
            `Failed to get summary status: ${response.statusText}. ${errorText}`
        );
    }

    return response.json();
}

/**
 * Get the final result of a summary generation task.
 *
 * @param summaryId - Summary task ID
 * @returns Final summary report data
 */
export async function getSummaryResult(
    summaryId: string
): Promise<SummaryResultResponse> {
    const response = await fetch(
        `${GRADING_API_BASE_URL}/api/v1/grading/summary/${summaryId}/result`
    );

    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(
            `Failed to get summary result: ${response.statusText}. ${errorText}`
        );
    }

    return response.json();
}
