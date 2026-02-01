import { useState, useEffect } from "react";
import { useParams, useNavigate, useSearchParams, useLocation } from "react-router-dom";
import { Avatar, AvatarFallback } from "../../components/ui/avatar";
import { Button } from "../../components/ui/button";
import { SessionOverview, PerformanceSummary, FeedbackByQuestions, StrengthsAndImprovements } from "./sections";
import { fetchQuestionLists, fetchQuestionsInList, fetchAnswers } from "../../services/api";
import { getSummaryStatus, getSummaryResult, getGradingResult } from "../../services/gradingApi";
import { QuestionListMetadata, Question, Answer, SummaryResultResponse, GradingResultResponse } from "../../types/api";
import { Loader2Icon, Sparkles } from "lucide-react";

// Weights for overall score calculation
const DIMENSION_WEIGHTS: Record<string, number> = {
  "Problem Framing": 0.25,
  "Solution Execution": 0.25,
  "Technical Correctness": 0.25,
  "Communication & Whiteboard Use": 0.15,
  "Time Management": 0.10,
};

export const SummaryReport = (): JSX.Element => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const summaryId = searchParams.get("summaryId");
  const questionListId = id ? Number(id) : null;

  const [questionList, setQuestionList] = useState<QuestionListMetadata | null>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [answers, setAnswers] = useState<Answer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Summary state
  const location = useLocation();
  const [summaryResult, setSummaryResult] = useState<SummaryResultResponse | null>(location.state?.summaryResult || null);
  const [isGeneratingSummary, setIsGeneratingSummary] = useState(false);

  // Per-question grading results (feedback for each question)
  const [gradingResults, setGradingResults] = useState<GradingResultResponse[]>([]);

  // Poll for summary status if summaryId is present
  useEffect(() => {
    if (!summaryId) return;
    if (summaryResult) return; // Skip if we already have the result (e.g. passed via navigation state)

    const POLL_INTERVAL_MS = 2000;
    let isMounted = true;
    let pollInterval: any;

    const checkStatus = async () => {
      try {
        setIsGeneratingSummary(true);
        const statusRes = await getSummaryStatus(summaryId);

        if (statusRes.status === "completed") {
          const result = await getSummaryResult(summaryId);
          if (isMounted) {
            setSummaryResult(result);
            setIsGeneratingSummary(false);
          }
        } else if (statusRes.status === "failed") {
          console.error("Summary generation failed:", statusRes.message);
          if (isMounted) setIsGeneratingSummary(false);
        } else {
          // Still processing, poll again
          pollInterval = setTimeout(checkStatus, POLL_INTERVAL_MS);
        }
      } catch (err) {
        console.error("Error polling summary status:", err);
        if (isMounted) setIsGeneratingSummary(false);
      }
    };

    checkStatus();

    return () => {
      isMounted = false;
      if (pollInterval) clearTimeout(pollInterval);
    };
  }, [summaryId]);

  useEffect(() => {
    if (!questionListId) {
      setError("Invalid question list ID");
      setLoading(false);
      return;
    }

    const abortController = new AbortController();
    let isMounted = true;

    const loadData = async () => {
      try {
        setLoading(true);
        setError(null);

        // Fetch question list metadata
        const questionLists = await fetchQuestionLists(abortController.signal);
        if (!isMounted) return;
        const currentList = questionLists.find(list => list.id === questionListId);
        if (!currentList) {
          throw new Error(`Question list ${questionListId} not found`);
        }
        setQuestionList(currentList);

        // Fetch questions in the list
        const questionsData = await fetchQuestionsInList(questionListId, abortController.signal);
        if (!isMounted) return;
        setQuestions(questionsData);

        // Fetch answers for all questions
        const questionIds = questionsData.map(q => q.id);
        if (questionIds.length > 0) {
          const answersData = await fetchAnswers(questionIds, abortController.signal);
          if (!isMounted) return;
          setAnswers(answersData);
        }
      } catch (err) {
        if (!isMounted || abortController.signal.aborted) return;
        setError(err instanceof Error ? err.message : "Failed to load data");
      } finally {
        if (isMounted && !abortController.signal.aborted) {
          setLoading(false);
        }
      }
    };

    loadData();

    return () => {
      isMounted = false;
      abortController.abort();
    };
  }, [questionListId]);

  // Fetch grading results for each session (per-question feedback)
  useEffect(() => {
    if (!questionListId) return;

    const key = `summary_sessions_${questionListId}`;
    const sessionIds: string[] = JSON.parse(localStorage.getItem(key) || '[]');

    if (sessionIds.length === 0) return;

    let isMounted = true;

    const fetchGradingResults = async () => {
      try {
        const results = await Promise.all(
          sessionIds.map(async (sessionId) => {
            try {
              return await getGradingResult(sessionId);
            } catch {
              console.warn(`Failed to fetch grading result for ${sessionId}`);
              return null;
            }
          })
        );

        if (isMounted) {
          setGradingResults(results.filter((r): r is GradingResultResponse => r !== null));
        }
      } catch (err) {
        console.error("Failed to fetch grading results:", err);
      }
    };

    fetchGradingResults();

    return () => {
      isMounted = false;
    };
  }, [questionListId]);

  if (loading) {
    return (
      <div className="bg-[#F8FAFC] w-full min-h-screen flex flex-col items-center justify-center">
        <Loader2Icon className="w-12 h-12 text-[#0053FA] animate-spin mb-4" />
        <p className="text-gray-600">Loading summary report...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-[#F8FAFC] w-full min-h-screen flex flex-col items-center justify-center">
        <h1 className="text-2xl font-semibold text-gray-800 mb-4">Error Loading Report</h1>
        <p className="text-red-500 mb-6">{error}</p>
      </div>
    );
  }

  return (
    <div className="bg-[#F8FAFC] w-full min-h-screen flex flex-col">
      {/* Header - Consistent with QuestionSample */}
      <header className="w-full h-[60px] 2xl:h-[70px] bg-[#0053FA] flex items-center justify-between px-4 sm:px-6 md:px-8 relative">
        {/* Logo - Left */}
        <Button variant="ghost" size="icon" className="w-20 md:w-[132px] h-12 p-0 hover:bg-white/20">
          <img src="/MemoryBun-landscape-white.png" alt="MemoryBun" className="w-20 md:w-[132px] h-auto" onClick={() => navigate("/")} />
        </Button>

        {/* Title - Center */}
        <h1 className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 text-white font-semibold text-xl 2xl:text-2xl whitespace-nowrap">
          {questionList?.title ? `${questionList.title} : Summary Report` : "Summary Report"}
        </h1>

        {/* Avatar - Right */}
        <Avatar className="w-10 h-10 md:w-12 md:h-12">
          <AvatarFallback className="bg-gradient-to-br from-blue-400 to-purple-500 text-white font-semibold">
            P
          </AvatarFallback>
        </Avatar>
      </header>

      {/* Main Content - Two Column Layout */}
      <main className="flex-1 flex flex-col lg:flex-row items-start lg:items-stretch gap-4 p-4 md:p-8">
        {/* Left Panel */}
        <div className="w-[340px] 2xl:w-[420px] flex flex-col gap-4">
          <SessionOverview
            questionListDifficulty={questionList?.difficulty || null}
            questionListId={questionListId}
          />
          <PerformanceSummary
            summaryResult={summaryResult}
            gradingResults={gradingResults}
            weights={DIMENSION_WEIGHTS}
          />
        </div>

        {/* Right Panel */}
        <div className="flex-1 flex flex-col gap-4">
          <FeedbackByQuestions questions={questions} answers={answers} summaryResult={summaryResult} gradingResults={gradingResults} />
          <StrengthsAndImprovements summaryResult={summaryResult} />
        </div>
      </main>

      <div className="h-px bg-gray-200 my-3" />

      {/* Action Buttons */}
      <div className="flex justify-end gap-3 p-4 md:p-8">
        <button className="bg-[#0053FA] text-white px-6 py-2 rounded-full font-medium text-sm 2xl:text-base hover:bg-[#0046d4] transition-colors"
          onClick={() => {
            // Clear duration timestamps for replay
            if (questionListId) {
              sessionStorage.removeItem(`question_session_start_${questionListId}`);
              sessionStorage.removeItem(`question_session_end_${questionListId}`);
            }
            navigate(`/question/${questionListId}`);
          }}
        >
          Replay Session
        </button>
        <button
          className="bg-white text-[#0053FA] border-2 border-[#0053FA] px-6 py-2 rounded-full font-medium text-sm 2xl:text-base hover:bg-[#f0f5ff] transition-colors"
          onClick={() => {
            // Clear session IDs for this question list to avoid stale data
            if (questionListId) {
              localStorage.removeItem(`summary_sessions_${questionListId}`);
              // Clear duration timestamps
              sessionStorage.removeItem(`question_session_start_${questionListId}`);
              sessionStorage.removeItem(`question_session_end_${questionListId}`);
            }
            navigate("/");
          }}
        >
          Start New Mock
        </button>
      </div>
    </div>
  );
};

