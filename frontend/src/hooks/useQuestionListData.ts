/**
 * Custom hook for loading question list data from the backend.
 * 
 * Handles:
 * - URL parsing for questionListId and currentPartIndex
 * - Fetching questions and question list metadata
 * - Session start time tracking
 * - Loading and error states
 * - Cleanup on unmount
 */

import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { fetchQuestionsInList, fetchQuestionLists } from "../services/api";
import { Question as APIQuestion, QuestionListMetadata } from "../types/api";

export interface UseQuestionListDataReturn {
    /** Question list ID from URL (defaults to 1) */
    questionListId: number;
    /** Current part index (0-based, derived from URL partId) */
    currentPartIndex: number;
    /** Key for storing part state (1-based string) */
    partStateKey: string;
    /** All questions in the list */
    questions: APIQuestion[];
    /** Question list metadata */
    questionList: QuestionListMetadata | null;
    /** Current question being displayed */
    currentQuestion: APIQuestion | undefined;
    /** Whether data is loading */
    loading: boolean;
    /** Error message if any */
    error: string | null;
    /** Function to set error state */
    setError: (error: string | null) => void;
}

/**
 * Hook for loading and managing question list data
 */
export function useQuestionListData(): UseQuestionListDataReturn {
    const { id, partId } = useParams<{ id: string; partId?: string }>();

    // Parse URL params
    const questionListId = id ? Number(id) : 1;
    const currentPartIndex = partId ? Number(partId) - 1 : 0; // partId is 1-based, convert to 0-based
    const partStateKey = String(currentPartIndex + 1);

    // State for backend data
    const [questions, setQuestions] = useState<APIQuestion[]>([]);
    const [questionList, setQuestionList] = useState<QuestionListMetadata | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Store session start time when entering question list for the first time
    useEffect(() => {
        const sessionKey = `question_session_start_${questionListId}`;
        // Only set start time if it doesn't exist (first time entering this question list)
        if (!sessionStorage.getItem(sessionKey)) {
            sessionStorage.setItem(sessionKey, Date.now().toString());
        }
    }, [questionListId]);

    // Fetch question list and questions from backend when questionListId changes
    useEffect(() => {
        const abortController = new AbortController();
        let isMounted = true;

        const loadData = async () => {
            try {
                setLoading(true);
                setError(null);

                // Fetch questions
                const questionsData = await fetchQuestionsInList(questionListId, abortController.signal);
                if (!isMounted) return;
                setQuestions(questionsData);

                // Fetch question list metadata to get the title
                const questionLists = await fetchQuestionLists(abortController.signal);
                if (!isMounted) return;
                const currentList = questionLists.find(list => list.id === questionListId);
                setQuestionList(currentList || null);
            } catch (err) {
                // Don't update state if component unmounted or request was aborted
                if (!isMounted || abortController.signal.aborted) return;

                setError(err instanceof Error ? err.message : "Failed to load data");
            } finally {
                if (isMounted && !abortController.signal.aborted) {
                    setLoading(false);
                }
            }
        };

        loadData();

        // Cleanup: abort request and mark as unmounted
        return () => {
            isMounted = false;
            abortController.abort();
        };
    }, [questionListId]);

    // Get current question from backend data
    const currentQuestion = questions[currentPartIndex];

    return {
        questionListId,
        currentPartIndex,
        partStateKey,
        questions,
        questionList,
        currentQuestion,
        loading,
        error,
        setError,
    };
}
