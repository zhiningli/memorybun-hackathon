# QuestionSample Page Architecture

The `QuestionSample` page is the core interview practice screen where students answer questions with:
- 🎙️ **Real-time audio recording** with Whisper AI transcription
- 🎨 **Interactive drawing board** with screenshot capabilities
- 🤖 **AI-powered grading** using LLM (Gemini/OpenAI)
- 📊 **Multi-criteria feedback** based on rubrics
- ⏱️ **Smart timers** for prep and recording phases

This document describes the complete architecture and data flow from recording to AI feedback.

## Overview

```
┌───────────────────────────────────────────────────────────────────┐
│                      QuestionSample.tsx                            │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                      Custom Hooks Layer                        │ │
│  │                                                                │ │
│  │  Data Loading:                    State Management:           │ │
│  │  ┌──────────────────┐             ┌────────────────┐          │ │
│  │  │useQuestionListData│             │  usePartState  │          │ │
│  │  │   (fetch Q&A)    │             │ (timers/state) │          │ │
│  │  └──────────────────┘             └────────────────┘          │ │
│  │                                                                │ │
│  │  Recording Flow:                  Grading Flow:               │ │
│  │  ┌──────────────────────────┐    ┌────────────────────┐      │ │
│  │  │useTranscriptionRecorder  │    │useGradingFeedback  │      │ │
│  │  │  (Whisper AI)            │───▶│  (LLM Grading)     │      │ │
│  │  │  ┌────────────────────┐  │    │  - Poll status     │      │ │
│  │  │  │  useAudioRecorder  │  │    │  - Get result      │      │ │
│  │  │  │ (MediaRecorder)    │  │    │  - Score breakdown │      │ │
│  │  │  └────────────────────┘  │    └────────────────────┘      │ │
│  │  └──────────────────────────┘                                 │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                    │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                      UI Components Layer                       │ │
│  │  ┌──────────────────┐         ┌──────────────────────────┐    │ │
│  │  │ QuestionSidebar  │         │     DrawingBoard         │    │ │
│  │  │                  │         │                          │    │ │
│  │  │ ┌──────────────┐ │         │ ┌──────────────────────┐ │    │ │
│  │  │ │ PrepTimer    │ │         │ │ DrawingToolbar       │ │    │ │
│  │  │ └──────────────┘ │         │ │ (pen, eraser, clear) │ │    │ │
│  │  │ ┌──────────────┐ │         │ └──────────────────────┘ │    │ │
│  │  │ │RecordingCtls │ │         │ ┌──────────────────────┐ │    │ │
│  │  │ │(mic button)  │ │         │ │   PlotGrid/Canvas    │ │    │ │
│  │  │ └──────────────┘ │         │ │   (html2canvas)      │ │    │ │
│  │  │ ┌──────────────┐ │         │ └──────────────────────┘ │    │ │
│  │  │ │     Hint     │ │         │ ┌──────────────────────┐ │    │ │
│  │  │ └──────────────┘ │         │ │  Feedback Overlay    │ │    │ │
│  │  └──────────────────┘         │ │  (AI grading result) │ │    │ │
│  │                                │ └──────────────────────┘ │    │ │
│  │                                └──────────────────────────┘    │ │
│  └───────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────┘
```

## Custom Hooks

### 1. `useQuestionListData` (`hooks/useQuestionListData.ts`)

Handles loading question data from the backend.

**Responsibilities:**
- URL parsing (`questionListId`, `currentPartIndex`, `partStateKey`)
- Fetching questions via `fetchQuestionsInList()`
- Fetching question list metadata via `fetchQuestionLists()`
- Session start time tracking in sessionStorage
- Loading and error state management
- Cleanup via AbortController on unmount

**Returns:**
```typescript
{
  questionListId: number;
  currentPartIndex: number;
  partStateKey: string;
  questions: APIQuestion[];
  questionList: QuestionListMetadata | null;
  currentQuestion: APIQuestion | undefined;
  loading: boolean;
  error: string | null;
  setError: (error: string | null) => void;
}
```

