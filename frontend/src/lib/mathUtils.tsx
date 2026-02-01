import { InlineMath } from "react-katex";

/**
 * Helper function to render text with inline math using $...$ syntax
 * Example: "Calculate $\\sin(x)$ when $x = 0$" renders sin(x) and x = 0 as math
 * 
 * @param text - Text that may contain math expressions wrapped in $...$
 * @returns JSX element with text and math expressions properly rendered
 */
export const renderTextWithMath = (text: string): JSX.Element => {
  // Split by $...$ pattern, keeping the delimiters info
  const parts: (string | JSX.Element)[] = [];
  const regex = /\$([^$]+)\$/g;
  let lastIndex = 0;
  let match;
  let keyIndex = 0;
  
  while ((match = regex.exec(text)) !== null) {
    // Add text before the match
    if (match.index > lastIndex) {
      parts.push(text.substring(lastIndex, match.index));
    }
    // Add the math expression (match[1] is the content inside $...$)
    parts.push(<InlineMath key={keyIndex++} math={match[1]} />);
    lastIndex = match.index + match[0].length;
  }
  
  // Add remaining text
  if (lastIndex < text.length) {
    parts.push(text.substring(lastIndex));
  }
  
  return <>{parts}</>;
};

