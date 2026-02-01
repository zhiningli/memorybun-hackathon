import { useEffect, useCallback, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Avatar, AvatarFallback } from "../../components/ui/avatar";
import { Button } from "../../components/ui/button";
import { QuestionSidebar, DrawingBoard, PrepTimer, type DrawingBoardRef } from "./sections";
import { QuestionPart } from "../../config/questions";
import { Loader2Icon } from "lucide-react";
import { useQuestionListData } from "../../hooks/useQuestionListData";
import { usePartState } from "../../hooks/usePartState";
import { useTranscriptionRecorder } from "../../hooks/useTranscriptionRecorder";
import { useAudioRecorder } from "../../hooks/useAudioRecorder";
import { useGradingFeedback } from "../../hooks/useGradingFeedback";
import { GradingResultResponse, Answer } from "../../types/api";
import { fetchAnswers, API_BASE_URL } from "../../services/api";
import { createSummary, getSummaryStatus, getSummaryResult } from "../../services/gradingApi";

// Note: PartState and ChunkUploadProgress are now exported from usePartState hook

export const QuestionSample = (): JSX.Element => {
  const navigate = useNavigate();

  // Load question list data from backend
  const {
    questionListId,
    currentPartIndex,
    partStateKey,
    questions,
    questionList,
    currentQuestion,
    loading,
    error,
    setError,
  } = useQuestionListData();

  // Audio recording hook (needed for usePartState)
  const audioRecorder = useAudioRecorder();

  // Per-part state management
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const {
    currentState,
    prepTime,
    recordTime,
    isRecording,
    recordingStage,
    isPrepTimerPaused,
    sessionId, // Session ID from backend - kept for future use/debugging
    completedUpToIndex,
    isPrepTimeExceeded,
    recordTimerRef,
    updateCurrentPartState,
  } = usePartState({
    partStateKey,
    questionListId,
    currentPartIndex,
    currentQuestion,
    audioRecorder,
  });

  // Ref for DrawingBoard to capture screenshots
  const drawingBoardRef = useRef<DrawingBoardRef>(null);

  // Transcription recording orchestration
  const transcriptionRecorder = useTranscriptionRecorder({
    questionId: currentQuestion?.id.toString(),
    model: "base",
    captureScreenshot: async () => {
      // Capture whiteboard screenshot when recording stops
      return drawingBoardRef.current?.getScreenshotBlob() ?? null;
    },
    onComplete: (transcription) => {
      updateCurrentPartState({
        transcriptionResult: transcription,
        // Do NOT transition to successful here.
        // We wait for grading + answer fetch to complete in the useEffect below.
        // recordingStage: "successful", 
      });
    },
    onError: (err) => {
      setError(err.message);
      updateCurrentPartState({
        recordingStage: "ready",
        isRecording: false,
      });
    },
  });

  // Sync transcription recorder error to UI
  useEffect(() => {
    if (transcriptionRecorder.error) {
      setError(transcriptionRecorder.error.message);
    }
  }, [transcriptionRecorder.error, setError]);

  // Sync session ID from transcription recorder to part state
  useEffect(() => {
    if (transcriptionRecorder.sessionId) {
      updateCurrentPartState({
        sessionId: transcriptionRecorder.sessionId,
      });
    }
  }, [transcriptionRecorder.sessionId, updateCurrentPartState]);

  // Sync audio recorder error to UI
  useEffect(() => {
    if (audioRecorder.error) {
      console.error("Recording error:", audioRecorder.error);
      setError(audioRecorder.error);
    }
  }, [audioRecorder.error, setError]);

  // Sync transcription recorder stage to part state
  // This ensures UI reflects current status (too_short, uploading, evaluating, etc.)
  useEffect(() => {
    const stage = transcriptionRecorder.recordingStage;
    // Sync these stages from transcription recorder to part state
    if (stage === "too_short" || stage === "uploading" || stage === "evaluating") {
      updateCurrentPartState({
        recordingStage: stage,
      });
    }
  }, [transcriptionRecorder.recordingStage, updateCurrentPartState]);

  // Clear stale session IDs when starting the first question
  useEffect(() => {
    if (currentPartIndex === 0 && questionListId) {
      // Only clear if we are cleanly mounting the first question (not navigating back/forth)
      // For safety, we could check if it's the very first part of the first question
      localStorage.removeItem(`summary_sessions_${questionListId}`);
    }
  }, [currentPartIndex, questionListId]);

  // Debug log for recordingStage changes - REMOVED
  // useEffect(() => {
  //   console.log(`[TIMING] recordingStage changed to: ${recordingStage}`);
  // }, [recordingStage]);

  // State for grading result
  const [gradingResult, setGradingResult] = useState<GradingResultResponse | null>(null);

  // State for answer data (to get graph_answer image)
  const [currentAnswer, setCurrentAnswer] = useState<Answer | null>(null);

  // State for summary generation loading
  const [isGeneratingReport, setIsGeneratingReport] = useState(false);

  // Ref that mirrors isAnswerFetched - needed because callbacks capture stale state
  const isAnswerFetchedRef = useRef(false);

  // Ref to track if grading has completed (success or failure)
  const isGradingCompletedRef = useRef(false);

  // Ref to track pending grading result while waiting for answer
  const pendingGradingResult = useRef<GradingResultResponse | null>(null);

  // Fetch answer for current question when entering evaluating stage
  useEffect(() => {
    if (!currentQuestion?.id || transcriptionRecorder.recordingStage !== "evaluating") {
      return;
    }

    // Reset refs and state for new evaluation
    isAnswerFetchedRef.current = false;
    isGradingCompletedRef.current = false;
    pendingGradingResult.current = null;
    setCurrentAnswer(null);

    const controller = new AbortController();

    fetchAnswers([currentQuestion.id], controller.signal)
      .then((answers) => {
        if (answers.length > 0) {
          setCurrentAnswer(answers[0]);
        }
        isAnswerFetchedRef.current = true;

        // If grading already completed, now transition to successful
        if (isGradingCompletedRef.current) {
          if (pendingGradingResult.current) {
            setGradingResult(pendingGradingResult.current);
          }
          transcriptionRecorder.markCompleted();
          updateCurrentPartState({
            recordingStage: "successful",
          });
        }
      })
      .catch((err) => {
        if (!controller.signal.aborted) {
          console.error("Failed to fetch answer:", err);
        }
        isAnswerFetchedRef.current = true;

        // Even if answer fails, proceed with grading if ready
        if (isGradingCompletedRef.current) {
          if (pendingGradingResult.current) {
            setGradingResult(pendingGradingResult.current);
          }
          transcriptionRecorder.markCompleted();
          updateCurrentPartState({
            recordingStage: "successful",
          });
        }
      });

    return () => controller.abort();
  }, [currentQuestion?.id, transcriptionRecorder.recordingStage]);

  // Poll for grading feedback when in "evaluating" stage
  useGradingFeedback({
    sessionId: transcriptionRecorder.sessionId,
    enabled: transcriptionRecorder.recordingStage === "evaluating",
    intervalMs: 2000,
    onComplete: (result) => {
      isGradingCompletedRef.current = true;
      pendingGradingResult.current = result;

      // If answer is already fetched, transition immediately
      if (isAnswerFetchedRef.current) {
        setGradingResult(result);
        transcriptionRecorder.markCompleted();
        updateCurrentPartState({
          recordingStage: "successful",
        });
      }
      // Otherwise, answer fetch will check isGradingCompletedRef and trigger transition
    },
    onError: (err) => {
      console.error("Grading failed:", err);
      isGradingCompletedRef.current = true;
      pendingGradingResult.current = null;

      // If answer is already fetched, transition immediately
      if (isAnswerFetchedRef.current) {
        transcriptionRecorder.markCompleted();
        updateCurrentPartState({
          recordingStage: "successful",
        });
      }
      // Otherwise, answer fetch will check isGradingCompletedRef and trigger transition
    },
  });

  // Save session ID to localStorage when a part is successfully completed
  useEffect(() => {
    if (recordingStage === "successful" && sessionId && questionListId) {
      const key = `summary_sessions_${questionListId}`;
      const existingSessions: string[] = JSON.parse(localStorage.getItem(key) || '[]');

      // Avoid duplicates
      if (!existingSessions.includes(sessionId)) {
        const updatedSessions = [...existingSessions, sessionId];
        localStorage.setItem(key, JSON.stringify(updatedSessions));
        console.log("Saved session ID for summary:", sessionId);
      }
    }
  }, [recordingStage, sessionId, questionListId]);

  // Build answer image URL
  const answerImageUrl = currentAnswer?.graph_answer_url
    ? `${API_BASE_URL}${currentAnswer.graph_answer_url}`
    : null;

  /**
   * Start recording - uses transcription recorder hook
   */
  const handleRecord = useCallback(async () => {
    // Clear any previous errors first
    setError(null);
    
    // Track if we should update UI - only set to true after everything succeeds
    let recordingStarted = false;
    
    try {
      // First, explicitly request permission before doing anything else
      // This ensures we don't start any recording process if permission is denied
      console.log("[handleRecord] Requesting microphone permission...");
      const hasPermission = await audioRecorder.requestPermission();
      console.log("[handleRecord] Permission result:", hasPermission);
      
      if (!hasPermission) {
        console.log("[handleRecord] Permission denied, aborting");
        setError("Microphone permission denied. Please allow microphone access and try again.");
        return; // Exit early - don't start recording
      }

      // Start recording via transcription recorder
      // This handles session creation and starting recording
      console.log("[handleRecord] Starting transcription recorder...");
      await transcriptionRecorder.startRecording();
      console.log("[handleRecord] Recording started successfully");

      // Mark that recording actually started
      recordingStarted = true;
      
      // Only update UI state AFTER startRecording completes successfully
      updateCurrentPartState({
        isRecording: true,
        recordingStage: "recording",
      });
    } catch (err) {
      console.error("[handleRecord] Error:", err);
      // Recording failed - ensure UI shows ready state
      if (!recordingStarted) {
        updateCurrentPartState({
          isRecording: false,
          recordingStage: "ready",
        });
      }
    }
  }, [transcriptionRecorder, audioRecorder, updateCurrentPartState, setError]);

  /**
   * Stop recording and process transcription
   */
  const handleStopRecording = useCallback(async () => {
    try {
      // Update UI state
      updateCurrentPartState({
        isRecording: false,
        recordingStage: "uploading",
      });

      // Stop recording via transcription recorder - it handles everything
      await transcriptionRecorder.stopRecording();

      // Success handling is done by the hook's onComplete callback
    } catch (err) {
      console.error("Error stopping recording:", err);
      // Error handling is done by the hook's onError callback
    }
  }, [transcriptionRecorder, updateCurrentPartState]);

  /**
   * Handle submit (same as stop recording for now)
   */
  const handleSubmit = useCallback(async () => {
    await handleStopRecording();
  }, [handleStopRecording]);

  /**
   * Handle retry - reset recording state and allow re-recording
   * Called when recording was too short (less than 5 seconds)
   */
  const handleRetry = useCallback(() => {
    // Reset the transcription recorder (clears session, error, etc.)
    transcriptionRecorder.reset();
    
    // Clear any error messages
    setError(null);
    
    // Reset the current part state to allow fresh recording
    updateCurrentPartState({
      isRecording: false,
      recordingStage: "ready",
      sessionId: null,
      transcriptionResult: null,
    });
  }, [transcriptionRecorder, setError, updateCurrentPartState]);

  // Save session ID for summary generation
  useEffect(() => {
    if (transcriptionRecorder.recordingStage === "successful" && transcriptionRecorder.sessionId && questionListId) {
      const key = `summary_sessions_${questionListId}`;
      try {
        const stored = JSON.parse(localStorage.getItem(key) || '[]');
        if (!stored.includes(transcriptionRecorder.sessionId)) {
          const updated = [...stored, transcriptionRecorder.sessionId];
          localStorage.setItem(key, JSON.stringify(updated));
          console.log("Saved session ID for summary:", transcriptionRecorder.sessionId);
        }
      } catch (e) {
        console.error("Failed to save session ID to localStorage", e);
      }
    }
  }, [transcriptionRecorder.recordingStage, transcriptionRecorder.sessionId, questionListId]);

  // Timer count up for recording (using current part config) - moved here after handleStopRecording is defined
  useEffect(() => {
    // Clear any existing record timer first
    if (recordTimerRef.current) {
      clearTimeout(recordTimerRef.current);
      recordTimerRef.current = null;
    }

    if (currentQuestion && isRecording && recordTime < currentQuestion.record_time_limit_seconds) {
      recordTimerRef.current = setTimeout(() => {
        // Use functional update to avoid dependency on recordTime
        updateCurrentPartState((prev) => ({ recordTime: (prev?.recordTime || 0) + 1 }));
        recordTimerRef.current = null;
      }, 1000);
    } else if (currentQuestion && isRecording && recordTime >= currentQuestion.record_time_limit_seconds && recordingStage === "recording") {
      // Recording time ended, automatically stop recording
      // Only stop if we're actually recording (not already stopping)
      handleStopRecording();
    }

    return () => {
      if (recordTimerRef.current) {
        clearTimeout(recordTimerRef.current);
        recordTimerRef.current = null;
      }
    };
  }, [isRecording, recordTime, currentQuestion, partStateKey, recordingStage, handleStopRecording, updateCurrentPartState]); // Keep recordTime for the condition check, but use functional update

  // Loading state - MUST be after all hooks
  if (loading) {
    return (
      <div className="bg-white w-full min-h-screen flex flex-col items-center justify-center">
        <Loader2Icon className="w-12 h-12 text-[#0053FA] animate-spin mb-4" />
        <p className="text-gray-600">Loading questions...</p>
      </div>
    );
  }

  // Error state (for loading errors) - MUST be after all hooks
  if (error && !currentQuestion) {
    return (
      <div className="bg-white w-full min-h-screen flex flex-col items-center justify-center">
        <h1 className="text-2xl font-semibold text-gray-800 mb-4">Error Loading Questions</h1>
        <p className="text-red-500 mb-6">{error}</p>
        <div className="flex gap-4">
          <Button
            onClick={() => window.location.reload()}
            variant="secondary"
            className="bg-[#e6eeff] hover:bg-[#e6eeff]/80 text-[#1e386d]"
          >
            Retry
          </Button>
          <Button
            onClick={() => {
              if (questionListId) {
                localStorage.removeItem(`summary_sessions_${questionListId}`);
              }
              navigate("/");
            }}
            className="bg-[#0053FA] hover:bg-[#0053FA]/90 text-white"
          >
            Return to Menu
          </Button>
        </div>
      </div>
    );
  }

  // If question not found or invalid index - MUST be after all hooks
  if (!currentQuestion || currentPartIndex < 0 || currentPartIndex >= questions.length) {
    return (
      <div className="bg-white w-full min-h-screen flex flex-col items-center justify-center">
        <h1 className="text-2xl font-semibold text-gray-800 mb-4">Question not found</h1>
        <p className="text-gray-600 mb-6">
          The question you're looking for doesn't exist in this list.
        </p>
        <Button
          onClick={() => {
            if (questionListId) {
              localStorage.removeItem(`summary_sessions_${questionListId}`);
            }
            navigate("/");
          }}
          className="bg-[#0053FA] hover:bg-[#0053FA]/90 text-white"
        >
          Return to Menu
        </Button>
      </div>
    );
  }

  // Convert API question to QuestionPart format for compatibility with existing components
  const currentPart: QuestionPart = {
    partId: String(currentPartIndex + 1), // Convert 0-based index to 1-based string
    partLabel: `(${String.fromCharCode(97 + currentPartIndex)})`, // a, b, c, d...
    title: currentQuestion.title,
    questionDetails: currentQuestion.question_details,
    questionDetailsMath: undefined, // Not in backend schema yet
    instructions: currentQuestion.instructions,
    thinkTimeLimit: currentQuestion.think_time_limit_seconds,
    recordTimeLimit: currentQuestion.record_time_limit_seconds,
    hint: currentQuestion.hints[0]?.text || "",
    feedback: {
      overallMessage: "Well done!",
      sections: [],
      sampleSolutionImage: ""
    },
    isPlottingQuestion: currentQuestion.topics.includes("Graph Plotting" as any), // Derived from topics
  };


  // Handle final report generation
  const handleGenerateReport = async () => {
    if (!questionListId) return;

    try {
      setIsGeneratingReport(true);

      // Record session end time for duration calculation
      const endTimeKey = `question_session_end_${questionListId}`;
      sessionStorage.setItem(endTimeKey, Date.now().toString());

      // Get session IDs from localStorage
      const key = `summary_sessions_${questionListId}`;
      const sessionIds = JSON.parse(localStorage.getItem(key) || '[]');

      if (sessionIds.length === 0) {
        // Fallback: if no sessions found, just navigate (SummaryReport handles partial data)
        navigate(`/question/${questionListId}/summary_report`);
        return;
      }

      console.log("Generating summary for sessions:", sessionIds);

      // Call createSummary API
      const response = await createSummary(sessionIds);
      const summaryId = response.summary_id;

      // Poll for completion
      const POLL_INTERVAL = 2000;
      let status = "processing";

      while (status === "processing" || status === "pending") {
        await new Promise(resolve => setTimeout(resolve, POLL_INTERVAL));
        const statusRes = await getSummaryStatus(summaryId);
        status = statusRes.status;

        if (status === "failed") {
          throw new Error(statusRes.message || "Summary generation failed");
        }
      }

      // Fetch the final result
      const summaryResult = await getSummaryResult(summaryId);

      // Navigate to summary report with summaryId and the result object
      navigate(`/question/${questionListId}/summary_report?summaryId=${summaryId}`, {
        state: { summaryResult }
      });

    } catch (err) {
      console.error("Failed to start summary generation:", err);
      setError("Failed to start summary generation. Please try again.");
      setIsGeneratingReport(false);
    }
  };

  return (
    <div className="bg-white w-full min-h-screen flex flex-col relative">
      {/* Blue Header - same height as QuestionMenu (70px) */}
      <header className="w-full h-[60px] 2xl:h-[70px] bg-[#0053FA] flex items-center justify-between px-4 sm:px-6 md:px-8 relative">
        {/* Left side: Logo and Timer */}
        <div className="flex items-center gap-3 md:gap-4 flex-shrink-0">
          {/* Menu Icon - Click to go back to menu */}
          <Button variant="ghost" size="icon" className="w-20 md:w-[132px] h-12 p-0 hover:bg-white/20 flex-shrink-0">
            <img src="/MemoryBun-landscape-white.png" alt="MemoryBun" className="w-20 md:w-[132px] h-auto" onClick={() => navigate("/")} />
          </Button>

          {/* Timer (left side) - Preparation only */}
          <PrepTimer
            time={prepTime}
            isExceeded={isPrepTimeExceeded}
            isPaused={isPrepTimerPaused}
            onTogglePause={() => {
              updateCurrentPartState({ isPrepTimerPaused: !isPrepTimerPaused });
            }}
          />
        </div>

        {/* Title (centered) */}
        <h1 className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 text-white font-semibold text-xl 2xl:text-2xl whitespace-nowrap">
          {questionList?.title || `Question List ${questionListId}`}
        </h1>

        {/* Avatar */}
        <Avatar className="w-12 h-12 flex-shrink-0">
          <AvatarFallback className="bg-gradient-to-br from-blue-400 to-purple-500 text-white font-semibold">P</AvatarFallback>
        </Avatar>
      </header>

      {/* Main Content */}
      <div className="flex flex-1 relative">
        {/* Left Sidebar */}
        <QuestionSidebar
          questionId={String(questionListId)}
          questionSet={{
            id: questionListId,
            category: currentQuestion.topics[0] || "Unknown",
            displayName: `Question ${currentPartIndex + 1}`,
            parts: questions.map((q, idx) => ({
              partId: String(idx + 1),
              partLabel: `(${String.fromCharCode(97 + idx)})`,
              title: q.title,
              questionDetails: q.question_details,
              instructions: q.instructions,
              thinkTimeLimit: q.think_time_limit_seconds,
              recordTimeLimit: q.record_time_limit_seconds,
              hint: q.hints[0]?.text || "",
              feedback: { overallMessage: "", sections: [], sampleSolutionImage: "" },
              isPlottingQuestion: q.topics.includes("Graph Plotting" as any),
            }))
          }}
          currentPart={currentPart}
          completedUpToIndex={completedUpToIndex}
          onRecord={handleRecord}
          recordTime={recordTime}
          recordingStage={recordingStage}
          onSubmit={handleSubmit}
          onStopRecording={handleStopRecording}
          onRetry={handleRetry}
          isSupported={audioRecorder.isSupported}
          error={audioRecorder.error || error}
        />

        {/* Drawing Board - canvas data persisted per part */}
        <DrawingBoard
          ref={drawingBoardRef}
          key={`${questionListId}-${currentPartIndex}`}
          currentPart={currentPart}
          currentQuestion={currentQuestion}
          showHint={isPrepTimeExceeded}
          showFeedback={recordingStage === "successful"}
          savedCanvasData={currentState.canvasData}
          onSaveCanvas={(canvasData) => updateCurrentPartState({ canvasData })}
          isFinalQuestion={currentPartIndex === questions.length - 1}
          onGenerateFinalReport={handleGenerateReport}
          isGeneratingReport={isGeneratingReport}
          gradingResult={gradingResult}
          answerImageUrl={answerImageUrl}
          readOnly={recordingStage === "successful"}
        />
      </div>

    </div>
  );
};
