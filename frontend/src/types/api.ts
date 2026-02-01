/**
 * TypeScript types matching backend Pydantic schemas
 */

// ============================================
// QUESTION LIST TYPES
// ============================================

export enum AccessStatus {
  PUBLIC = "public",
  PRIVATE = "private",
  PREMIUM = "premium",
}

export enum QuestionListCategory {
  GRAPH_PLOTTING = "Graph Plotting",
  CIRCUIT_ANALYSIS = "Circuit Analysis",
  DYNAMICS = "Dynamics",
  FLUID_DYNAMICS = "Fluid Dynamics",
  GUIDED = "Guided",
  FULL_RUN = "Full Run",
}

export enum QuestionListDifficulty {
  EASY = "Easy",
  MEDIUM = "Medium",
  ADVANCED = "Advanced",
}

// Question List Metadata (from /api/v1/question-lists)
export interface QuestionListMetadata {
  id: number;
  title: string;
  categories: QuestionListCategory[];
  subjects: SubjectEnum[];
  difficulty: QuestionListDifficulty;
  duration_seconds: number; // in seconds
  access_status: AccessStatus;
  created_at: string;
  updated_at: string;
}

// ============================================
// QUESTION TYPES
// ============================================

export enum SubjectEnum {
  ENGINEERING = "Engineering",
  MATHEMATICS = "Mathematics",
  PHYSICS = "Physics",
}

export enum QuestionTopicEnum {
  MATHEMATICS = "Mathematics",
  ENERGY = "Energy",
  ELECTRICITY = "Electricity",
  GRAPH_PLOTTING = "Graph Plotting",
  FLUID_DYNAMICS = "Fluid Dynamics",
}

export enum QuestionDifficulty {
  EASY = "easy",
  MEDIUM = "medium",
  HARD = "hard",
}

export interface Hint {
  text: string | null;
  image_url: string | null;
}

// Question (from /api/v1/question-lists/{id}/questions)
export interface Question {
  id: number;
  title: string;
  question_details: string;
  think_time_limit_seconds: number;
  record_time_limit_seconds: number;
  instructions: string[];
  hints: Hint[];
  question_image_url: string | null;
  subjects: SubjectEnum[];
  topics: QuestionTopicEnum[];
  difficulty: QuestionDifficulty;
  rubric_id: number;
  created_at: string;
  updated_at: string;
}

// ============================================
// ANSWER TYPES
// ============================================

// Answer (from /api/v1/answers)
export interface Answer {
  id: number;
  question_id: number;
  text_answer: string | null;
  graph_answer_url: string | null;
  ideal_answer_structure: string[] | null;
  key_constraints_to_mention: string[] | null;
  created_at: string;
  updated_at: string;
}

// ============================================
// TRANSCRIPTION TYPES
// ============================================

export type WhisperModel = "tiny" | "tiny.en" | "base" | "base.en" | "small" | "small.en" | "medium" | "medium.en" | "large";

export type TranscriptionSessionStatus = "active" | "completed" | "expired";

export type ChunkStatus = "pending" | "processing" | "completed" | "failed";

// Transcription Session (from POST /api/v1/transcribe/session)
export interface TranscriptionSession {
  session_id: string;
  model: WhisperModel;
  status: TranscriptionSessionStatus;
  created_at: string;
  student_id: string | null;
  question_id: string | null;
}

// Chunk Upload Response (from POST /api/v1/transcribe/session/{session_id}/audio/chunk)
export interface ChunkUploadResponse {
  task_id: string;
  session_id: string;
  chunk_index: number;
  status: "queued";
  message: string;
}

// Chunk Status Response (from GET /api/v1/transcribe/session/{session_id}/audio/chunk/{chunk_index}/status)
export interface ChunkStatusResponse {
  task_id: string;
  session_id: string;
  chunk_index: number;
  status: ChunkStatus;
  created_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  result: string | null; // Transcribed text if completed
  error: string | null; // Error message if failed
}

// Session Result (from GET /api/v1/transcribe/session/{session_id}/audio or POST /finalize)
export interface SessionResultResponse {
  session_id: string;
  status: TranscriptionSessionStatus;
  full_text: string;
  chunks_processed: number;
  total_duration: number | null;
  total_processing_time: number;
  whisper_model: WhisperModel;
  created_at: string;
  completed_at: string | null;
}

// ============================================
// SCREENSHOT TYPES
// ============================================

export type ScreenshotUploadStatus = "uploaded" | "ready_for_grading";

export type GradingReadinessStatus =
  | "waiting_for_screenshot"
  | "waiting_for_audio"
  | "ready"
  | "enqueued";

// Screenshot Upload Response (from POST /api/v1/transcribe/session/{session_id}/screenshot)
export interface ScreenshotUploadResponse {
  session_id: string;
  screenshot_key: string;
  status: ScreenshotUploadStatus;
  message: string;
  grading_readiness_status?: GradingReadinessStatus;
}

// ============================================
// GRADING TYPES
// ============================================

export type GradingStatus = "processing" | "completed" | "failed";

export interface GradingStatusResponse {
  session_id: string;
  status: GradingStatus;
  message?: string;
}

export interface ScoreBreakdown {
  dimension: string;
  percentage: number;
  feedback: string | null;
}

export interface GradingResultResponse {
  session_id: string;
  feedback: string;
  score?: number;
  confidence?: number;
  internal_notes?: string;
  score_breakdown?: ScoreBreakdown[];
}

// ============================================
// SUMMARY REPORT TYPES
// ============================================

export interface SummaryDimension {
  dimension: string;
  score: number;
  feedback: string;
}

export interface CreateSummaryResponse {
  summary_id: string;
  status: string;
  message: string;
}

export interface SummaryStatusResponse {
  summary_id: string;
  status: "processing" | "completed" | "failed";
  message?: string;
  created_at: string;
  completed_at?: string;
}

export interface SummaryResultResponse {
  summary_id: string;
  overall_feedback: string;
  dimension_scores: SummaryDimension[];
  key_strengths: string[];
  areas_for_improvement: string[];
  analytics_summary: string[];
  created_at: string;
}
