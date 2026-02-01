import { Award, CheckCircle2, TrendingUp, Lightbulb } from 'lucide-react';
import { summaryReportConfig } from '../../../config/summaryReport';
import { SummaryResultResponse } from '../../../types/api';
import { renderTextWithMath } from '../../../lib/mathUtils';

interface StrengthsAndImprovementsProps {
    summaryResult?: SummaryResultResponse | null;
}

export const StrengthsAndImprovements = ({ summaryResult }: StrengthsAndImprovementsProps): JSX.Element => {
    const { strengths: configStrengths, improvements: configImprovements } = summaryReportConfig;

    // Use dynamic data if available, otherwise fallback to config
    const strengths = summaryResult?.key_strengths || configStrengths;
    const improvements = summaryResult?.areas_for_improvement || configImprovements;

    return (
        <div className="flex flex-col h-full flex-1">
            <div className="grid grid-cols-2 gap-4 h-full">
                {/* Key Strengths */}
                <div className="bg-[#e6eeff80] rounded-xl border border-gray-200 p-5 2xl:p-6">
                    <div className="flex items-center gap-2 mb-4">
                        <div className="w-8 h-8 bg-[#0053FA] rounded-full flex items-center justify-center">
                            <Award className="w-4 h-4 text-white" />
                        </div>
                        <h3 className="text-base 2xl:text-lg font-semibold text-black">
                            Key Strengths
                        </h3>
                    </div>
                    <ul className="space-y-3">
                        {strengths.map((strength, index) => (
                            <li key={index} className="flex items-start gap-2">
                                <CheckCircle2 className="w-4 h-4 text-[#0053FA] mt-0.5 flex-shrink-0" />
                                <span className="text-sm 2xl:text-base text-gray-700">{renderTextWithMath(strength)}</span>
                            </li>
                        ))}
                    </ul>
                </div>

                {/* Areas for Improvement */}
                <div className="bg-[#FFF7ED] rounded-xl border border-gray-200 p-5 2xl:p-6">
                    <div className="flex items-center gap-2 mb-4">
                        <div className="w-8 h-8 bg-orange-500 rounded-full flex items-center justify-center">
                            <TrendingUp className="w-4 h-4 text-[#FFF7ED]" />
                        </div>
                        <h3 className="text-base 2xl:text-lg font-semibold text-black">
                            Areas for Improvement
                        </h3>
                    </div>
                    <ul className="space-y-3">
                        {improvements.map((improvement, index) => (
                            <li key={index} className="flex items-start gap-2">
                                <Lightbulb className="w-4 h-4 text-orange-500 mt-0.5 flex-shrink-0" />
                                <span className="text-sm 2xl:text-base text-gray-700">{renderTextWithMath(improvement)}</span>
                            </li>
                        ))}
                    </ul>
                </div>
            </div>
        </div>
    );
};
