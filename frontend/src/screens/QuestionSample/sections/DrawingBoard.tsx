import { useState, useEffect, useRef, forwardRef, useImperativeHandle } from "react";
import { MessageSquare, Minimize2, X } from "lucide-react";
import html2canvas from "html2canvas";
import { renderTextWithMath } from "../../../lib/mathUtils";
import { QuestionPart } from "../../../config/questions";
import { Question as APIQuestion, GradingResultResponse } from "../../../types/api";
import { PlotGrid } from "./PlotGrid";
import { DrawingToolbar, type Tool } from "./DrawingToolbar";
import { Hint } from "./Hint";
import { API_BASE_URL } from "../../../services/api";

interface DrawingBoardProps {
  currentPart: QuestionPart;
  currentQuestion?: APIQuestion; // Optional backend question data
  showHint: boolean;
  showFeedback: boolean;
  savedCanvasData: string | null;
  onSaveCanvas: (canvasData: string) => void;
  isFinalQuestion?: boolean; // Whether this is the final question in the list
  onGenerateFinalReport?: () => void; // Callback for generating final report
  isGeneratingReport?: boolean; // Whether report is currently being generated
  gradingResult?: GradingResultResponse | null; // AI grading result from backend
  answerImageUrl?: string | null; // URL to the sample solution/answer graph image
  readOnly?: boolean; // If true, disables drawing and hides toolbar
}

// Ref interface for external access to drawing board methods
export interface DrawingBoardRef {
  /** Capture the current whiteboard as a PNG Blob for screenshot upload */
  getScreenshotBlob: () => Promise<Blob | null>;
}