---

### 2. `usePartState` (`hooks/usePartState.ts`)

Manages per-part state and timers.

**Responsibilities:**
- Per-part state management (prepTime, recordTime, isRecording, recordingStage, canvasData, etc.)
- Prep timer effect (counts up during preparation phase)
- Timer refs (prep, record) and timeout refs (upload, evaluate)
- Abort controller for transcription API
- Completion tracking (`completedUpToIndex`)
- State updates via `updateCurrentPartState`
- Cleanup and reset when `questionListId` changes

**Returns:**
```typescript
{
  // State
  partStates: Record<string, PartState>;
  currentState: PartState;
  prepTime, recordTime, isRecording, recordingStage: ...;
  completedUpToIndex: number;
  isPrepTimeExceeded: boolean;
  
  // Refs
  prepTimerRef, recordTimerRef: MutableRefObject<...>;
  transcriptionAbortControllerRef: MutableRefObject<AbortController | null>;
  
  // Helpers
  updateCurrentPartState: (updates) => void;
  clearAllTimeouts: () => void;
}
```

---

### 3. `useTranscriptionRecorder` (`hooks/useTranscriptionRecorder.ts`)

Orchestrates the full transcription recording flow.

**Responsibilities:**
- Uses `useAudioRecorder` internally
- Creates transcription sessions via API
- Streams audio chunks to backend during recording
- Polls for chunk processing status
- Finalizes session and retrieves transcription result
- Provides status, progress, and error information to UI

**Parameters:**
```typescript
{
  questionId?: string;
  studentId?: string;
  model?: "tiny" | "base" | "small" | "medium" | "large";
  onComplete?: (transcription: string) => void;
  onError?: (error: TranscriptionError) => void;
}
```

**Returns:**
```typescript
{
  // Status
  status: TranscriptionStatus;  // idle, requesting_permission, ready, creating_session, recording, uploading, processing, completed, error
  recordingStage: RecordingStage;  // Compatible with RecordingControls
  isRecording: boolean;
  
  // Progress
  sessionId: string | null;
  chunks: ChunkProgress[];
  transcriptionResult: string | null;
  
  // Error handling
  error: TranscriptionError | null;
  hasPermission: boolean;
  isSupported: boolean;
  
  // Actions
  requestPermission: () => Promise<boolean>;
  startRecording: () => Promise<void>;
  stopRecording: () => Promise<void>;
  reset: () => void;
  
  // Internal access
  audioRecorder: UseAudioRecorderReturn;
}
```

---

### 4. `useGradingFeedback` (`hooks/useGradingFeedback.ts`)

Manages AI grading workflow with polling.

**Responsibilities:**
- Polls grading service for status updates
- Retrieves grading results when complete
- Manages grading state transitions
- Error handling for grading failures
- Provides real-time progress updates

**Parameters:**
```typescript
{
  sessionId?: string;           // Transcription session ID
  autoStart?: boolean;          // Start polling automatically
  pollInterval?: number;        // Polling interval (default: 2000ms)
  maxAttempts?: number;         // Max polling attempts (default: 60)
  onComplete?: (result: GradingResultResponse) => void;
  onError?: (error: Error) => void;
}
```

**Returns:**
```typescript
{
  // Status
  status: GradingStatus;        // pending, grading, completed, failed
  isLoading: boolean;
  isPolling: boolean;
  
  // Results
  gradingResult: GradingResultResponse | null;
  score: number | null;
  feedback: string | null;
  rubricScores: RubricScore[] | null;
  
  // Error handling
  error: Error | null;
  
  // Actions
  startGrading: () => void;
  reset: () => void;
}
```

