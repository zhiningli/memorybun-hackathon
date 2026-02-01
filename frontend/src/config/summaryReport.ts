// Summary Report configuration file
// This file contains all text and data for the Summary Report page

// ============================================
// TYPE DEFINITIONS
// ============================================

export interface OverviewAnalytics {
  highestScoringDimension: string;
  secondaryStrengths: string;
  lowestScoringDimension: string;
  scoreSpread: string;
  performanceProfile: string;
}

export interface QuestionSlide {
  id: number;
  title: string;
  feedback: string;
  idealAnswer: {
    description: string[];
    keyPoints: string[];
  };
}

export interface PerformanceData {
  problemFraming: number;
  solutionExecution: number;
  technicalCorrectness: number;
  communicationAndWhiteboard: number;
  timeManagement: number;
}

export interface SessionOverviewData {
  date: string;
  question: string;
  duration: string;
}

export interface SummaryReportConfig {
  sessionOverview: SessionOverviewData;
  performanceData: PerformanceData;
  overallScorePercentile: string;
  overviewAnalytics: OverviewAnalytics;
  overviewFeedback: string;
  questionSlides: QuestionSlide[];
  strengths: string[];
  improvements: string[];
}

// ============================================
// CONFIGURATION DATA
// ============================================

export const summaryReportConfig: SummaryReportConfig = {
  sessionOverview: {
    date: "October 28, 2025",
    question: "Envelope Function Plot",
    duration: "18m 28s",
  },

  performanceData: {
    problemFraming: 75,
    solutionExecution: 70,
    technicalCorrectness: 85,
    communicationAndWhiteboard: 80,
    timeManagement: 60,
  },

  overallScorePercentile: "Top 15%",

  overviewAnalytics: {
    highestScoringDimension: 'Technical Correctness, indicating consistently accurate reasoning and correct application of core concepts.',
    secondaryStrengths: 'Communication and Whiteboard Use, both scoring above the median and supporting clear explanation and visual structuring of ideas.',
    lowestScoringDimension: 'Time Management, which had the largest negative impact on the overall score relative to other skills.',
    scoreSpread: 'Moderate, with most dimensions clustered within a narrow band, suggesting a balanced skill profile rather than isolated strengths or weaknesses.',
    performanceProfile: 'Strong technical accuracy combined with moderate variability in execution and pacing across the session.',
  },

  overviewFeedback: `This session reflects a solid and dependable technical performance, with clear confidence in core concepts and composure under questioning. Responses were generally well-structured, and explanations demonstrated understanding beyond surface-level recall.

Performance was strongest when a clear approach was established early and reasoning was verbalised throughout. Under time pressure, structure and pacing became less consistent, suggesting that earlier prioritisation would further strengthen delivery.

Overall, this was a strong showing with clear upside, particularly through more deliberate upfront structuring and execution efficiency.`,

  questionSlides: [
    {
      id: 1,
      title: 'Plot function $f(x) = e^x$',
      feedback: 'You correctly identified the exponential form of the function $f(x) = e^x$ and sketched its overall behaviour well. The curve increases monotonically and passes through the key point $f(0) = 1$, which you stated clearly. To improve, be more explicit about the function\'s asymptotic behaviour as $x \\to -\\infty$ and ensure your axis scaling reflects the rapid growth for large positive $x$.',
      idealAnswer: {
        description: [
          'Begin by identifying the function as an exponential function of the form $f(x) = e^x$.',
          'State the key reference point at $x = 0$ and explain why $f(0) = 1$.',
          'Describe how the function behaves as $x$ increases, focusing on its rapid growth.',
          'Discuss the behaviour as $x \\to -\\infty$, introducing the horizontal asymptote.',
          'Summarise the overall shape and key features of the graph.',
        ],
        keyPoints: [
          'The function is always positive and never crosses the x-axis, meaning $f(x) > 0$ for all real $x$.',
          'At $x = 0$, the function evaluates to $f(0) = 1$.',
          'As $x \\to -\\infty$, the function approaches zero, i.e. $f(x) \\to 0$.',
          'As $x$ increases, the rate of growth accelerates exponentially.',
        ],
      },
    },
    {
      id: 2,
      title: 'Plot function $f(x) = \\sin(x)$',
      feedback: 'You correctly recognised the sinusoidal nature of the function $f(x) = \\sin(x)$ and captured its periodic behaviour in your sketch. The amplitude and symmetry about the x-axis were shown clearly. To improve, explicitly mark key points such as zeros and extrema, and ensure the period is accurately represented along the x-axis.',
      idealAnswer: {
        description: [
          'Start by identifying the function as the sine function $f(x) = \\sin(x)$.',
          'Explain that the function is periodic and describe what this means for the graph.',
          'State the amplitude and range of the function.',
          'Identify key points such as zeros, maxima, and minima.',
          'Conclude by describing how the pattern repeats over each period.',
        ],
        keyPoints: [
          'The function has amplitude 1 and range $[-1, 1]$.',
          'The period of the function is $2\\pi$, meaning the pattern repeats every $2\\pi$.',
          'The function crosses the x-axis at $x = n\\pi$ for any integer $n$.',
          'Maximum values of $1$ occur at $x = \\frac{\\pi}{2} + 2n\\pi$, and minimum values of $-1$ occur at $x = \\frac{3\\pi}{2} + 2n\\pi$.',
        ],
      },
    },
    {
      id: 3,
      title: 'Plot function $f(x) = e^x \\sin(x)$',
      feedback: 'You correctly identified that the function $f(x) = e^x \\sin(x)$ combines exponential growth with sinusoidal oscillation. Your sketch showed the oscillatory behaviour clearly, but it would be stronger if you explicitly indicated how the amplitude grows with $e^x$ as $x$ increases. Marking the envelope curves would also help communicate the long-term behaviour of the function.',
      idealAnswer: {
        description: [
          'Start by identifying the function as a product of two familiar functions: $e^x$ and $\\sin(x)$.',
          'Describe the basic behaviour of $\\sin(x)$, including its oscillation and zeros.',
          'Explain how multiplying by $e^x$ affects the graph by scaling the amplitude of the oscillations.',
          'Introduce the envelope curves and describe how they bound the function.',
          'Conclude by discussing the behaviour as $x$ increases and as $x \\to -\\infty$.',
        ],
        keyPoints: [
          'The function oscillates between the envelope curves $y = e^x$ and $y = -e^x$.',
          'Zeros occur at the same x-values as $\\sin(x)$, namely at $x = n\\pi$ for any integer $n$.',
          'As $x$ increases, the magnitude of the oscillations increases exponentially.',
          'As $x \\to -\\infty$, the function decays toward zero while continuing to oscillate.',
        ],
      },
    },
  ],

  strengths: [
    'Strong theoretical understanding of signal processing fundamentals.',
    'Clear verbal communication when defining variables.',
    'Effective use of visual aids (dashed lines) to construct complex plots.',
    'Maintained composure during complex follow-up questions.',
  ],

  improvements: [
    'Pay closer attention to axis scaling consistency on the whiteboard.',
    'Time management: You spent 40% of time on part (a), leaving less for (c).',
    'State assumptions explicitly before starting the derivation.',
    'Consider double-checking arithmetic for boundary conditions.',
  ],
};

