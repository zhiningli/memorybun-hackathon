declare module 'react-katex' {
  import { FC, ReactNode } from 'react';
  
  interface MathProps {
    math: string;
    block?: boolean;
    errorColor?: string;
    renderError?: (error: Error) => ReactNode;
  }
  
  export const InlineMath: FC<MathProps>;
  export const BlockMath: FC<MathProps>;
}

declare module 'katex/dist/katex.min.css';