**Grading Flow:**
1. Session is finalized after transcription complete
2. Grading service automatically triggered
3. Hook polls `/api/v1/grading/session/:id/status` every 2s
4. Status transitions: `pending` → `grading` → `completed`/`failed`
5. When `completed`, fetches full result from `/api/v1/grading/session/:id/result`
6. Result includes: overall score, rubric breakdown, detailed feedback

---

### 5. `useAudioRecorder` (`hooks/useAudioRecorder.ts`)

Low-level hook for MediaRecorder API.

**Responsibilities:**
- Manages MediaRecorder lifecycle
- Requests microphone permissions
- Records audio in chunks (configurable timeslice)
- Stores chunks as Blobs
- Provides access to current chunks via `getChunks()`

**Returns:**
```typescript
{
  isRecording: boolean;
  chunks: Blob[];
  isSupported: boolean;
  permissionStatus: PermissionState | "unknown";
  error: string | null;
  
  startRecording: () => Promise<void>;
  stopRecording: () => void;
  reset: () => void;
  requestPermission: () => Promise<boolean>;
  getChunks: () => Blob[];  // Returns ref for latest chunks
}
```

---

## UI Components

### `QuestionSidebar` (`sections/QuestionSidebar.tsx`)

**Left sidebar containing question navigation and controls.**

**Features:**
- Question part selector (numbered buttons)
- Question content display (title, instructions)
- Prep timer display
- Recording controls integration
- Hint toggle button
- Progress indicators

**Props:**
- `questionSet`, `currentPart`, `completedUpToIndex`
- `prepTime`, `recordTime`, `recordingStage`
- `onRecord`, `onStopRecording`, `onSubmit`
- `showHint`, `onToggleHint`
- `isSupported`, `error`

---

### `PrepTimer` (`sections/PrepTimer.tsx`)

**Displays preparation time before recording.**

**Features:**
- Counts up during prep phase
- Visual indicator when prep time exceeded
- Formatted time display (MM:SS)

**Props:**
- `prepTime`: Current prep time in seconds
- `maxPrepTime`: Maximum allowed prep time
- `isPrepTimeExceeded`: Whether time limit exceeded

---

### `RecordingControls` (`sections/RecordingControls.tsx`)

**Recording interface with microphone button and status.**

**Features:**
- Record/Stop button (state-dependent styling)
- Recording time display with progress bar
- Status indicators (uploading, evaluating)
- Error display
- Submit button after successful recording

**Props:**
- `recordingStage`: Current stage (`ready`, `recording`, `uploading`, `evaluating`, `successful`)
- `recordTime`, `maxRecordTime`
- `onRecord`, `onStopRecording`, `onSubmit`
- `isSupported`, `error`

**Recording Stages:**
| Stage | Button | Display |
|-------|--------|---------|
| `ready` | Record (🎙️) | Ready to record |
| `recording` | Stop (⏹️) | Timer + progress bar |
| `uploading` | Disabled | "Uploading..." + spinner |
| `evaluating` | Disabled | "Evaluating..." + spinner |
| `successful` | Submit (✓) | "Next" button enabled |

---

### `DrawingBoard` (`sections/DrawingBoard.tsx`)

**Main canvas area for drawing, plotting, and visual feedback.**

**Features:**
- HTML5 Canvas with drawing tools
- Drawing toolbar integration
- Plot grid for mathematical functions
- Screenshot capture with html2canvas
- Hint overlay (after prep time exceeded)
- AI feedback overlay with grading results

**Props:**
- `currentPart`, `currentQuestion`
- `showHint`, `showFeedback`
- `savedCanvasData`, `onSaveCanvas`
- `isFinalQuestion`, `onGenerateFinalReport`
- `gradingResult`: AI grading response with scores
- `answerImageUrl`: Sample solution image URL

**Screenshot Flow:**
1. User finishes recording
2. Component captures canvas via html2canvas
3. Screenshot sent to transcription service
4. Grading service receives both transcription + screenshot
5. LLM evaluates answer with visual context

---

### `DrawingToolbar` (`sections/DrawingToolbar.tsx`)

