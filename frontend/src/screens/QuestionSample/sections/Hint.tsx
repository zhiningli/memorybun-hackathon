import { useState } from "react";
import { Lightbulb, Minimize2 } from "lucide-react";
import "katex/dist/katex.min.css";
import { renderTextWithMath } from "../../../lib/mathUtils";

interface HintProps {
  showHint: boolean;
  hint: string;
}

export const Hint = ({ showHint, hint }: HintProps): JSX.Element => {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!showHint) {
    return <></>;
  }

  return (
    <>
      {/* Hint Button (minimized) */}
      {!isExpanded && (
        <div className="absolute top-4 left-4 z-20 pointer-events-auto">
          <button
            className="flex items-center gap-2 px-4 py-2 bg-[#E6EEFF] border border-gray-0 rounded-full shadow-sm hover:bg-[#d9e5ff] hover:border-gray-100 transition-all"
            onClick={() => setIsExpanded(true)}
            title="Show Hint"
          >
            <Lightbulb className="w-4 h-4 text-gray-900" />
            <span className="text-sm font-medium text-gray-900">Hint</span>
          </button>
        </div>
      )}

      {/* Expanded Hint Card */}
      {isExpanded && (
        <div className="absolute top-4 left-4 z-20 pointer-events-auto w-80 bg-white rounded-xl shadow-2xl border border-gray-200 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-300">
          {/* Hint Header */}
          <div className="px-5 pt-4 pb-3 flex items-center justify-between border-b border-gray-100">
            <h3 className="text-xl font-semibold text-gray-900">Hint</h3>
            <button
              onClick={() => setIsExpanded(false)}
              className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors"
              title="Minimize"
            >
              <Minimize2 className="w-5 h-5 text-gray-500" />
            </button>
          </div>

          {/* Hint Content */}
          <div className="px-5 py-4">
            <p className="text-sm 2xl:text-base text-gray-700 leading-relaxed">
              {renderTextWithMath(hint)}
            </p>
          </div>
        </div>
      )}
    </>
  );
};

