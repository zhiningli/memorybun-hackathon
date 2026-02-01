import { Calendar, CircleGauge, Clock } from 'lucide-react';
import { summaryReportConfig } from '../../../config/summaryReport';
import { QuestionListDifficulty } from '../../../types/api';

interface SessionOverviewProps {
  questionListDifficulty: QuestionListDifficulty | null;
  questionListId: number | null;
}

export const SessionOverview = ({ questionListDifficulty, questionListId }: SessionOverviewProps): JSX.Element => {
  const difficulty = questionListDifficulty || QuestionListDifficulty.MEDIUM;

  // Get current date and format it as "Month Day, Year"
  const currentDate = new Date();
  const formattedDate = currentDate.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });

  // Calculate duration from session start time
  const calculateDuration = (): string => {
    if (!questionListId) {
      return summaryReportConfig.sessionOverview.duration;
    }

    const sessionKey = `question_session_start_${questionListId}`;
    const startTimeStr = sessionStorage.getItem(sessionKey);

    if (!startTimeStr) {
      return summaryReportConfig.sessionOverview.duration;
    }

    const startTime = parseInt(startTimeStr, 10);

    const endTimeKey = `question_session_end_${questionListId}`;
    const endTimeStr = sessionStorage.getItem(endTimeKey);
    const endTime = endTimeStr ? parseInt(endTimeStr, 10) : Date.now();

    const durationMs = endTime - startTime;

    // Convert to minutes and seconds
    const totalSeconds = Math.floor(durationMs / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;

    return `${minutes}m ${seconds}s`;
  };

  const duration = calculateDuration();

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 2xl:p-6">
      {/* Header with icon */}
      <div className="flex items-center gap-2 mb-6">
        <h2 className="text-lg font-semibold text-black">
          Session Overview
        </h2>
      </div>

      {/* Data fields */}
      <div className="space-y-2">
        {/* Date */}
        <div className="bg-[#e6eeff80] rounded-lg p-2 2xl:p-3">
          <div className="flex items-start gap-3">
            <div className="w-5 h-5 flex items-center justify-center flex-shrink-0 mt-0.5">
              <Calendar className="w-4 h-4 2xl:w-5 2xl:h-5 text-gray-500" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-xs font-medium text-gray-600 mb-1">DATE</div>
              <div className="text-sm 2xl:text-base text-gray-900">{formattedDate}</div>
            </div>
          </div>
        </div>

        {/* Difficulty */}
        <div className="bg-[#e6eeff80] rounded-lg p-2 2xl:p-3">
          <div className="flex items-start gap-3">
            <div className="w-5 h-5 flex items-center justify-center flex-shrink-0 mt-0.5">
              <CircleGauge className="w-4 h-4 2xl:w-5 2xl:h-5 text-gray-500" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-xs font-medium text-gray-600 mb-1">DIFFICULTY</div>
              <div className="text-sm 2xl:text-base text-gray-900">{difficulty}</div>
            </div>
          </div>
        </div>

        {/* Duration */}
        <div className="bg-[#e6eeff80] rounded-lg p-2 2xl:p-3">
          <div className="flex items-start gap-3">
            <div className="w-5 h-5 flex items-center justify-center flex-shrink-0 mt-0.5">
              <Clock className="w-4 h-4 2xl:w-5 2xl:h-5 text-gray-500" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-xs font-medium text-gray-600 mb-1">DURATION</div>
              <div className="text-sm 2xl:text-base text-gray-900">{duration}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