**Toolbar for canvas drawing tools.**

**Features:**
- Pen tool with color picker
- Eraser tool
- Clear canvas button
- Tool selection state
- Responsive layout

**Props:**
- `activeTool`: Currently selected tool (`pen`, `eraser`)
- `onSelectTool`: Tool change handler
- `onClearCanvas`: Clear canvas handler
- `penColor`, `onColorChange`: Color selection

---

### `PlotGrid` (`sections/PlotGrid.tsx`)

**Mathematical plot grid overlay for canvas.**

**Features:**
- Grid lines for X/Y axes
- Axis labels
- Coordinate system
- SVG-based rendering
- Responsive sizing

**Props:**
- `width`, `height`: Canvas dimensions
- `gridSize`: Spacing between grid lines
- `showAxes`: Whether to show axes
- `axisColor`, `gridColor`: Styling options

---

### `Hint` (`sections/Hint.tsx`)

**Collapsible hint display.**

**Features:**
- Expandable/collapsible interface
- LaTeX rendering for math content
- Appears after prep time exceeded
- Smooth transitions

**Props:**
- `hintText`: Hint content (supports LaTeX)
- `isVisible`: Whether hint is shown
- `onToggle`: Toggle handler

---

## Complete Data Flow

### Phase 1: Preparation
```
Page loads
    │
    ▼
useQuestionListData fetches questions
    │
    ▼
usePartState initializes timers
    │
    ▼
Prep timer starts counting
    │
    ▼
User draws on canvas, reviews question
```

### Phase 2: Recording & Transcription
```
User clicks "Record"
       │
       ▼
QuestionSample.handleRecord()
       │
       ├──► Captures canvas screenshot (html2canvas)
       │
       ▼
transcriptionRecorder.startRecording()
       │
       ├──► POST /api/v1/transcribe/session
       │    (Creates session with questionId)
       │
       ├──► Starts MediaRecorder (WebM/Opus)
       │
       └──► Updates recordingStage: "recording"
       
       │ (Recording in progress...)
       │
       ▼
Audio chunks stream to backend
       │
       ├──► POST /api/v1/transcribe/session/:id/audio/chunk
       │    (Every 3 seconds during recording)
       │
       └──► Whisper AI processes chunks in parallel
       
User clicks "Stop" (or max time reached)
       │
       ▼
QuestionSample.handleStopRecording()
       │
       ▼
transcriptionRecorder.stopRecording()
       │
       ├──► Stops MediaRecorder
       │
       ├──► recordingStage: "uploading"
       │
       ├──► Uploads remaining chunks
       │
       ├──► POST screenshot to session
       │    POST /api/v1/transcribe/session/:id/screenshot
       │
       ├──► recordingStage: "processing"
       │
       ├──► Polls chunk status
       │    GET /api/v1/transcribe/session/:id/audio/chunk/:idx/status
       │
       ├──► POST /api/v1/transcribe/session/:id/audio/finalize
       │    (Triggers grading pipeline)
       │
       └──► GET /api/v1/transcribe/session/:id/audio
            (Returns full transcription)
       
       │
       ▼
onComplete callback updates UI
       │
       └──► Transcription displayed in UI
```

### Phase 3: AI Grading
```
Session finalized (triggers grading)
       │
       ▼
useGradingFeedback starts polling
       │
       ├──► Grading Service receives:
       │    - Transcription text
       │    - Screenshot image
       │    - Question context
       │    - Rubric criteria
       │
       ▼
Poll grading status (every 2s)
       │
       ├──► GET /api/v1/grading/session/:id/status
       │    Response: { status: "pending" | "grading" | "completed" }
       │
       └──► recordingStage: "evaluating"
       
       │ (LLM processes answer...)
       │
       ▼
Status becomes "completed"
       │
       ▼
Fetch full grading result
       │
       ├──► GET /api/v1/grading/session/:id/result
       │    Response: {
       │      score: number,
       │      feedback: string,
       │      rubric_scores: [
       │        { criterion: string, score: number, feedback: string }
       │      ]
       │    }
       │
       └──► recordingStage: "successful"
       
       │
       ▼
Display feedback overlay
       │
       ├──► Overall score displayed
       ├──► Rubric breakdown shown
       ├──► Detailed feedback rendered
       └──► Sample solution image shown
       
       │
       ▼
User clicks "Next" or "Generate Report"
```

