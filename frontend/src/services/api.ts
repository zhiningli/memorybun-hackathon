/**
 * API service for communicating with the backend
 */

import { QuestionListMetadata, Question, Answer } from "../types/api";

// API base URL - empty string means same origin (nginx proxies to backends)
// For local development, set VITE_API_BASE_URL=http://localhost:8000
export const API_BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || "";

/**
 * Fetch all question lists from the backend
 * @param signal - Optional AbortSignal to cancel the request
 */
export async function fetchQuestionLists(signal?: AbortSignal): Promise<QuestionListMetadata[]> {
  const response = await fetch(`${API_BASE_URL}/api/v1/question-lists/`, { signal });

  if (!response.ok) {
    throw new Error(`Failed to fetch question lists: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Fetch all questions in a specific question list
 * @param questionListId - The ID of the question list
 * @param signal - Optional AbortSignal to cancel the request
 */
export async function fetchQuestionsInList(questionListId: number, signal?: AbortSignal): Promise<Question[]> {
  const response = await fetch(`${API_BASE_URL}/api/v1/question-lists/${questionListId}/questions`, { signal });

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error(`Question list ${questionListId} not found`);
    }
    throw new Error(`Failed to fetch questions: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Fetch answers by question IDs
 * @param questionIds - Array of question IDs to get answers for
 * @param signal - Optional AbortSignal to cancel the request
 */
export async function fetchAnswers(questionIds: number[], signal?: AbortSignal): Promise<Answer[]> {
  if (questionIds.length === 0) {
    return [];
  }

  // Build query string with multiple question_id parameters
  const queryParams = questionIds.map(id => `question_id=${id}`).join('&');
  const response = await fetch(`${API_BASE_URL}/api/v1/answers/?${queryParams}`, { signal });

  if (!response.ok) {
    throw new Error(`Failed to fetch answers: ${response.statusText}`);
  }

  return response.json();
}
