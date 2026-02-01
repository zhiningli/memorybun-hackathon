// Question configuration file
// This file contains all question data that can be easily modified or fetched from a database

// ============================================
// TYPE DEFINITIONS
// ============================================

// Hint is now just a string with $...$ for inline math
// Example: "Calculate $\\sin(x)$ when $x = 0$"

export interface FeedbackConfig {
  overallMessage: string;
  sections: {
    title: string;
    text: string;
    points: string[];
  }[];
  sampleSolutionImage: string;
}

// Each question part (a, b, c, d) is a complete question
export interface QuestionPart {
  partId: string;              // "a", "b", "c", "d"
  partLabel: string;           // "(a)", "(b)", "(c)", "(d)"
  title: string;               // "Graph Plotting" - the main title
  questionDetails?: string;    // "Plot function" - the specific task (displayed emphasized)
  questionDetailsMath?: string;// "f(x) = e^x" - optional LaTeX for question details
  instructions: string[];      // Array of instruction paragraphs
  thinkTimeLimit: number;      // Think time in seconds
  recordTimeLimit: number;     // Record time in seconds
  hint: string;  // Use $...$ for inline math, e.g. "Calculate $\\sin(x)$"
  feedback: FeedbackConfig;
  isPlottingQuestion?: boolean; // Whether to show the plot grid (default: false)
}

// A question set groups related question parts together
export interface QuestionSet {
  id: number;                  // Question set ID (1, 2, 3...)
  category: string;            // "Graph Plotting", "Circuit Analysis", etc.
  displayName: string;         // "Mock Question 1"
  parts: QuestionPart[];       // All parts: a, b, c, d
}

// ============================================
// QUESTION 1 - Graph Plotting
// ============================================

export const question1: QuestionSet = {
  id: 1,
  category: "Graph Plotting",
  displayName: "Exercise 1",
  parts: [
    // Part (a) - Main question
    {
      partId: "a",
      partLabel: "(a)",
      title: "Graph Plotting 1",
      questionDetails: "Plot function",
      questionDetailsMath: "f(x) = e^x",
      isPlottingQuestion: true,
      instructions: [
        "You will now have {thinkTime} to prepare. After that, you will have up to {recordTime} to record your verbal response and plot the function on the highlighted plot grid to the right. You may also use the white board to show any additional calculations or thoughts.",
        "You can press the 'Record' button below when you're ready."
      ],
      thinkTimeLimit: 20,
      recordTimeLimit: 60,
      hint: "Calculate the value of $e^x$ when $x$ equals to $0, 1, 2$...",
      feedback: {
        overallMessage: "Well done! Your response is mostly correct!",
        sections: [
          {
            title: "Plot",
            text: "Your plot looks correct but lack of details:",
            points: [
              "No label on value at x=0",
              "......",
              "......"
            ]
          },
          {
            title: "Recording",
            text: "Your explanation sounds sensible but several things can be improved:",
            points: [
              "explanation needs to be more structure and logical",
              "lots of grammar error which affects the fluency of your answer",
              "......"
            ]
          }
        ],
        sampleSolutionImage: "/sample-solution-plot-1a.png"
      }
    },

    // Part (b) - Follow-up Question 1
    {
      partId: "b",
      partLabel: "(b)",
      title: "Follow-up Question 1",
      questionDetails: "Plot function",
      questionDetailsMath: "f(x) = sin(x)",
      isPlottingQuestion: true,
      instructions: [
        "You will have {thinkTime} to prepare and {recordTime} to record your verbal response.",
        "Press 'Record' when ready."
      ],
      thinkTimeLimit: 20,
      recordTimeLimit: 60,
      hint: "Calculate the value of $\\sin(x)$ when $x$ equals to $0$, $\\frac{\\pi}{2}$, $\\pi$, $\\frac{3\\pi}{2}$, $2\\pi$...",
      feedback: {
        overallMessage: "Good attempt!",
        sections: [
          {
            title: "Answer",
            text: "Your answer is partially correct:",
            points: [
              "Correct understanding of the concept",
              "Missing some details"
            ]
          }
        ],
        sampleSolutionImage: "/sample-solution-plot-1b.png"
      }
    },

    // Part (c) - Follow-up Question 2
    {
      partId: "c",
      partLabel: "(c)",
      title: "Follow-up Question 2",
      questionDetails: "Plot function",
      questionDetailsMath: "f(x) = e^x \\cdot sin(x)",
      isPlottingQuestion: true,
      instructions: [
        "You will have {thinkTime} to prepare and {recordTime} to record your verbal response.",
        "Press 'Record' when ready."
      ],
      thinkTimeLimit: 30,
      recordTimeLimit: 90,
      hint: "Consider the behaviour of $f(x) = e^x$ and $f(x) = \\sin(x)$ when $x$ approaches $\\infty$ and $-\\infty$",
      feedback: {
        overallMessage: "Nice work!",
        sections: [
          {
            title: "Answer",
            text: "Your response shows good understanding:",
            points: [
              "Clear explanation",
              "Good use of terminology"
            ]
          }
        ],
        sampleSolutionImage: "/sample-solution-plot-1c.png"
      }
    },

    // Part (d) - Extension Question
    {
      partId: "d",
      partLabel: "(d)",
      title: "Extension Question",
      questionDetails: "Plot function",
      questionDetailsMath: "f(x) = x \\cdot \\cos(x)",
      isPlottingQuestion: true,
      instructions: [
        "You will have {thinkTime} to prepare and {recordTime} to record.",
        "Press 'Record' when ready."
      ],
      thinkTimeLimit: 40,
      recordTimeLimit: 90,
      hint: "Think about the behaviour of $f(x) = x \\cdot \\cos(x)$, try to plot the two individual functions $f(x) = x$ and $f(x) = \\cos(x)$ first",
      feedback: {
        overallMessage: "Excellent work on the extension!",
        sections: [
          {
            title: "Plot",
            text: "Your comparison plot is good:",
            points: [
              "Correct reflection shown",
              "Good labeling"
            ]
          },
          {
            title: "Explanation",
            text: "Your verbal explanation:",
            points: [
              "Clear connection made between the two functions"
            ]
          }
        ],
        sampleSolutionImage: "/sample-solution-plot-1d.png"
      }
    }
  ]
};