### Phase 4: Navigation & Summary
```
If more parts exist:
    │
    ├──► Navigate to next part
    ├──► Preserve current part state
    └──► Reset timers for next part

If final part completed:
    │
    ├──► Collect all session IDs
    │
    ├──► POST /api/v1/grading/summarize
    │    (Generate overall summary)
    │
    ├──► Poll summary status
    │
    ├──► GET /api/v1/grading/summary/:id/result
    │
    └──► Navigate to /summary_report
```

### Microservices Interaction
```
┌──────────────┐     ┌────────────────┐     ┌──────────────┐
│   Frontend   │────▶│  Transcription │────▶│   Grading    │
│              │     │    Service     │     │   Service    │
│              │     │  (Whisper AI)  │     │  (LLM/GPT)   │
└──────────────┘     └────────────────┘     └──────────────┘
       │                     │                      │
       │                     │                      │
       ▼                     ▼                      ▼
┌──────────────┐     ┌────────────────┐     ┌──────────────┐
│   Question   │     │     Redis      │     │   Question   │
│   Service    │     │  (Task Queue)  │     │   Service    │
│  (Questions) │     │                │     │  (Rubrics)   │
└──────────────┘     └────────────────┘     └──────────────┘
```

## Recording Stages

The recording flow progresses through distinct stages, each with specific UI states and backend interactions:

| Stage | Description | Backend Activity | UI State |
|-------|-------------|------------------|----------|
| `idle` | Initial state | None | Prep timer visible |
| `ready` | Permission granted, ready to record | None | Record button (🎙️) enabled |
| `recording` | MediaRecorder active | Streaming chunks to transcription service | Stop button (⏹️) + timer + progress bar |
| `uploading` | Recording stopped, sending final data | Uploading remaining chunks + screenshot | "Uploading..." + spinner |
| `processing` | Backend processing | Whisper transcribing audio chunks | "Processing..." + spinner |
| `evaluating` | Transcription complete, grading in progress | LLM analyzing transcription + screenshot | "Evaluating..." + spinner |
| `successful` | Grading complete | None | Feedback overlay + "Next" button |
| `error` | Something failed | None | Error message + retry option |

### Stage Transitions

```
idle ──[request permission]──▶ ready
                                 │
                                 │ [start recording]
                                 ▼
                              recording
                                 │
                                 │ [stop recording]
                                 ▼
                              uploading
                                 │
                                 │ [chunks uploaded]
                                 ▼
                              processing
                                 │
                                 │ [transcription complete]
                                 ▼
                              evaluating
                                 │
                                 │ [grading complete]
                                 ▼
                              successful
                                 
                     [error at any stage] ──▶ error
```

## File Structure

