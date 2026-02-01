import {
  CheckCircleIcon,
  CircleIcon,
  StarIcon,
  Loader2Icon,
} from "lucide-react";
import { Button } from "../../../components/ui/button";
import { QuestionListMetadata, QuestionListDifficulty } from "../../../types/api";

// Helper to format difficulty for display
const formatDifficulty = (difficulty: QuestionListDifficulty): string => {
  switch (difficulty) {
    case QuestionListDifficulty.EASY:
      return "Easy";
    case QuestionListDifficulty.MEDIUM:
      return "Med.";
    case QuestionListDifficulty.ADVANCED:
      return "Adv.";
    default:
      return difficulty;
  }
};

// Helper to format duration for display
const formatDuration = (seconds: number): string => {
  const minutes = Math.ceil(seconds / 60);
  return `${minutes} mins`;
};

interface QuestionListTableProps {
  rows: QuestionListMetadata[];
  completed: Record<number, boolean>;
  starred: Record<number, boolean>;
  onToggleCompleted: (id: number) => void;
  onToggleStarred: (id: number) => void;
  onRowClick: (id: number) => void;
  loading: boolean;
  error: string | null;
}

export const QuestionListTable = ({
  rows,
  completed,
  starred,
  onToggleCompleted,
  onToggleStarred,
  onRowClick,
  loading,
  error,
}: QuestionListTableProps): JSX.Element => {
  return (
    <div className="mt-6 min-w-[600px]">
      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <Loader2Icon className="w-8 h-8 text-[#0052f9] animate-spin" />
          <span className="ml-3 text-[#1e386d]">Loading question lists...</span>
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className="flex flex-col items-center justify-center py-12">
          <p className="text-red-500 mb-4">{error}</p>
          <Button
            onClick={() => window.location.reload()}
            variant="secondary"
            className="bg-[#e6eeff] hover:bg-[#e6eeff]/80 text-[#1e386d]"
          >
            Retry
          </Button>
        </div>
      )}

      {/* Table Header */}
      {!loading && !error && (
        <>
          <div className="grid grid-cols-[60px_1fr_200px_200px_100px_60px] 2xl:grid-cols-[80px_1fr_250px_250px_120px_80px] gap-4 items-center h-[38px] 2xl:h-[48px] mb-2 px-2">
            <div className="text-[#001d58] font-medium text-sm 2xl:text-base">Status</div>
            <div className="text-[#001d58] font-medium text-sm 2xl:text-base">Question</div>
            <div className="text-[#001d58] font-medium text-sm 2xl:text-base">Category</div>
            <div className="text-[#001d58] font-medium text-sm 2xl:text-base">Difficulty</div>
            <div className="text-[#001d58] font-medium text-sm 2xl:text-base">Duration</div>
            <div className="text-[#001d58] font-medium text-sm 2xl:text-base"></div>
          </div>

          {/* Empty State */}
          {rows.length === 0 && (
            <div className="flex items-center justify-center py-12">
              <p className="text-[#1e386d99]">No question lists available.</p>
            </div>
          )}

          {/* Table Rows */}
          <div className="flex flex-col gap-0">
            {rows.map((questionList, index) => (
              <div
                key={questionList.id}
                className={`grid grid-cols-[60px_1fr_200px_200px_100px_60px] 2xl:grid-cols-[80px_1fr_250px_250px_120px_80px] gap-4 items-center h-[38px] 2xl:h-[48px] rounded-[5px] px-2 ${index % 2 === 0 ? "bg-[#e6eeff80]" : "bg-white"
                  }`}
              >
                {/* Status Icon */}
                <div
                  className="cursor-pointer hover:opacity-70 transition-opacity flex items-center justify-center"
                  onClick={() => onToggleCompleted(questionList.id)}
                >
                  {completed[questionList.id] ? (
                    <CheckCircleIcon className="w-5 h-5 2xl:w-6 2xl:h-6 text-[#1e386d]" />
                  ) : (
                    <CircleIcon className="w-5 h-5 2xl:w-6 2xl:h-6 text-[#1e386d]" />
                  )}
                </div>

                {/* Question Title - Click to navigate */}
                <div
                  className="text-[#1e386d] text-sm 2xl:text-base truncate cursor-pointer hover:text-[#0052f9] hover:underline transition-colors"
                  onClick={() => onRowClick(questionList.id)}
                >
                  {questionList.title}
                </div>

                {/* Category */}
                <div className="text-[#1e386d] text-sm 2xl:text-base truncate">
                  {questionList.categories.join(", ")}
                </div>

                {/* Difficulty */}
                <div className="text-[#1e386d] text-sm 2xl:text-base">
                  {formatDifficulty(questionList.difficulty)}
                </div>

                {/* Duration */}
                <div className="text-[#1e386d] text-sm 2xl:text-base">
                  {formatDuration(questionList.duration_seconds)}
                </div>

                {/* Star Icon */}
                <div
                  className="cursor-pointer group flex items-center justify-center"
                  onClick={() => onToggleStarred(questionList.id)}
                >
                  {starred[questionList.id] ? (
                    <StarIcon className="w-5 h-5 2xl:w-6 2xl:h-6 text-[#1e386d] fill-[#1e386d] transition-opacity group-hover:opacity-70" />
                  ) : (
                    <StarIcon className="w-5 h-5 2xl:w-6 2xl:h-6 text-[#1e386d] fill-none opacity-0 group-hover:opacity-100 transition-opacity duration-200" />
                  )}
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
};

