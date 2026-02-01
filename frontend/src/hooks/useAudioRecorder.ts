/**
 * Custom React hook for audio recording using MediaRecorder API
 * 
 * Features:
 * - Request microphone permission
 * - Initialize MediaRecorder with WebM/Opus codec
 * - Auto-chunk audio every 30 seconds
 * - Handle recording start/stop
 * - Provide recording state (isRecording, chunks, errors)
 * - Cleanup on unmount
 */

import { useState, useRef, useCallback, useEffect } from "react";
import { extractInitSegment, prependInitSegment } from "../lib/webmUtils";

export type PermissionStatus = "prompt" | "granted" | "denied";

export interface UseAudioRecorderReturn {
  isRecording: boolean;
  isSupported: boolean;
  error: string | null;
  permissionStatus: PermissionStatus;
  requestPermission: () => Promise<boolean>; // Returns true if granted, false if denied
  startRecording: () => Promise<void>;
  stopRecording: () => void;
  chunks: Blob[];
  getChunks: () => Blob[]; // Get current chunks from ref (use in callbacks to avoid stale closures)
  reset: () => void;
}

// Recording timeslice in milliseconds - chunks will be generated at this interval
// Set to 90 seconds (90000ms) to balance between real-time processing and chunk size
const RECORDING_TIMESLICE_MS = 30000;

// Check if MediaRecorder is supported in the browser
const isMediaRecorderSupported = (): boolean => {
  return (
    typeof window !== "undefined" &&
    typeof MediaRecorder !== "undefined" &&
    MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
  );
};

// Get the best supported MIME type for MediaRecorder
const getSupportedMimeType = (): string | null => {
  const types = [
    "audio/webm;codecs=opus",
    "audio/webm",
  ];

  for (const type of types) {
    if (MediaRecorder.isTypeSupported(type)) {
      return type;
    }
  }

  return null;
};

/**
 * Custom hook for audio recording with automatic chunking
 * 
 * @returns Object containing recording state and control functions
 */
