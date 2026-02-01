/**
 * Recording configuration
 * 
 * Centralized configuration for audio recording behavior,
 * including minimum duration requirements and dev mode settings.
 */

/**
 * Minimum recording duration in seconds
 * Recordings shorter than this will be rejected and require retry
 * Set to 0 to disable minimum duration check
 * 
 * Default: 5 seconds (production)
 * Can be overridden via VITE_MIN_RECORDING_DURATION env var
 */
export const MIN_RECORDING_DURATION = parseInt(
  (import.meta as any).env?.VITE_MIN_RECORDING_DURATION || "5",
  10
);

/**
 * Development mode flag
 * When true, bypasses minimum recording duration check
 * This allows faster testing without waiting for minimum duration
 * 
 * Default: false (enforces minimum duration)
 * Can be overridden via VITE_DEV_MODE env var
 * 
 * IMPORTANT: 
 * - VITE_DEV_MODE="true" → DEV_MODE=true → Bypass minimum duration
 * - VITE_DEV_MODE="false" (or not set) → DEV_MODE=false → Enforce 5s minimum
 */
export const DEV_MODE = (import.meta as any).env?.VITE_DEV_MODE === "true";

// Add debug logging (remove after testing)
if (typeof window !== 'undefined') {
  console.log('🔧 Recording Config:', {
    MIN_RECORDING_DURATION,
    DEV_MODE,
    VITE_DEV_MODE: (import.meta as any).env?.VITE_DEV_MODE
  });
}

/**
 * Check if a recording duration meets the minimum requirement
 * Takes dev mode into account
 * 
 * @param durationSeconds - Recording duration in seconds
 * @returns true if recording is acceptable, false if too short
 */
export function isRecordingDurationValid(durationSeconds: number): boolean {
  // In dev mode, bypass minimum duration check
  if (DEV_MODE) {
    return true;
  }

  // No minimum duration configured, accept any recording
  if (MIN_RECORDING_DURATION === 0) {
    return true;
  }

  // Check if recording meets minimum duration
  return durationSeconds >= MIN_RECORDING_DURATION;
}

/**
 * Get a user-friendly error message for recordings that are too short
 * 
 * @returns Error message string
 */
export function getRecordingTooShortMessage(): string {
  const required = MIN_RECORDING_DURATION;
  
  return `The recording needs to be at least ${required} seconds long. Please try again.`;
}

