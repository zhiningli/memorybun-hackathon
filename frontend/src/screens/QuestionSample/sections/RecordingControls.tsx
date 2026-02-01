import { Loader, RotateCcw } from "lucide-react";
import { Button } from "../../../components/ui/button";

export type RecordingStage = "ready" | "recording" | "submit" | "uploading" | "evaluating" | "successful" | "too_short";

interface RecordingControlsProps {
  recordingStage: RecordingStage;
  recordTime: number;
  maxRecordTime: number;
  onRecord: () => void;
  onStopRecording: () => void;
  onSubmit: () => void;
  onRetry?: () => void;
  isSupported?: boolean;
  error?: string | null;
}

export const RecordingControls = ({
  recordingStage,
  recordTime,
  maxRecordTime,
  onRecord,
  onStopRecording,
  onSubmit,
  onRetry,
  isSupported = true,
  error = null,
}: RecordingControlsProps): JSX.Element => {
  const remainingTime = maxRecordTime - recordTime;
  const progressPercentage = (recordTime / maxRecordTime) * 100;

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
  };

  const getButtonContent = () => {
    switch (recordingStage) {
      case "ready":
        return "Record";
      case "recording":
        return (
          <span className="flex items-center gap-2">
            <span className="w-3 h-3 bg-red-500 rounded-full animate-pulse"></span>
            Recording...
          </span>
        );
      case "submit":
        return "Submit";
      case "uploading":
        return (
          <span className="flex items-center gap-2">
            <Loader className="w-5 h-5 animate-spin" />
            Uploading...
          </span>
        );
      case "evaluating":
        return (
          <span className="flex items-center gap-2">
            <Loader className="w-5 h-5 animate-spin" />
            Evaluating...
          </span>
        );
      case "successful":
        return "Successful";
      case "too_short":
        return (
          <span className="flex items-center gap-2">
            <RotateCcw className="w-5 h-5" />
            Retry
          </span>
        );
      default:
        return "Record";
    }
  };

  const handleButtonClick = () => {
    if (recordingStage === "ready") {
      onRecord();
    } else if (recordingStage === "recording") {
      onStopRecording();
    } else if (recordingStage === "submit") {
      onSubmit();
    } else if (recordingStage === "too_short") {
      onRetry?.();
    }
  };

  const isButtonDisabled =
    recordingStage === "uploading" ||
    recordingStage === "evaluating" ||
    recordingStage === "successful" ||
    !isSupported;
  const showProgressBar = recordingStage !== "ready";

  return (
    <div className="flex flex-col items-center w-full">
      {/* Error Message */}
      {error && (
        <div className="w-full mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-800">{error}</p>
          {!isSupported && (
            <p className="text-xs text-red-600 mt-1">
              Please use Chrome or a modern browser that supports audio recording.
            </p>
          )}
        </div>
      )}

      {/* Record Button */}
      <Button
        onClick={handleButtonClick}
        disabled={isButtonDisabled}
        className={`w-[190px] h-12 text-white font-semibold text-xl rounded-full shadow-lg mb-4 ${recordingStage === "successful"
          ? "bg-green-600 hover:bg-green-600"
          : recordingStage === "recording"
            ? "bg-red-600 hover:bg-red-600"
            : recordingStage === "too_short"
              ? "bg-[#EB6724] hover:bg-[#EB6724]/80"
              : "bg-[#0053FA]/90 hover:bg-[#0053FA]/80"
          }`}
      >
        {getButtonContent()}
      </Button>

      {/* Progress Bar with Countdown */}
      {showProgressBar && (
        <div className="w-full mb-2">
          <div className="relative w-full h-2 bg-gray-200 rounded-full overflow-hidden">
            {/* Filled progress */}
            <div
              className="absolute top-0 left-0 h-full bg-[#0053FA] transition-all duration-300 ease-linear"
              style={{ width: `${progressPercentage}%` }}
            />
          </div>
          {/* Countdown number at the end */}
          <div className="flex justify-end mt-2">
            <span className="text-base font-semibold text-[#0053FA]">
              {formatTime(remainingTime)}
            </span>
          </div>
        </div>
      )}
    </div>
  );
};

