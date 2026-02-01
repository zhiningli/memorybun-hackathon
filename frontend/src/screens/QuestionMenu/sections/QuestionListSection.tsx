import {
  SearchIcon,
  ArrowDownUpIcon,
  ArrowUpNarrowWideIcon,
  ArrowDownWideNarrowIcon,
} from "lucide-react";
import { useState, useEffect, useMemo, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import { Separator } from "../../../components/ui/separator";
import { fetchQuestionLists } from "../../../services/api";
import { QuestionListMetadata, QuestionListDifficulty } from "../../../types/api";
import { QuestionListTable } from "./QuestionListTable";

interface Topic {
  id: number;
  label: string;
}

type SortField = "category" | "difficulty" | "duration" | null;
type SortDirection = "asc" | "desc";

export const QuestionListSection = (): JSX.Element => {
  const navigate = useNavigate();
  const [activeTopic, setActiveTopic] = useState<string>("All Topics");
  const [questionLists, setQuestionLists] = useState<QuestionListMetadata[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [completedQuestions, setCompletedQuestions] = useState<Record<number, boolean>>({});
  const [starredQuestions, setStarredQuestions] = useState<Record<number, boolean>>({});
  const [searchQuery, setSearchQuery] = useState("");
  const [sortField, setSortField] = useState<SortField>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>("asc");
  const [showSortMenu, setShowSortMenu] = useState(false);
  const sortMenuRef = useRef<HTMLDivElement>(null);

  // Fetch question lists from the backend
  useEffect(() => {
    const abortController = new AbortController();
    let isMounted = true;

    const loadQuestionLists = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await fetchQuestionLists(abortController.signal);

        // Don't update state if component unmounted or request was aborted
        if (!isMounted || abortController.signal.aborted) return;

        setQuestionLists(data);

        // Initialize completed/starred states
        const initialCompleted: Record<number, boolean> = {};
        const initialStarred: Record<number, boolean> = {};
        data.forEach((q) => {
          initialCompleted[q.id] = false;
          initialStarred[q.id] = false;
        });
        setCompletedQuestions(initialCompleted);
        setStarredQuestions(initialStarred);
      } catch (err) {
        // Don't update state if component unmounted or request was aborted
        if (!isMounted || abortController.signal.aborted) return;

        setError(err instanceof Error ? err.message : "Failed to load question lists");
      } finally {
        if (isMounted && !abortController.signal.aborted) {
          setLoading(false);
        }
      }
    };

    loadQuestionLists();

    // Cleanup: abort request and mark as unmounted
    return () => {
      isMounted = false;
      abortController.abort();
    };
  }, []);

  // Derive available topics from questionLists categories
  const availableTopics = useMemo<Topic[]>(() => {
    const categories = new Set<string>();
    questionLists.forEach((list) => {
      // Add all categories from the list
      list.categories.forEach(category => categories.add(category));
    });

    const topics: Topic[] = [{ id: 0, label: "All Topics" }];
    Array.from(categories).sort().forEach((category, index) => {
      topics.push({ id: index + 1, label: category });
    });

    return topics;
  }, [questionLists]);

  // Filter and sort question lists by topic, search query, and sort field
  const filteredQuestionLists = useMemo<QuestionListMetadata[]>(() => {
    let filtered = [...questionLists];

    // Filter by topic/category
    if (activeTopic !== "All Topics") {
      // Check if the list contains the active topic
      filtered = filtered.filter((list) =>
        list.categories.includes(activeTopic as any)
      );
    }

    // Filter by search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase().trim();
      filtered = filtered.filter((list) =>
        list.title.toLowerCase().includes(query)
      );
    }

    // Sort the filtered results
    if (sortField) {
      filtered.sort((a, b) => {
        let comparison = 0;

        switch (sortField) {
          case "category":
            // Compare based on the first category
            const catA = a.categories[0] || "";
            const catB = b.categories[0] || "";
            comparison = catA.localeCompare(catB);
            break;
          case "difficulty":
            // Map difficulty to numeric values for proper sorting
            const difficultyOrder: Record<QuestionListDifficulty, number> = {
              [QuestionListDifficulty.EASY]: 1,
              [QuestionListDifficulty.MEDIUM]: 2,
              [QuestionListDifficulty.ADVANCED]: 3,
            };
            comparison = difficultyOrder[a.difficulty] - difficultyOrder[b.difficulty];
            break;
          case "duration":
            comparison = a.duration_seconds - b.duration_seconds;
            break;
        }

        return sortDirection === "asc" ? comparison : -comparison;
      });
    }

    return filtered;
  }, [questionLists, activeTopic, searchQuery, sortField, sortDirection]);

  // Close sort menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (sortMenuRef.current && !sortMenuRef.current.contains(event.target as Node)) {
        setShowSortMenu(false);
      }
    };

    if (showSortMenu) {
      document.addEventListener("mousedown", handleClickOutside);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [showSortMenu]);

  const handleTopicClick = (topicLabel: string) => {
    setActiveTopic(topicLabel);
  };

  const handleStatusToggle = (questionId: number) => {
    setCompletedQuestions((prev) => ({
      ...prev,
      [questionId]: !prev[questionId],
    }));
  };

  const handleStarToggle = (questionId: number) => {
    setStarredQuestions((prev) => ({
      ...prev,
      [questionId]: !prev[questionId],
    }));
  };

  const handleRowClick = (questionId: number) => {
    // Clear stale session data to ensure fresh duration tracking
    sessionStorage.removeItem(`question_session_start_${questionId}`);
    sessionStorage.removeItem(`question_session_end_${questionId}`);
    localStorage.removeItem(`summary_sessions_${questionId}`);

    navigate(`/question/${questionId}`);
  };

  const handleSortClick = (field: SortField) => {
    if (sortField === field) {
      // Toggle direction if same field
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      // Set new field with ascending direction
      setSortField(field);
      setSortDirection("asc");
    }
    setShowSortMenu(false);
  };

  const handleClearSort = () => {
    setSortField(null);
    setSortDirection("asc");
    setShowSortMenu(false);
  };

  return (
    <section className="w-full flex flex-col gap-4 md:gap-6">
      <div className="flex items-center gap-2 flex-wrap">
        {availableTopics.map((topic) => {
          const isActive = activeTopic === topic.label;
          return (
            <Button
              key={topic.id}
              onClick={() => handleTopicClick(topic.label)}
              variant={isActive ? "default" : "secondary"}
              className={`h-[41px] 2xl:h-[51px] px-3.5 2xl:px-5 py-[7px] 2xl:py-3 rounded-[40px] transition-colors duration-200 ${isActive
                ? "bg-[#0052f9] hover:bg-[#0052f9]/90 text-white"
                : "bg-[#e6eeff] hover:bg-[#e6eeff]/80 text-[#1e386d99]"
                }`}
            >
              <span className="text-sm 2xl:text-lg font-medium">
                {topic.label}
              </span>
            </Button>
          );
        })}
      </div>

      <div className="flex items-center gap-3 md:gap-6">
        <div className="relative w-full sm:w-[203px] max-w-[300px]">
          <Input
            type="text"
            placeholder="Search"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="h-[34px] pl-4 pr-10 rounded-full border-[#0052f9e6] text-sm text-[#1e386d99]"
          />
          <SearchIcon className="absolute top-2.5 right-3 w-3.5 h-3.5 text-[#1e386d99]" />
        </div>

        <div className="relative" ref={sortMenuRef}>
          <Button
            variant="ghost"
            size="icon"
            className="w-6 h-6 p-0 flex-shrink-0 relative"
            onClick={() => setShowSortMenu(!showSortMenu)}
          >
            <ArrowDownUpIcon className={`w-6 h-6 ${sortField ? "text-[#0052f9]" : "text-[#1e386d]"}`} />
            {sortField && (
              <span className="absolute -top-1 -right-1 w-2 h-2 bg-[#0052f9] rounded-full" />
            )}
          </Button>

          {showSortMenu && (
            <div className="absolute left-0 top-8 z-50 bg-white border border-gray-200 rounded-lg shadow-lg py-2 min-w-[160px]">
              <button
                onClick={() => handleSortClick("category")}
                className={`w-full text-left px-4 py-2 text-sm hover:bg-gray-100 flex items-center justify-between ${sortField === "category" ? "text-[#0052f9] font-semibold" : "text-[#1e386d]"
                  }`}
              >
                <span>Category</span>
                {sortField === "category" && (
                  sortDirection === "asc" ? (
                    <ArrowUpNarrowWideIcon className="w-4 h-4" />
                  ) : (
                    <ArrowDownWideNarrowIcon className="w-4 h-4" />
                  )
                )}
              </button>
              <button
                onClick={() => handleSortClick("difficulty")}
                className={`w-full text-left px-4 py-2 text-sm hover:bg-gray-100 flex items-center justify-between ${sortField === "difficulty" ? "text-[#0052f9] font-semibold" : "text-[#1e386d]"
                  }`}
              >
                <span>Difficulty</span>
                {sortField === "difficulty" && (
                  sortDirection === "asc" ? (
                    <ArrowUpNarrowWideIcon className="w-4 h-4" />
                  ) : (
                    <ArrowDownWideNarrowIcon className="w-4 h-4" />
                  )
                )}
              </button>
              <button
                onClick={() => handleSortClick("duration")}
                className={`w-full text-left px-4 py-2 text-sm hover:bg-gray-100 flex items-center justify-between ${sortField === "duration" ? "text-[#0052f9] font-semibold" : "text-[#1e386d]"
                  }`}
              >
                <span>Duration</span>
                {sortField === "duration" && (
                  sortDirection === "asc" ? (
                    <ArrowUpNarrowWideIcon className="w-4 h-4" />
                  ) : (
                    <ArrowDownWideNarrowIcon className="w-4 h-4" />
                  )
                )}
              </button>
              {sortField && (
                <>
                  <div className="border-t border-gray-200 my-1" />
                  <button
                    onClick={handleClearSort}
                    className="w-full text-left px-4 py-2 text-sm hover:bg-gray-100 text-[#1e386d]"
                  >
                    Clear Sort
                  </button>
                </>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="flex flex-col overflow-x-auto">
        <Separator className="bg-[#d9d9d9]" />

        <QuestionListTable
          rows={filteredQuestionLists}
          completed={completedQuestions}
          starred={starredQuestions}
          onToggleCompleted={handleStatusToggle}
          onToggleStarred={handleStarToggle}
          onRowClick={handleRowClick}
          loading={loading}
          error={error}
        />
      </div>
    </section>
  );
};
