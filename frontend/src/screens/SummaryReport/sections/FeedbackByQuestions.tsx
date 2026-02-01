import { useState, useMemo } from 'react';
import { CheckCircle2, ArrowRight, MessageSquare, Gem, BarChart3, ChartPie } from 'lucide-react';
import { renderTextWithMath } from '../../../lib/mathUtils';
import { summaryReportConfig } from '../../../config/summaryReport';
import { Question, Answer, SummaryResultResponse, GradingResultResponse } from '../../../types/api';

interface FeedbackByQuestionsProps {
  questions: Question[];
  answers: Answer[];
  summaryResult?: SummaryResultResponse | null;
  gradingResults?: GradingResultResponse[];
}

export const FeedbackByQuestions = ({ questions, answers, summaryResult, gradingResults = [] }: FeedbackByQuestionsProps): JSX.Element => {
  const [currentSlide, setCurrentSlide] = useState(0);

  const { overviewAnalytics, overviewFeedback: configOverviewFeedback } = summaryReportConfig;
  const overviewFeedback = summaryResult?.overall_feedback || configOverviewFeedback;

  // Create question slides from questions and answers
  const questionSlides = useMemo(() => {
    return questions.map((question, index) => {
      const answer = answers.find(a => a.question_id === question.id);
      // Use grading result feedback if available, otherwise fall back to config
      const gradingFeedback = gradingResults[index]?.feedback;

      return {
        id: index + 1,
        title: question.title,
        feedback: gradingFeedback || summaryReportConfig.questionSlides[index]?.feedback || 'Feedback not available',
        idealAnswer: {
          description: answer?.ideal_answer_structure || summaryReportConfig.questionSlides[index]?.idealAnswer.description || [],
          keyPoints: answer?.key_constraints_to_mention || summaryReportConfig.questionSlides[index]?.idealAnswer.keyPoints || [],
        },
      };
    });
  }, [questions, answers, gradingResults]);

  // Total slides = 1 overview + question slides
  const totalSlides = 1 + questionSlides.length;


  const nextSlide = () => {
    if (currentSlide < totalSlides - 1) {
      setCurrentSlide(currentSlide + 1);
    }
  };

  const goToSlide = (index: number) => {
    setCurrentSlide(index);
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Top Section: Feedback by Questions Sliding Panel */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 2xl:p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg 2xl:text-xl font-semibold text-black">
            Feedback by Questions
          </h2>
        </div>

        {/* Slide Content */}
        <div className="grid grid-cols-1 mb-2">
          {/* Overview Slide (index 0) */}
          <div
            className={`col-start-1 row-start-1 border border-gray-200 rounded-xl p-4 2xl:p-5 mb-4 transition-opacity duration-300 ${currentSlide === 0 ? 'visible opacity-100' : 'invisible opacity-0'
              }`}
          >
            {/* Overview Title */}
            <div className="flex items-center gap-2 mb-4">
              <span className="w-8 h-8 bg-[#0053FA]/10 text-[#0053FA] rounded-full flex items-center justify-center text-base font-semibold">
                <BarChart3 className="w-4 h-4" />
              </span>
              <h3 className="text-base 2xl:text-lg font-semibold text-black">
                Overview
              </h3>
            </div>

            <div className="h-px bg-gray-200 my-4 mb-6" />

            {/* Two Column Layout - Analytics and Feedback */}
            <div className="grid grid-cols-[1fr_auto_1fr] gap-4 mb-1">
              {/* Left: Analytics */}
              <div className="flex flex-col">
                <div className="flex items-center gap-2 mb-2">
                  <ChartPie className="w-4 h-4 text-gray-500" />
                  <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">Analytics</span>
                </div>
                <ul className="bg-[#e6eeff80] rounded-lg p-4 space-y-1 h-full">
                  {[
                    { label: "Highest scoring dimension", value: summaryResult?.analytics_summary?.[0] ?? overviewAnalytics.highestScoringDimension },
                    { label: "Secondary strengths", value: summaryResult?.analytics_summary?.[1] ?? overviewAnalytics.secondaryStrengths },
                    { label: "Lowest scoring dimension", value: summaryResult?.analytics_summary?.[2] ?? overviewAnalytics.lowestScoringDimension },
                    { label: "Score spread", value: summaryResult?.analytics_summary?.[3] ?? overviewAnalytics.scoreSpread },
                    { label: "Performance profile", value: summaryResult?.analytics_summary?.[4] ?? overviewAnalytics.performanceProfile },
                  ].map((item, i) => (
                    <li key={i} className="text-sm 2xl:text-base text-gray-700 flex items-start gap-2">
                      <span className="text-gray-400 mt-1 flex-shrink-0">•</span>
                      <span className="flex-1">
                        <span className="font-semibold">{item.label}:</span> {item.value ? renderTextWithMath(item.value) : ''}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Vertical Separator */}
              <div className="w-px h-[75%] bg-gray-200 self-center" />

              {/* Right: Feedback */}
              <div className="flex flex-col">
                <div className="flex items-center gap-2 mb-2">
                  <MessageSquare className="w-4 h-4 text-gray-500" />
                  <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">Feedback</span>
                </div>
                <div className="bg-[#F9F9F9] rounded-lg p-4 h-full">
                  <div className="text-sm 2xl:text-base text-gray-700 leading-relaxed space-y-3">
                    {overviewFeedback.split('\n\n').map((paragraph, index) => (
                      <p key={index}>{renderTextWithMath(paragraph.trim())}</p>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Question Slides (index 1+) */}
          {questionSlides.map((slide, index) => (
            <div
              key={slide.id}
              className={`col-start-1 row-start-1 border border-gray-200 rounded-xl p-4 2xl:p-5 mb-4 transition-opacity duration-300 ${index + 1 === currentSlide ? 'visible opacity-100' : 'invisible opacity-0'
                }`}
            >
              {/* Question Title */}
              <div className="flex items-center gap-2 mb-4">
                <span className="w-8 h-8 bg-[#0053FA]/10 text-[#0053FA] rounded-full flex items-center justify-center text-base font-semibold">
                  {slide.id}
                </span>
                <h3 className="text-base 2xl:text-lg font-semibold text-black">
                  {renderTextWithMath(slide.title)}
                </h3>
              </div>


              <div className="h-px bg-gray-200 my-4 mb-6" />

              {/* Feedback */}
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <MessageSquare className="w-4 h-4 text-gray-500" />
                  <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">Feedback</span>
                </div>
                <p className="text-sm 2xl:text-base text-gray-700 leading-relaxed mb-3">
                  {renderTextWithMath(slide.feedback)}
                </p>
              </div>

              {/*Horizontal Separator */}
              <div className="h-px bg-gray-200 my-4 mb-6" />

              {/* Two Column Layout - Feedback narrower, Ideal Answer wider */}
              <div className="grid grid-cols-[1fr_auto_1fr] gap-4 mb-1">
                {/* Left: Ideal Answer Structure */}
                <div className="flex flex-col">
                  <div className="flex items-center gap-2 mb-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                    <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">Ideal Answer Structure</span>
                  </div>
                  <ul className="bg-[#e6eeff80] rounded-lg p-4 space-y-1 h-full">
                    {slide.idealAnswer.description.map((point, i) => (
                      <li key={i} className="text-sm 2xl:text-base text-gray-700 flex items-start gap-2">
                        <span className="text-gray-400 mt-1 flex-shrink-0">•</span>
                        <span className="flex-1">{renderTextWithMath(point)}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Vertical Separator */}
                <div className="w-px h-[75%] bg-gray-200 self-center" />

                {/* Right: Key Constraints */}
                <div className="flex flex-col">
                  <div className="flex items-center gap-2 mb-2">
                    <Gem className="w-4 h-4 text-gray-500" />
                    <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">Key Constraints to Mention:</span>
                  </div>
                  <ul className="bg-[#F9F9F9] rounded-lg p-4 space-y-1 h-full">
                    {slide.idealAnswer.keyPoints.map((point, i) => (
                      <li key={i} className="text-sm 2xl:text-base text-gray-700 flex items-start gap-2">
                        <span className="text-gray-400 mt-1 flex-shrink-0">•</span>
                        <span className="flex-1">{renderTextWithMath(point)}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Navigation */}
        <div className="flex items-center justify-between">
          <span className="text-sm 2xl:text-base text-gray-500">
            {currentSlide === 0 ? 'Overview' : `Question ${currentSlide} of ${questionSlides.length}`}
          </span>

          {/* Dots */}
          <div className="flex items-center gap-2">
            {/* Overview dot */}
            <button
              onClick={() => goToSlide(0)}
              className={`rounded-full transition-all ${0 === currentSlide
                ? 'w-3.5 h-3.5 bg-[#0053FA] border-2 border-[#e6eeff80]'
                : 'w-2.5 h-2.5 bg-gray-300'
                }`}
            />
            {/* Question dots */}
            {questionSlides.map((_, index) => (
              <button
                key={index}
                onClick={() => goToSlide(index + 1)}
                className={`rounded-full transition-all ${index + 1 === currentSlide
                  ? 'w-3.5 h-3.5 bg-[#0053FA] border-2 border-[#e6eeff80]'
                  : 'w-2.5 h-2.5 bg-gray-300'
                  }`}
              />
            ))}
          </div>

          {/* Next Button */}
          {currentSlide < totalSlides - 1 ? (
            <button
              onClick={nextSlide}
              className="flex items-center gap-1 text-[#0053FA] font-medium text-sm 2xl:text-base hover:opacity-80 transition-opacity"
            >
              {currentSlide === 0 ? 'Next Question' : 'Next Question'}
              <ArrowRight className="w-4 h-4" />
            </button>
          ) : (
            <span className="text-sm 2xl:text-base text-gray-400">End of Questions</span>
          )}
        </div>
      </div>
    </div>
  );
};
