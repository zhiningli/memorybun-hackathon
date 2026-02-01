import { PenTool, Eraser, Shapes, MousePointer, Image, Type, Trash2 } from "lucide-react";

export type Tool = "pen" | "eraser" | "select" | "shape" | "image" | "text" | null;

interface DrawingToolbarProps {
  activeTool: Tool;
  onToolSelect: (tool: Tool) => void;
  onClearCanvas: () => void;
  readOnly?: boolean;
}

export const DrawingToolbar = ({ activeTool, onToolSelect, onClearCanvas, readOnly = false }: DrawingToolbarProps): JSX.Element | null => {
  if (readOnly) return null;

  return (
    <div className="absolute bottom-6 left-1/2 -translate-x-1/2 bg-white border border-gray-300 rounded-full shadow-lg px-4 py-3 flex items-center gap-5 pointer-events-auto z-20">
      {/* Pen Tool */}
      <button
        onClick={() => onToolSelect("pen")}
        className={`p-3 rounded-full transition-colors ${activeTool === "pen" ? "bg-[#0053FA] text-white" : "text-gray-700 hover:bg-gray-100"
          }`}
        title="Pen Tool"
      >
        <PenTool className="w-5 h-5" />
      </button>

      {/* Eraser Tool */}
      <button
        onClick={() => onToolSelect("eraser")}
        className={`p-3 rounded-full transition-colors ${activeTool === "eraser" ? "bg-[#0053FA] text-white" : "text-gray-700 hover:bg-gray-100"
          }`}
        title="Eraser"
      >
        <Eraser className="w-5 h-5" />
      </button>

      {/* Shape Tool (inactive for now) */}
      <button
        className="p-3 rounded-full text-gray-400 cursor-not-allowed"
        title="Shapes (Coming soon)"
        disabled
      >
        <Shapes className="w-5 h-5" />
      </button>

      {/* Select Tool (inactive for now) */}
      <button
        className="p-3 rounded-full text-gray-400 cursor-not-allowed"
        title="Select (Coming soon)"
        disabled
      >
        <MousePointer className="w-5 h-5" />
      </button>

      {/* Image Tool (inactive for now) */}
      <button
        className="p-3 rounded-full text-gray-400 cursor-not-allowed"
        title="Image (Coming soon)"
        disabled
      >
        <Image className="w-5 h-5" />
      </button>

      {/* Text Tool (inactive for now) */}
      <button
        className="p-3 rounded-full text-gray-400 cursor-not-allowed"
        title="Text (Coming soon)"
        disabled
      >
        <Type className="w-5 h-5" />
      </button>

      {/* Trash/Clear Tool */}
      <button
        onClick={onClearCanvas}
        className="p-3 rounded-full text-gray-700 hover:bg-gray-100 transition-colors"
        title="Clear Canvas"
      >
        <Trash2 className="w-5 h-5" />
      </button>
    </div>
  );
};