```
src/
├── screens/QuestionSample/
│   ├── QuestionSample.tsx       # Main component (orchestrates all hooks)
│   ├── index.ts                 # Barrel export
│   ├── README.md                # This file
│   └── sections/                # UI component sections
│       ├── index.ts             # Barrel export
│       ├── QuestionSidebar.tsx  # Left sidebar with question nav
│       ├── PrepTimer.tsx        # Preparation timer display
│       ├── RecordingControls.tsx # Microphone button & controls
│       ├── DrawingBoard.tsx     # Main canvas area
│       ├── DrawingToolbar.tsx   # Drawing tool selection
│       ├── PlotGrid.tsx         # Mathematical plot grid
│       └── Hint.tsx             # Collapsible hint display
│
├── hooks/
│   ├── useAudioRecorder.ts           # Low-level MediaRecorder API
│   ├── useTranscriptionRecorder.ts   # Transcription orchestration
│   ├── useGradingFeedback.ts         # AI grading polling
│   ├── useQuestionListData.ts        # Question data loading
│   └── usePartState.ts               # Per-part state management
│
├── services/
│   ├── api.ts                   # Question Service API client
│   ├── transcriptionApi.ts      # Transcription Service API client
│   └── gradingApi.ts            # Grading Service API client
│
├── lib/
│   ├── mathUtils.tsx            # LaTeX rendering (KaTeX)
│   ├── utils.ts                 # General utilities (cn, classNames)
│   └── webmUtils.ts             # WebM audio processing
│
└── types/
    └── api.ts                   # TypeScript type definitions
```

### File Responsibilities

#### Main Component
- **QuestionSample.tsx**: Orchestrates all hooks, manages state flow, coordinates UI updates

#### Hooks (Business Logic)
- **useAudioRecorder**: WebRTC/MediaRecorder wrapper
- **useTranscriptionRecorder**: Manages session creation, chunk streaming, finalization
- **useGradingFeedback**: Polls grading status, retrieves results
- **useQuestionListData**: Fetches questions, answers, metadata from Question Service
- **usePartState**: Per-part state persistence, timer management

#### API Services (Network Layer)
- **api.ts**: Question lists, questions, answers
- **transcriptionApi.ts**: Session creation, chunk upload, screenshot upload
- **gradingApi.ts**: Status polling, result retrieval, summary generation

#### UI Components (Presentation)
- **QuestionSidebar**: Question navigation, instructions, controls
- **PrepTimer**: Countdown/countup timer display
- **RecordingControls**: Record/stop button with status
- **DrawingBoard**: Canvas container with feedback overlay
- **DrawingToolbar**: Tool selection UI
- **PlotGrid**: Mathematical grid overlay
- **Hint**: Collapsible hint with LaTeX support

## Key Design Decisions

### 1. **Layered Hook Architecture**
Separated concerns into focused, composable hooks:
- **Data layer**: `useQuestionListData` (fetching)
- **Recording layer**: `useAudioRecorder` → `useTranscriptionRecorder` (composition)
- **Grading layer**: `useGradingFeedback` (polling)
- **State layer**: `usePartState` (persistence)

**Benefits**: Testability, reusability, single responsibility

### 2. **Hook Composition Over Duplication**
`useTranscriptionRecorder` uses `useAudioRecorder` internally rather than duplicating MediaRecorder logic.

**Benefits**: DRY principle, easier maintenance, consistent behavior

### 3. **Callback-Based Communication**
Hooks use callbacks (`onComplete`, `onError`) to notify parent components.

**Benefits**: Keeps hooks UI-agnostic, easier to test, flexible integration

### 4. **Ref-Based State for Async Operations**
`getChunks()` returns current ref value instead of state to avoid stale closures.

**Benefits**: Always current data, no race conditions, works with async callbacks

### 5. **Per-Part State Persistence**
`usePartState` maintains state for ALL parts in a single object, keyed by part index.

**Benefits**: 
- Navigate between parts without losing progress
- Canvas drawings preserved
- Timer states maintained
- Can resume from any part

### 6. **Streaming Audio Upload**
Audio chunks sent to backend during recording (every 3s) rather than waiting until end.

**Benefits**:
- Lower latency (transcription starts immediately)
- Better UX (faster feedback)
- Handles long recordings (no memory issues)
- Parallel processing on backend

### 7. **Screenshot Integration**
Canvas captured as screenshot and sent with transcription for visual grading.

**Benefits**:
- LLM can evaluate diagrams/drawings
- More accurate grading for visual answers
- Context for mathematical work
- Richer feedback

### 8. **Polling with Exponential Backoff** (Considered)
Currently uses fixed 2s interval; could implement exponential backoff.

