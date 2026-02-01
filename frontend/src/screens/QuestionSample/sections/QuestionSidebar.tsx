import { Lock, LockOpen, CheckCircle } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Separator } from "../../../components/ui/separator";
import "katex/dist/katex.min.css";
import { QuestionSet, QuestionPart, getPartIndex } from "../../../config/questions";
import { RecordingControls, RecordingStage } from "./RecordingControls";
import { renderTextWithMath } from "../../../lib/mathUtils";

interface QuestionSidebarProps {
  questionId: string;
  questionSet: QuestionSet;
  currentPart: QuestionPart;
  completedUpToIndex: number; // Highest index of completed parts (-1 if none)
  onRecord: () => void;
  recordTime: number;
  recordingStage: RecordingStage;
  onSubmit: () => void;
  onStopRecording: () => void;
  onRetry?: () => void;
  isSupported?: boolean;
  error?: string | null;
}

// Helper function to format seconds into human-readable time
const formatTimeHuman = (seconds: number): string => {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;

  if (mins === 0) {
    return `${secs} seconds`;
  } else if (secs === 0) {
    return mins === 1 ? `${mins} minute` : `${mins} minutes`;
  } else {
    const minText = mins === 1 ? `${mins} minute` : `${mins} minutes`;
    return `${minText} ${secs} seconds`;
  }
};

// Helper function to replace time placeholders in instructions
const replaceTimePlaceholders = (text: string, thinkTime: number, recordTime: number): string => {
  return text
    .replace(/{thinkTime}/g, formatTimeHuman(thinkTime))
    .replace(/{recordTime}/g, formatTimeHuman(recordTime));
};

// Determine the state of each part
type PartState = "completed" | "active" | "unlocked" | "locked";

export const QuestionSidebar = ({
  questionId,
  questionSet,
  currentPart,
  completedUpToIndex,
  onRecord,
  recordTime,
  recordingStage,
  onSubmit,
  onStopRecording,
  onRetry,
  isSupported = true,
  error = null,
}: QuestionSidebarProps): JSX.Element => {
  const navigate = useNavigate();
  const currentPartIndex = getPartIndex(questionSet, currentPart.partId);

  // Determine state for each part
  // Logic:
  // - Current part is "active"
  // - Parts at or below completedUpToIndex are "completed" (can revisit)
  // - Next part after current is "unlocked" ONLY when current part just succeeded
  // - Everything else is "locked"
  const getPartState = (partIndex: number): PartState => {
    // Current part is always "active"
    if (partIndex === currentPartIndex) {
      return "active";
    }

    // Parts that have been completed (at or below completedUpToIndex)
    if (partIndex <= completedUpToIndex) {
      return "completed";
    }

    // Next part after CURRENT is "unlocked" only when current part succeeded
    if (partIndex === currentPartIndex + 1 && recordingStage === "successful") {
      return "unlocked";
    }

    // Everything else is locked
    return "locked";
  };

  // Handle click on a part
  const handlePartClick = (part: QuestionPart, state: PartState) => {
    if (state === "completed" || state === "unlocked") {
      navigate(`/question/${questionId}/${part.partId}`);
    }
  };

  return (
    <aside className="w-[clamp(350px,25vw,450px)] bg-white shadow-lg flex flex-col p-[clamp(1rem,2vw,2rem)] overflow-y-auto border-r border-gray-200">
      {/* Render ALL parts */}
      {questionSet.parts.map((part, index) => {
        const state = getPartState(index);

        return (
          <div key={part.partId}>
            {/* Separator before each part except first */}
            {index > 0 && <Separator className="my-3 bg-[#D9D9D9]" />}

            {/* COMPLETED PART - Collapsed with checkmark */}
            {state === "completed" && (
              <div
                className="flex items-center gap-3 cursor-pointer hover:bg-gray-50 -mx-2 px-2 py-1 rounded-lg transition-colors"
                onClick={() => handlePartClick(part, state)}
              >
                <CheckCircle className="w-5 h-5 2xl:w-6 2xl:h-6 text-green-600" />
                <div className="flex-1">
                  <h3 className="text-base 2xl:text-lg font-semibold text-gray-600">
                    {part.partLabel} {part.questionDetails ? renderTextWithMath(part.questionDetails) : part.title}
                  </h3>
                </div>
              </div>
            )}

            {/* ACTIVE PART - Expanded with details + RecordingControls */}
            {state === "active" && (
              <div>
                {/* Title */}
                <h2 className="text-xl 2xl:text-2xl font-semibold text-black mb-3 2xl:mb-4">
                  {part.partLabel} {part.title}
                </h2>

                {/* Question Details */}
                {part.questionDetails && (
                  <p className="text-base 2xl:text-lg text-black leading-relaxed mb-3 2xl:mb-4 font-semibold">
                    {renderTextWithMath(part.questionDetails)}
                  </p>
                )}

                {/* Instructions */}
                {part.instructions.map((instruction, instrIndex) => {
                  const instructionWithTime = replaceTimePlaceholders(instruction, part.thinkTimeLimit, part.recordTimeLimit);
                  return (
                    <p key={instrIndex} className="text-base 2xl:text-lg text-black leading-relaxed mb-6 2xl:mb-8">
                      {renderTextWithMath(instructionWithTime)}
                    </p>
                  );
                })}

                {/* Recording Controls */}
                <RecordingControls
                  recordingStage={recordingStage}
                  recordTime={recordTime}
                  maxRecordTime={part.recordTimeLimit}
                  onRecord={onRecord}
                  onStopRecording={onStopRecording}
                  onSubmit={onSubmit}
                  onRetry={onRetry}
                  isSupported={isSupported}
                  error={error}
                />
              </div>
            )}

            {/* UNLOCKED PART - Clickable with lock-open icon */}
            {state === "unlocked" && (
              <div
                className="flex items-center gap-3 cursor-pointer hover:bg-blue-50 -mx-2 px-2 py-1 rounded-lg transition-colors"
                onClick={() => handlePartClick(part, state)}
              >
                <LockOpen className="w-5 h-5 2xl:w-6 2xl:h-6 text-[#1e386d]" />
                <h3 className="text-lg 2xl:text-xl font-bold text-black">
                  {part.partLabel} {part.title}
                </h3>
              </div>
            )}

            {/* LOCKED PART - Not clickable with lock icon */}
            {state === "locked" && (
              <div className="flex items-center gap-3">
                <Lock className="w-5 h-5 2xl:w-6 2xl:h-6 text-[#B3B3B3]" />
                <h3 className="text-lg 2xl:text-xl font-bold text-[#979797]">
                  {part.partLabel} {part.title}
                </h3>
              </div>
            )}
          </div>
        );
      })}
    </aside>
  );
};
