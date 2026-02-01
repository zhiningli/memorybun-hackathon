// Preparation Timer Component - Displays countdown/count-up timer in header

import { Play, Pause } from 'lucide-react';

interface PrepTimerProps {
  time: number; // Time in seconds
  isExceeded: boolean; // Whether time limit has been exceeded
  isPaused: boolean; // Whether the timer is paused
  onTogglePause: () => void; // Callback to toggle pause state
}

// Format seconds into MM : SS display format
const formatTime = (seconds: number): string => {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${String(mins).padStart(2, "0")} : ${String(secs).padStart(2, "0")}`;
};

export const PrepTimer = ({ time, isExceeded, isPaused, onTogglePause }: PrepTimerProps): JSX.Element => {
  return (
    <div className="flex items-center">
      <div className="bg-white/35 backdrop-blur-sm px-4 2xl:px-5 py-1.5 2xl:py-2 rounded-full shadow-lg flex items-center gap-1">
        <button
          onClick={onTogglePause}
          className="flex items-center justify-center hover:bg-white/20 rounded-full p-1 transition-colors"
          aria-label={isPaused ? "Resume timer" : "Pause timer"}
        >
          {isPaused ? (
            <Play className="w-4 h-4 2xl:w-6 2xl:h-6 text-white fill-white" />
          ) : (
            <Pause className="w-4 h-4 2xl:w-6 2xl:h-6 text-white fill-white" />
          )}
        </button>
        <span className={`font-semibold text-xl 2xl:text-2xl tracking-wide transition-colors duration-300 ${
          isExceeded ? "text-red-600" : "text-white"
        }`}>
          {formatTime(time)}
        </span>
      </div>
    </div>
  );
};