**Current**: Simple, predictable polling
**Future**: Reduce backend load for long-running tasks

### 9. **Microservices Architecture**
Frontend communicates with 3 separate services instead of monolithic backend.

**Benefits**:
- Independent scaling
- Technology flexibility (Python for ML, Node for API)
- Fault isolation
- Parallel development

### 10. **Type-Safe API Clients**
All API calls have TypeScript interfaces for requests and responses.

**Benefits**:
- Compile-time error catching
- IntelliSense/autocomplete
- Self-documenting code
- Refactoring safety

## AI Integration Details

### Whisper Transcription
- **Model**: Configurable (tiny/base/small/medium/large)
- **Default**: `base` (good balance of speed/accuracy)
- **Format**: WebM/Opus audio chunks
- **Chunk size**: 3 seconds
- **Processing**: Parallel processing of chunks on backend
- **Languages**: Supports multiple languages (auto-detect)

### LLM Grading
- **Providers**: Gemini (default) or OpenAI GPT
- **Input**: Transcription text + screenshot image + question context + rubric
- **Output**: Overall score (0-100) + per-criterion scores + detailed feedback
- **Rubric**: Multi-criteria evaluation (e.g., accuracy, clarity, depth, structure)
- **Prompt engineering**: Custom prompts per question type
- **Context window**: Full question + instructions + hint + student answer
- **Safety**: Rate limiting, timeout handling, retry logic

### Grading Rubric Structure
```typescript
{
  criterion: string;        // e.g., "Mathematical Accuracy"
  weight: number;           // e.g., 0.4 (40%)
  score: number;            // 0-100
  max_score: number;        // Usually 100
  feedback: string;         // Specific feedback for this criterion
}
```

## Performance Considerations

### Memory Management
- Audio chunks cleared after upload
- Canvas data stored as data URLs (efficient)
- State cleanup on unmount
- AbortControllers for request cancellation

### Network Optimization
- Chunked uploads reduce memory usage
- Parallel chunk processing
- Polling instead of WebSockets (simpler, works everywhere)
- Request cancellation on navigation

### UI Responsiveness
- Async operations don't block UI
- Loading states for all async operations
- Progress indicators during uploads
- Optimistic UI updates where safe

## Error Handling

### Error Types
1. **Permission Errors**: Microphone access denied
2. **Network Errors**: API request failures
3. **Processing Errors**: Transcription/grading failures
4. **Validation Errors**: Invalid input data
5. **Timeout Errors**: Backend processing too long

### Error Recovery
- Clear error messages to user
- Retry buttons for recoverable errors
- Graceful degradation (e.g., skip screenshot if fails)
- State preservation on error (don't lose progress)
- Logging for debugging

### User Feedback
- Toast notifications for non-critical errors
- Modal dialogs for critical errors
- Inline validation messages
- Status indicators during processing

## Testing Considerations

### Unit Tests (Recommended)
- Test each hook independently
- Mock API calls
- Test state transitions
- Test error handling

### Integration Tests (Recommended)
- Test hook composition
- Test complete recording flow
- Test grading flow
- Test navigation between parts

### E2E Tests (Recommended)
- Test complete user journey
- Test with real audio recording
- Test with real backend services
- Test error scenarios

## Future Enhancements

### Considered Features
- 🔄 **Offline support**: Cache questions for offline practice
- 📊 **Real-time feedback**: Show transcription as user speaks
- 🎯 **Adaptive difficulty**: Adjust question difficulty based on performance
- 🌍 **Multi-language**: Support for non-English questions
- 📱 **Mobile optimization**: Better touch controls for canvas
- 🎨 **Rich text editor**: Better formatting for written answers
- 🔊 **Audio playback**: Let user review their recorded answer
- 📈 **Progress tracking**: Show improvement over time
- 🤝 **Collaborative practice**: Practice with peers
- 🎓 **Tutor mode**: Connect with human tutors for help