export function useAudioRecorder(): UseAudioRecorderReturn {
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [chunks, setChunks] = useState<Blob[]>([]);
  const [permissionStatus, setPermissionStatus] = useState<PermissionStatus>("prompt");

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  // Cache the WebM init segment (EBML header + Segment info + Tracks) from chunk 0
  // This is prepended to chunks 1+ to make them valid, parseable WebM files
  const initSegmentRef = useRef<ArrayBuffer | null>(null);

  // Check support lazily to avoid issues during SSR or module initialization
  const isSupported = useState(() => {
    try {
      return isMediaRecorderSupported();
    } catch {
      return false;
    }
  })[0];

  /**
   * Request microphone permission (without starting recording)
   */
  const requestPermission = useCallback(async (): Promise<boolean> => {
    try {
      if (!isSupported) {
        setError("Audio recording is not supported in this browser.");
        setPermissionStatus("denied");
        return false;
      }

      // Check current permission status
      if (navigator.permissions) {
        try {
          const permissionStatus = await navigator.permissions.query({ name: "microphone" as PermissionName });
          if (permissionStatus.state === "granted") {
            setPermissionStatus("granted");
            return true;
          }
          if (permissionStatus.state === "denied") {
            setPermissionStatus("denied");
            setError("Microphone permission denied. Please allow microphone access in your browser settings.");
            return false;
          }
        } catch (e) {
          // Permissions API not supported or failed, continue with getUserMedia
        }
      }

      // Request permission by getting user media (but don't keep the stream yet)
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      // Permission granted - stop the stream immediately (we'll get it again when recording starts)
      stream.getTracks().forEach(track => track.stop());

      setPermissionStatus("granted");
      setError(null);
      return true;
    } catch (err: any) {
      console.error("Error requesting microphone permission:", err);
      setPermissionStatus("denied");

      if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
        setError("Microphone permission denied. Please allow microphone access and try again.");
      } else if (err.name === "NotFoundError" || err.name === "DevicesNotFoundError") {
        setError("No microphone found. Please connect a microphone and try again.");
      } else {
        setError(err.message || "Failed to access microphone.");
      }
      return false;
    }
  }, [isSupported]);

  /**
   * Request microphone access and initialize MediaRecorder
   */
  const initializeMediaRecorder = useCallback(async (): Promise<MediaRecorder> => {
    // Request microphone access
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });

    streamRef.current = stream;
    setPermissionStatus("granted");

    // Get supported MIME type
    const mimeType = getSupportedMimeType();
    if (!mimeType) {
      throw new Error(
        "No supported audio format found. Please use Chrome or a modern browser."
      );
    }

    // Create MediaRecorder with 30-second timeslice for automatic chunking
    const mediaRecorder = new MediaRecorder(stream, {
      mimeType,
    });

    // Track ondataavailable event count for logging
    let dataEventCount = 0;

    // Handle dataavailable event - fires every RECORDING_TIMESLICE_MS, or when requestData() is called
    // For chunk 0: extract and cache init segment, store original blob
    // For chunk 1+: prepend cached init segment to make valid WebM
    mediaRecorder.ondataavailable = async (event: BlobEvent) => {
      dataEventCount++;
      const currentChunkIndex = chunksRef.current.length;

      if (event.data && event.data.size > 0) {
        try {
          let processedBlob: Blob;

          if (currentChunkIndex === 0) {
            // First chunk: extract and cache init segment
            console.log(`[Chunk #0] Extracting init segment from ${event.data.size} bytes`);
            initSegmentRef.current = await extractInitSegment(event.data);
            console.log(`[Chunk #0] Init segment cached: ${initSegmentRef.current.byteLength} bytes`);
            processedBlob = event.data;
          } else {
            // Subsequent chunks: prepend cached init segment
            if (!initSegmentRef.current) {
              console.error(`[Chunk #${currentChunkIndex}] Missing init segment, cannot process chunk`);
              return;
            }
            const originalSize = event.data.size;
            processedBlob = prependInitSegment(initSegmentRef.current, event.data);
            console.log(
              `[Chunk #${currentChunkIndex}] Prepended init segment: ${originalSize} -> ${processedBlob.size} bytes`
            );
          }

          chunksRef.current.push(processedBlob);
          setChunks([...chunksRef.current]);
        } catch (err) {
          console.error(`[Chunk #${currentChunkIndex}] Error processing chunk:`, err);
        }
      } else {
        console.warn(`[Event ${dataEventCount}] Received empty data (size: ${event.data?.size ?? 'null'}), not added to chunks`);
      }
    };

    // Handle errors
    mediaRecorder.onerror = (event: Event) => {
      const errorEvent = event as any; // MediaRecorderErrorEvent type may not be available in all environments
      setError(`Recording error: ${errorEvent.error?.message || "Unknown error"}`);
      console.error("MediaRecorder error:", errorEvent.error);
    };

    // Handle stop event - collect final chunk
    mediaRecorder.onstop = () => {
      // When stop() is called, request any remaining data
      // The final chunk will be delivered via ondataavailable before this handler runs
      console.log("MediaRecorder stopped. Total chunks:", chunksRef.current.length);

      // Clean up stream
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
      }
    };

    return mediaRecorder;
  }, []);

  /**
   * Start recording audio
   */
  const startRecording = useCallback(async () => {
    try {
      setError(null);
      chunksRef.current = [];
      setChunks([]);
      initSegmentRef.current = null; // Reset init segment cache for new recording

      if (!isSupported) {
        throw new Error(
          "MediaRecorder API is not supported in this browser. Please use Chrome or a modern browser."
        );
      }

      // Initialize MediaRecorder
      const mediaRecorder = await initializeMediaRecorder();
      mediaRecorderRef.current = mediaRecorder;

      // Start recording with 60-second timeslice for automatic chunking
      // This will trigger ondataavailable every 60 seconds
      mediaRecorder.start(RECORDING_TIMESLICE_MS);

      setIsRecording(true);
    } catch (err) {
      const errorMessage =
        err instanceof Error
          ? err.message
          : "Failed to start recording. Please check microphone permissions.";

      setError(errorMessage);
      setIsRecording(false);

      // Clean up on error
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
      }
      mediaRecorderRef.current = null;

      // Re-throw to allow caller to handle
      throw err;
    }
  }, [isSupported, initializeMediaRecorder]);

  // Track isRecording in a ref to avoid recreating stopRecording callback
  const isRecordingRef = useRef(isRecording);
  isRecordingRef.current = isRecording;

  /**
   * Stop recording audio
   */
  const stopRecording = useCallback(() => {
    // Use ref to access current isRecording state without dependency
    if (mediaRecorderRef.current && isRecordingRef.current) {
      try {
        // Request any remaining data before stopping
        // This ensures the final chunk is captured even if it's shorter than the timeslice
        if (mediaRecorderRef.current.state === "recording") {
          mediaRecorderRef.current.requestData(); // Force ondataavailable to fire with current buffer
          mediaRecorderRef.current.stop();
        }
      } catch (err) {
        console.error("Error stopping recording:", err);
        setError(
          err instanceof Error
            ? err.message
            : "Failed to stop recording properly"
        );
      } finally {
        setIsRecording(false);
        mediaRecorderRef.current = null;
      }
    }
  }, []); // Stable callback - uses refs to access state

  /**
   * Reset recording state and clear chunks
   */
  const reset = useCallback(() => {
    // Stop recording if active - use ref to check state
    if (mediaRecorderRef.current && isRecordingRef.current) {
      stopRecording();
    }

    // Clean up stream
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }

    // Clear state
    chunksRef.current = [];
    setChunks([]);
    setError(null);
    initSegmentRef.current = null; // Reset init segment cache
    setIsRecording(false);
    setPermissionStatus("prompt"); // Reset permission status
    mediaRecorderRef.current = null;
  }, [stopRecording]); // stopRecording is now stable

  /**
   * Get current chunks - use this to avoid stale closure issues
   * IMPORTANT: This must be defined BEFORE the cleanup useEffect to maintain hook order
   */
  const getChunks = useCallback(() => {
    return chunksRef.current;
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      // Stop recording if active - use ref for current state
      if (mediaRecorderRef.current && isRecordingRef.current) {
        try {
          if (mediaRecorderRef.current.state !== "inactive") {
            mediaRecorderRef.current.stop();
          }
        } catch (err) {
          console.error("Error stopping recording on unmount:", err);
        }
      }

      // Clean up stream
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
      }

      mediaRecorderRef.current = null;
    };
  }, []); // Empty deps - only run on mount/unmount

  return {
    isRecording,
    isSupported,
    error,
    permissionStatus,
    requestPermission,
    startRecording,
    stopRecording,
    chunks,
    getChunks, // Use this in callbacks to get current chunks
    reset,
  };
}

