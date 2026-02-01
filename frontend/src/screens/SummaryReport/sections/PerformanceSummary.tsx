import { useMemo } from 'react';
import { TrendingUp } from 'lucide-react';
import { summaryReportConfig } from '../../../config/summaryReport';
import { SummaryResultResponse, GradingResultResponse } from '../../../types/api';

interface PerformanceSummaryProps {
  summaryResult?: SummaryResultResponse | null;
  gradingResults?: GradingResultResponse[];
  weights?: Record<string, number>;
}

// Band classification schema
const BAND_CLASSIFICATION = [
  { min: 80, label: "Excellent candidate", exclusive: true }, // > 80
  { min: 75, label: "Strong candidate" },      // 75-80
  { min: 65, label: "Satisfactory candidate" }, // 65-75
  { min: 0, label: "Improvement needed" }      // < 65
];

export const PerformanceSummary = ({ summaryResult, gradingResults = [], weights = {} }: PerformanceSummaryProps): JSX.Element => {
  // Calculate aggregated scores from grading results if available
  const calculatedPerformance = useMemo(() => {
    if (!gradingResults.length) return null;

    // Initialize sums and counts for each dimension
    const dimensionSums: Record<string, number> = {
      "Technical Correctness": 0,
      "Communication & Whiteboard Use": 0,
      "Time Management": 0,
      "Solution Execution": 0,
      "Problem Framing": 0
    };

    const dimensionCounts: Record<string, number> = {
      "Technical Correctness": 0,
      "Communication & Whiteboard Use": 0,
      "Time Management": 0,
      "Solution Execution": 0,
      "Problem Framing": 0
    };

    // Iterate through all grading results and sum up scores
    gradingResults.forEach(result => {
      if (result.score_breakdown) {
        result.score_breakdown.forEach(score => {
          if (dimensionSums[score.dimension] !== undefined) {
            // Backend sends 0-1 percentage, frontend uses 0-100 scale for radar chart? 
            // Existing code used getScore which multiplied by 10 (assuming 0-10 input?)
            // Let's assume we want 0-100 scale for the radar chart data.
            // If percentage is 0.9, we want 90? Or 9?
            // Looking at existing config:
            // performanceData: { problemFraming: 75, ... } -> These are 0-100.
            // So percentage * 100.
            dimensionSums[score.dimension] += (score.percentage * 100);
            dimensionCounts[score.dimension]++;
          }
        });
      }
    });

    // Calculate averages
    return {
      technicalCorrectness: dimensionCounts["Technical Correctness"] ? Math.round(dimensionSums["Technical Correctness"] / dimensionCounts["Technical Correctness"]) : 0,
      communicationAndWhiteboard: dimensionCounts["Communication & Whiteboard Use"] ? Math.round(dimensionSums["Communication & Whiteboard Use"] / dimensionCounts["Communication & Whiteboard Use"]) : 0,
      timeManagement: dimensionCounts["Time Management"] ? Math.round(dimensionSums["Time Management"] / dimensionCounts["Time Management"]) : 0,
      solutionExecution: dimensionCounts["Solution Execution"] ? Math.round(dimensionSums["Solution Execution"] / dimensionCounts["Solution Execution"]) : 0,
      problemFraming: dimensionCounts["Problem Framing"] ? Math.round(dimensionSums["Problem Framing"] / dimensionCounts["Problem Framing"]) : 0,
    };
  }, [gradingResults]);


  // Helper to get score for a dimension from formatted summaryResult
  const getScore = (dimName: string) => {
    const dim = summaryResult?.dimension_scores.find(d => d.dimension === dimName);
    return dim ? dim.score * 10 : null; // Assuming backend returns 0-10, frontend uses 0-100
  };

  const performanceData = calculatedPerformance ?? (summaryResult ? {
    technicalCorrectness: getScore("Technical Correctness") ?? summaryReportConfig.performanceData.technicalCorrectness,
    communicationAndWhiteboard: getScore("Communication & Whiteboard Use") ?? summaryReportConfig.performanceData.communicationAndWhiteboard,
    timeManagement: getScore("Time Management") ?? summaryReportConfig.performanceData.timeManagement,
    solutionExecution: getScore("Solution Execution") ?? summaryReportConfig.performanceData.solutionExecution,
    problemFraming: getScore("Problem Framing") ?? summaryReportConfig.performanceData.problemFraming,
  } : summaryReportConfig.performanceData);

  // Calculate overall score: use weights if provided, otherwise simple average
  const overallScore = useMemo(() => {
    if (Object.keys(weights).length > 0) {
      const weightedSum =
        (performanceData.technicalCorrectness * (weights["Technical Correctness"] || 0)) +
        (performanceData.communicationAndWhiteboard * (weights["Communication & Whiteboard Use"] || 0)) +
        (performanceData.timeManagement * (weights["Time Management"] || 0)) +
        (performanceData.solutionExecution * (weights["Solution Execution"] || 0)) +
        (performanceData.problemFraming * (weights["Problem Framing"] || 0));

      // Ensure weights sum to 1 (or close to it), if not we might need to normalize?
      // Assuming they sum to 1 as provided in requirements.
      return Math.round(weightedSum);
    }

    return Math.round(
      (performanceData.technicalCorrectness +
        performanceData.communicationAndWhiteboard +
        performanceData.timeManagement +
        performanceData.solutionExecution +
        performanceData.problemFraming) / 5
    );
  }, [performanceData, weights]);

  // Determine band label based on overall score
  const bandLabel = useMemo(() => {
    for (const band of BAND_CLASSIFICATION) {
      if (band.exclusive) {
        if (overallScore > band.min) return band.label;
      } else {
        if (overallScore >= band.min) return band.label;
      }
    }
    return BAND_CLASSIFICATION[BAND_CLASSIFICATION.length - 1].label;
  }, [overallScore]);


  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 2xl:p-6 h-full flex-1">
      <h2 className="text-lg 2xl:text-xl font-semibold text-black">
        Performance Summary
      </h2>
      <p className="text-sm 2xl:text-base text-gray-500 mb-4">
        Skill distribution analysis
      </p>

      {/* Radar Chart Placeholder - SVG */}
      <div className="flex items-center justify-center">
        <svg width="320" height="320" viewBox="0 0 320 320" className="overflow-visible">
          {/* Background pentagon grid */}
          <g transform="translate(160, 160)">
            {/* Grid lines (3 levels) */}
            {[100, 75, 50, 25].map((scale, i) => {
              const points = [
                { x: 0, y: -scale },           // Technical Correctness (top)
                { x: scale * 0.95, y: -scale * 0.31 },  // Communication & Whiteboard (top-right)
                { x: scale * 0.59, y: scale * 0.81 },   // Time Management (bottom-right)
                { x: -scale * 0.59, y: scale * 0.81 },  // Solution Execution (bottom-left)
                { x: -scale * 0.95, y: -scale * 0.31 }, // Problem Framing (top-left)
              ];

              return (
                <polygon
                  key={i}
                  points={points.map(p => `${p.x},${p.y}`).join(' ')}
                  fill="none"
                  stroke="#E5E7EB"
                  strokeWidth="1"
                />
              );
            })}

            {/* Axis lines */}
            {[
              { x: 0, y: -100, label: 'Technical\nCorrectness', labelX: 0, labelY: -120 },
              { x: 95, y: -31, label: 'Comm. &\nWhiteboard', labelX: 125, labelY: -36 },
              { x: 59, y: 81, label: 'Time\nManagement', labelX: 64, labelY: 95 },
              { x: -59, y: 81, label: 'Solution\nExecution', labelX: -64, labelY: 95 },
              { x: -95, y: -31, label: 'Problem\nFraming', labelX: -125, labelY: -36 },
            ].map((axis, i) => (
              <g key={i}>
                <line
                  x1="0"
                  y1="0"
                  x2={axis.x}
                  y2={axis.y}
                  stroke="#E5E7EB"
                  strokeWidth="1"
                />
                <text
                  x={axis.labelX || axis.x}
                  y={axis.labelY || axis.y}
                  textAnchor="middle"
                  className="fill-gray-700 text-xs font-medium"
                  style={{ fontSize: '12px' }}
                >
                  {axis.label.split('\n').map((line, j) => (
                    <tspan key={j} x={axis.labelX || axis.x} dy={j === 0 ? 0 : 14}>
                      {line}
                    </tspan>
                  ))}
                </text>
              </g>
            ))}


            {/* Data polygon (blue fill) */}
            <polygon
              points={[
                `0,${-performanceData.technicalCorrectness}`,
                `${performanceData.communicationAndWhiteboard * 0.95},${-performanceData.communicationAndWhiteboard * 0.31}`,
                `${performanceData.timeManagement * 0.59},${performanceData.timeManagement * 0.81}`,
                `${-performanceData.solutionExecution * 0.59},${performanceData.solutionExecution * 0.81}`,
                `${-performanceData.problemFraming * 0.95},${-performanceData.problemFraming * 0.31}`,
              ].join(' ')}
              fill="#0053FA"
              fillOpacity="0.2"
              stroke="#0053FA"
              strokeWidth="1.5"
            />

            {/* Data points */}
            {[
              { x: 0, y: -performanceData.technicalCorrectness },
              { x: performanceData.communicationAndWhiteboard * 0.95, y: -performanceData.communicationAndWhiteboard * 0.31 },
              { x: performanceData.timeManagement * 0.59, y: performanceData.timeManagement * 0.81 },
              { x: -performanceData.solutionExecution * 0.59, y: performanceData.solutionExecution * 0.81 },
              { x: -performanceData.problemFraming * 0.95, y: -performanceData.problemFraming * 0.31 },
            ].map((point, i) => (
              <circle
                key={i}
                cx={point.x}
                cy={point.y}
                r="3.5"
                fill="#001d58"
                stroke="white"
                strokeWidth="1.5"
              />
            ))}
          </g>
        </svg>
      </div>

      {/* Overall Score Section */}
      <div className="flex flex-col items-center mt-6 pt-6 border-t border-gray-200">
        <div className="text-xs font-medium text-gray-500 tracking-wider mb-2">OVERALL SCORE</div>
        <div className="flex items-baseline gap-1 mb-3">
          <span className="text-5xl 2xl:text-6xl font-bold text-[#001d58]">
            {overallScore}
          </span>
          <span className="text-lg 2xl:text-xl text-gray-400">/100</span>
        </div>
        <div className="flex items-center gap-1 bg-emerald-50 text-emerald-600 px-3 py-1 rounded-full text-sm font-medium">
          <TrendingUp className="w-4 h-4" />
          <span>{bandLabel}</span>
        </div>
      </div>


    </div>
  );
};