export const DrawingBoard = forwardRef<DrawingBoardRef, DrawingBoardProps>(({ currentPart, currentQuestion, showHint, showFeedback, savedCanvasData, onSaveCanvas, isFinalQuestion = false, onGenerateFinalReport, isGeneratingReport = false, gradingResult, answerImageUrl, readOnly = false }, ref): JSX.Element => {
  const [activeTool, setActiveTool] = useState<Tool>("pen");
  const [isDrawing, setIsDrawing] = useState(false);
  const [isFeedbackExpanded, setIsFeedbackExpanded] = useState(true); // Start expanded when feedback appears
  const [isImageModalOpen, setIsImageModalOpen] = useState(false); // Image lightbox modal

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const contextRef = useRef<CanvasRenderingContext2D | null>(null);
  const boardCaptureRef = useRef<HTMLDivElement>(null); // Wrapper for html2canvas capture

  // Helper function to create blob from canvas
  const canvasToBlob = (canvas: HTMLCanvasElement): Promise<Blob | null> => {
    return new Promise((resolve) => {
      canvas.toBlob((blob) => {
        resolve(blob);
      }, "image/png");
    });
  };

  // Fallback: capture just the drawing canvas with white background
  const captureDrawingOnly = async (): Promise<Blob | null> => {
    const drawingCanvas = canvasRef.current;
    if (!drawingCanvas) return null;

    console.log("Fallback: capturing drawing only");
    const fallbackCanvas = document.createElement("canvas");
    fallbackCanvas.width = drawingCanvas.width;
    fallbackCanvas.height = drawingCanvas.height;
    const ctx = fallbackCanvas.getContext("2d");
    if (!ctx) return null;

    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, fallbackCanvas.width, fallbackCanvas.height);
    ctx.drawImage(drawingCanvas, 0, 0);

    return canvasToBlob(fallbackCanvas);
  };

  // Expose getScreenshotBlob method via ref
  useImperativeHandle(ref, () => ({
    getScreenshotBlob: async (): Promise<Blob | null> => {
      const captureElement = boardCaptureRef.current;

      // If wrapper doesn't exist, use fallback
      if (!captureElement) {
        console.warn("Capture wrapper not found, using fallback");
        return captureDrawingOnly();
      }

      try {
        // Wait one animation frame to ensure rendering is settled
        await new Promise(resolve => requestAnimationFrame(resolve));

        // Use html2canvas to capture the entire board area

        const canvas = await html2canvas(captureElement, {
          useCORS: true,           // Enable CORS for cross-origin images
          allowTaint: false,       // Don't allow tainted canvas (ensures export works)
          backgroundColor: "#ffffff", // Set white background
          scale: 2,                // Higher quality capture
          logging: false,          // Disable logging in production
        });

        const blob = await canvasToBlob(canvas);
        if (blob) {

          return blob;
        }

        console.warn("html2canvas returned null blob, using fallback");
        return captureDrawingOnly();
      } catch (error) {
        console.error("html2canvas failed, using fallback:", error);
        return captureDrawingOnly();
      }
    },
  }));

  // Helper to save current canvas state
  const saveCanvasState = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const dataUrl = canvas.toDataURL('image/png');
    onSaveCanvas(dataUrl);
  };

  // Helper to restore canvas from saved data
  const restoreCanvasState = (dataUrl: string) => {
    const canvas = canvasRef.current;
    const context = contextRef.current;
    if (!canvas || !context) return;

    const img = new window.Image();
    img.onload = () => {
      context.drawImage(img, 0, 0);
    };
    img.src = dataUrl;
  };

  // Initialize and resize canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const setupCanvas = () => {
      const rect = canvas.getBoundingClientRect();
      // Set canvas internal resolution to match display size
      canvas.width = rect.width;
      canvas.height = rect.height;

      const context = canvas.getContext("2d");
      if (!context) return;

      context.lineCap = "round";
      context.lineJoin = "round";
      context.strokeStyle = "black";
      context.lineWidth = 2;
      contextRef.current = context;

      // Restore saved canvas data if available
      if (savedCanvasData) {
        restoreCanvasState(savedCanvasData);
      }
    };

    // Small delay to ensure parent is rendered
    setTimeout(setupCanvas, 100);

    // Re-setup on resize (but save first to preserve drawing)
    const handleResize = () => {
      saveCanvasState();
      setupCanvas();
    };
    window.addEventListener('resize', handleResize);

    // Save canvas when component unmounts
    return () => {
      saveCanvasState();
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  // Get scaled coordinates accounting for canvas resolution vs display size
  const getCanvasCoordinates = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return { x: 0, y: 0 };

    const rect = canvas.getBoundingClientRect();
    // Scale coordinates if canvas internal size differs from display size
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;

    const x = (e.clientX - rect.left) * scaleX;
    const y = (e.clientY - rect.top) * scaleY;

    return { x, y };
  };

  // Get scaled coordinates from touch events (for iPad finger/Apple Pencil support)
  const getTouchCoordinates = (e: React.TouchEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return { x: 0, y: 0 };

    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;

    // Use first touch point (or changedTouches for touchend)
    const touch = e.touches[0] || e.changedTouches[0];
    if (!touch) return { x: 0, y: 0 };

    const x = (touch.clientX - rect.left) * scaleX;
    const y = (touch.clientY - rect.top) * scaleY;

    return { x, y };
  };

  // Handle mouse down
  const startDrawing = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (readOnly) return; // Prevent drawing in read-only mode
    if (!activeTool || activeTool === "select" || activeTool === "shape" || activeTool === "image" || activeTool === "text") return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const { x, y } = getCanvasCoordinates(e);

    contextRef.current?.beginPath();
    contextRef.current?.moveTo(x, y);
    setIsDrawing(true);
  };

  // Handle mouse move
  const draw = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isDrawing || !contextRef.current) return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const { x, y } = getCanvasCoordinates(e);

    if (activeTool === "pen") {
      contextRef.current.globalCompositeOperation = "source-over";
      contextRef.current.strokeStyle = "black";
      contextRef.current.lineWidth = 2;
    } else if (activeTool === "eraser") {
      contextRef.current.globalCompositeOperation = "destination-out";
      contextRef.current.lineWidth = 20;
    }

    contextRef.current.lineTo(x, y);
    contextRef.current.stroke();
  };

  // Handle mouse up
  const stopDrawing = () => {
    contextRef.current?.closePath();
    setIsDrawing(false);
    // Save canvas after each stroke
    saveCanvasState();
  };

  // Handle touch start (for iPad finger/Apple Pencil support)
  const startDrawingTouch = (e: React.TouchEvent<HTMLCanvasElement>) => {
    e.preventDefault(); // Prevent scrolling while drawing
    if (readOnly) return;
    if (!activeTool || activeTool === "select" || activeTool === "shape" || activeTool === "image" || activeTool === "text") return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const { x, y } = getTouchCoordinates(e);

    contextRef.current?.beginPath();
    contextRef.current?.moveTo(x, y);
    setIsDrawing(true);
  };

  // Handle touch move (for iPad finger/Apple Pencil support)
  const drawTouch = (e: React.TouchEvent<HTMLCanvasElement>) => {
    e.preventDefault(); // Prevent scrolling while drawing
    if (!isDrawing || !contextRef.current) return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const { x, y } = getTouchCoordinates(e);

    if (activeTool === "pen") {
      contextRef.current.globalCompositeOperation = "source-over";
      contextRef.current.strokeStyle = "black";
      contextRef.current.lineWidth = 2;
    } else if (activeTool === "eraser") {
      contextRef.current.globalCompositeOperation = "destination-out";
      contextRef.current.lineWidth = 20;
    }

    contextRef.current.lineTo(x, y);
    contextRef.current.stroke();
  };

  // Handle touch end (for iPad finger/Apple Pencil support)
  const stopDrawingTouch = (e: React.TouchEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    contextRef.current?.closePath();
    setIsDrawing(false);
    // Save canvas after each stroke
    saveCanvasState();
  };

  // Clear canvas
  const clearCanvas = () => {
    const canvas = canvasRef.current;
    if (!canvas || !contextRef.current) return;

    contextRef.current.clearRect(0, 0, canvas.width, canvas.height);
    // Save cleared canvas
    saveCanvasState();
  };

  // Handle tool selection
  const selectTool = (tool: Tool) => {
    setActiveTool(tool);
  };

  return (
    <main className="flex-1 flex flex-col items-end justify-center p-8 md:p-16 lg:pr-18 xl:pr-38 relative border-2 border-gray-300 bg-white rounded-2xl m-4 md:m-6 lg:m-8 overflow-hidden">
      {/* Minimized Buttons Container - Top Left */}
      {/* Hint Component */}
      <Hint showHint={showHint} hint={currentPart.hint} />

      {/* Feedback Button (minimized) */}
      {showFeedback && !isFeedbackExpanded && (
        <div className="absolute top-4 left-4 z-20 pointer-events-auto">
          <button
            className="flex items-center gap-2 px-4 py-2 bg-[#E6EEFF] border border-gray-0 rounded-full shadow-sm hover:bg-[#d9e5ff] hover:border-gray-100 transition-all"
            onClick={() => setIsFeedbackExpanded(true)}
            title="Show Feedback"
          >
            <MessageSquare className="w-4 h-4 text-gray-900" />
            <span className="text-sm font-medium text-gray-900">Feedback</span>
          </button>
        </div>
      )}

      {/* Expanded Feedback Panel */}
      {showFeedback && isFeedbackExpanded && (
        <div className="absolute top-4 left-4 z-30 pointer-events-auto w-[450px] max-h-[calc(100%-32px)] flex flex-col bg-white rounded-xl shadow-2xl border border-gray-200 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-300">
          {/* Feedback Header */}
          <div className="px-5 pt-4 pb-3 flex items-center justify-between border-b border-gray-100 flex-shrink-0">
            <h3 className="text-xl font-semibold text-gray-900">Feedback</h3>
            <button
              onClick={() => setIsFeedbackExpanded(false)}
              className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors"
              title="Minimize"
            >
              <Minimize2 className="w-5 h-5 text-gray-500" />
            </button>
          </div>

          {/* Feedback Content */}
          <div className="px-5 py-4 overflow-y-auto flex-1 min-h-0">
            {/* Feedback Text - Split by \n\n to render paragraphs */}
            <div className="text-sm 2xl:text-base font-medium text-green-600 mb-4 space-y-3">
              {(gradingResult?.feedback || currentPart.feedback.overallMessage)
                .split('\n\n')
                .map((paragraph, index) => (
                  <p key={index}>{renderTextWithMath(paragraph.trim())}</p>
                ))}
            </div>

            {/* Sample Solution / Graph Answer */}
            <div className="mt-4 pt-4 border-t border-gray-200">
              <h4 className="text-sm font-semibold text-gray-900 mb-3">Sample Solution</h4>
              <div
                className={`w-full h-48 bg-gray-50 rounded-lg border border-gray-200 flex items-center justify-center overflow-hidden ${answerImageUrl ? 'cursor-pointer hover:border-blue-400 hover:shadow-md transition-all' : ''}`}
                onClick={() => answerImageUrl && setIsImageModalOpen(true)}
              >
                {answerImageUrl ? (
                  <img
                    crossOrigin="anonymous"
                    src={answerImageUrl}
                    alt="Sample Solution"
                    className="w-full h-full object-contain"
                    onError={(e) => {
                      // Fallback placeholder if image fails to load
                      (e.target as HTMLImageElement).style.display = 'none';
                      (e.target as HTMLImageElement).parentElement!.innerHTML = `
                        <div class="flex flex-col items-center justify-center text-gray-400">
                          <svg class="w-12 h-12 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
                          </svg>
                          <span class="text-sm">Sample solution image</span>
                        </div>
                      `;
                    }}
                  />
                ) : (
                  <div className="flex flex-col items-center justify-center text-gray-400">
                    <svg className="w-12 h-12 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
                    </svg>
                    <span className="text-sm">Sample solution image</span>
                  </div>
                )}
              </div>
              {answerImageUrl && (
                <p className="text-xs text-gray-500 mt-2 text-center">Click to enlarge</p>
              )}
            </div>

            {/* Generate Final Report Button - Only show on final question */}
            {isFinalQuestion && (
              <div className="mt-6 pt-4 border-t border-gray-200">
                <button
                  onClick={() => {
                    onGenerateFinalReport?.();
                  }}
                  disabled={isGeneratingReport}
                  className={`w-full font-semibold py-3 px-4 rounded-full transition-colors duration-200 shadow-md hover:shadow-lg flex items-center justify-center gap-2
                    ${isGeneratingReport
                      ? 'bg-blue-300 text-white cursor-not-allowed'
                      : 'bg-[#0053FA] hover:bg-[#0053FA]/90 text-white'
                    }`}
                >
                  {isGeneratingReport ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Generating...
                    </>
                  ) : (
                    "Generate Final Report"
                  )}
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Board Capture Area - wrapper for html2canvas screenshot */}
      <div
        ref={boardCaptureRef}
        className="absolute inset-0 w-full h-full"
        style={{ backgroundColor: 'white' }}
      >
        {/* Grid Container OR Question Image - z-0 (bottom layer), positioned right */}
        {currentQuestion?.question_image_url ? (
          // Show question image if available (e.g., container diagram, circuit diagram)
          <div className="absolute inset-0 flex items-center justify-end pr-8 pointer-events-none z-0">
            <img
              crossOrigin="anonymous"
              src={`${API_BASE_URL}${currentQuestion.question_image_url}`}
              alt="Question Diagram"
              className="max-w-[65%] max-h-[65%] object-contain"
              style={{ filter: 'none', colorScheme: 'light' }}
              onError={(e) => {
                console.error("Failed to load question image:", currentQuestion.question_image_url);
                (e.target as HTMLImageElement).style.display = 'none';
              }}
            />
          </div>
        ) : currentQuestion?.topics?.includes("Graph Plotting" as any) ? (
          // Show plot grid for plotting questions (when no question_image_url)
          <div className="absolute inset-0 flex items-center justify-end pr-8 pointer-events-none z-0">
            <PlotGrid />
          </div>
        ) : null}

        {/* Full Drawing Canvas Overlay - z-10 (top layer for drawing) */}
        <canvas
          ref={canvasRef}
          onMouseDown={startDrawing}
          onMouseMove={draw}
          onMouseUp={stopDrawing}
          onMouseLeave={stopDrawing}
          onTouchStart={startDrawingTouch}
          onTouchMove={drawTouch}
          onTouchEnd={stopDrawingTouch}
          className="absolute inset-0 w-full h-full cursor-crosshair z-10"
          style={{ touchAction: 'none' }}
        />
      </div>

      {/* Toolbar - Centered at bottom of large rectangle */}
      <DrawingToolbar
        activeTool={activeTool}
        onToolSelect={selectTool}
        onClearCanvas={clearCanvas}
        readOnly={readOnly}
      />

      {/* Image Modal / Lightbox */}
      {isImageModalOpen && answerImageUrl && (
        <div
          className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4"
          onClick={() => setIsImageModalOpen(false)}
        >
          {/* Close button */}
          <button
            onClick={() => setIsImageModalOpen(false)}
            className="absolute top-4 right-4 p-2 bg-white/10 hover:bg-white/20 rounded-full transition-colors z-10"
          >
            <X className="w-6 h-6 text-white" />
          </button>

          {/* Image container - scrollable for long images */}
          <div
            className="max-w-[100vw] max-h-[90vh] bg-white rounded-xl shadow-2xl p-4 overflow-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <img
              crossOrigin="anonymous"
              src={answerImageUrl}
              alt="Sample Solution"
              className="w-auto h-auto max-w-none"
              style={{ minWidth: '400px' }}
            />
          </div>
        </div>
      )}
    </main>
  );
});