// ============================================
// TEMPLATE FOR NEW QUESTION SET
// ============================================
/*
export const question2: QuestionSet = {
  id: 2,
  category: "Circuit Analysis",
  displayName: "Mock Question 2",
  parts: [
    {
      partId: "a",
      partLabel: "(a)",
      title: "Circuit Analysis",              // Main title (e.g., topic)
      questionDetails: "Calculate voltage",   // Specific task (emphasized)
      questionDetailsMath: "V = IR",          // Optional LaTeX for the task
      instructions: [
        "First instruction paragraph",
        "Second instruction paragraph"
      ],
      thinkTimeLimit: 30,
      recordTimeLimit: 120,
      hint: {
        text: "Your hint text with {math} expressions",
        mathExpressions: [
          { placeholder: "{math}", math: "\\LaTeX" }
        ]
      },
      feedback: {
        overallMessage: "Feedback message",
        sections: [
          {
            title: "Section Title",
            text: "Section description",
            points: ["Point 1", "Point 2"]
          }
        ],
        sampleSolutionImage: "/sample-solution-2a.png"
      }
    },
    // Add parts b, c, d as needed...
  ]
};
*/

// ============================================
// QUESTION REGISTRY & HELPERS
// ============================================

// All question sets
export const questionSets: Record<number, QuestionSet> = {
  1: question1,
  // 2: question2,
};

// Get a question set by ID
export const getQuestionSet = (id: number): QuestionSet | undefined => {
  return questionSets[id];
};

// Get a specific question part from a question set
export const getQuestionPart = (setId: number, partId: string): QuestionPart | undefined => {
  const questionSet = questionSets[setId];
  if (!questionSet) return undefined;
  return questionSet.parts.find(p => p.partId === partId);
};

// Get the index of a part in the parts array
export const getPartIndex = (questionSet: QuestionSet, partId: string): number => {
  return questionSet.parts.findIndex(p => p.partId === partId);
};

// Get the next part after current one
export const getNextPart = (questionSet: QuestionSet, currentPartId: string): QuestionPart | undefined => {
  const currentIndex = getPartIndex(questionSet, currentPartId);
  if (currentIndex === -1 || currentIndex >= questionSet.parts.length - 1) {
    return undefined;
  }
  return questionSet.parts[currentIndex + 1];
};

// Default question set
export const defaultQuestionSet = question1;
export const defaultQuestionPart = question1.parts[0];
