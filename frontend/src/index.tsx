import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QuestionMenu } from "./screens/QuestionMenu";
import { QuestionSample } from "./screens/QuestionSample";
import { SummaryReport } from "./screens/SummaryReport";

createRoot(document.getElementById("app") as HTMLElement).render(
  <StrictMode>
    <BrowserRouter
      future={{
        v7_startTransition: true,
        v7_relativeSplatPath: true,
      }}
    >
      <Routes>
        <Route path="/" element={<QuestionMenu />} />
        <Route path="/question/:id" element={<QuestionSample />} />
        <Route path="/question/:id/:partId" element={<QuestionSample />} />
        <Route path="/question/:id/summary_report" element={<SummaryReport />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>,
);