"use client";

import { useEffect, useMemo, useState } from "react";
import { endpoints } from "@/lib/api";

export default function QuestionsPage() {
  const [questions, setQuestions] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState("All");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    loadQuestions();
  }, []);

  async function loadQuestions() {
    try {
      setLoading(true);
      setError("");

      const response = await fetch(
        "http://localhost:8000/questions?limit=100"
      );

      if (!response.ok) {
        throw new Error(`Failed to load questions (${response.status})`);
      }

      const data = await response.json();

      setQuestions(data.questions || []);
    } catch (err) {
      setError(err.message || "Unable to load questions");
    } finally {
      setLoading(false);
    }
  }

  const groupedQuestions = useMemo(() => {
    const groups = {};

    questions.forEach((question) => {
      const category = question.category || "General";

      if (!groups[category]) {
        groups[category] = [];
      }

      groups[category].push(question);
    });

    return groups;
  }, [questions]);

  const filteredGroups = useMemo(() => {
    const result = {};

    Object.entries(groupedQuestions).forEach(([category, items]) => {
      const filtered = items.filter((question) => {
        const text = (
          question.text ||
          question.question ||
          ""
        ).toLowerCase();

        return text.includes(search.toLowerCase());
      });

      if (filtered.length > 0) {
        result[category] = filtered;
      }
    });

    return result;
  }, [groupedQuestions, search]);

  const visibleGroups =
    selectedCategory === "All"
      ? filteredGroups
      : {
          [selectedCategory]:
            filteredGroups[selectedCategory] || [],
        };

  const totalVisible = Object.values(visibleGroups).reduce(
    (total, items) => total + items.length,
    0
  );

  return (
    <main className="min-h-screen bg-gray-50 p-6">
      <div className="mx-auto max-w-7xl">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900">
            Question Categorization
          </h1>

          <p className="mt-2 text-gray-600">
            View and organize interview questions by category.
          </p>
        </div>

        {/* Controls */}
        <div className="mb-6 rounded-xl bg-white p-4 shadow-sm">
          <div className="flex flex-col gap-4 md:flex-row">
            <input
              type="text"
              placeholder="Search questions..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="flex-1 rounded-lg border border-gray-300 px-4 py-2 outline-none focus:border-indigo-500"
            />

            <select
              value={selectedCategory}
              onChange={(e) =>
                setSelectedCategory(e.target.value)
              }
              className="rounded-lg border border-gray-300 px-4 py-2"
            >
              <option value="All">All Categories</option>
              {Object.keys(groupedQuestions).map((category) => (
                <option key={category} value={category}>
                  {category}
                </option>
              ))}
            </select>

            <button
              onClick={loadQuestions}
              className="rounded-lg bg-indigo-600 px-5 py-2 font-medium text-white hover:bg-indigo-700"
            >
              Refresh
            </button>
          </div>

          <div className="mt-4 text-sm text-gray-500">
            Showing{" "}
            <span className="font-semibold text-gray-900">
              {totalVisible}
            </span>{" "}
            question{totalVisible === 1 ? "" : "s"}
          </div>
        </div>

        {/* Loading */}
        {loading && (
          <div className="rounded-xl bg-white p-8 text-center shadow-sm">
            Loading questions...
          </div>
        )}

        {/* Error */}
        {!loading && error && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-6">
            <h2 className="font-semibold text-red-700">
              Unable to load questions
            </h2>

            <p className="mt-2 text-sm text-red-600">
              {error}
            </p>

            <button
              onClick={loadQuestions}
              className="mt-4 rounded-lg bg-red-600 px-4 py-2 text-white"
            >
              Try Again
            </button>
          </div>
        )}

        {/* Empty */}
        {!loading &&
          !error &&
          totalVisible === 0 && (
            <div className="rounded-xl bg-white p-10 text-center shadow-sm">
              <h2 className="text-lg font-semibold text-gray-800">
                No questions found
              </h2>

              <p className="mt-2 text-gray-500">
                Try another category or search term.
              </p>
            </div>
          )}

        {/* Question groups */}
        {!loading &&
          !error &&
          totalVisible > 0 && (
            <div className="space-y-6">
              {Object.entries(visibleGroups).map(
                ([category, items]) => (
                  <section
                    key={category}
                    className="rounded-xl bg-white p-6 shadow-sm"
                  >
                    {/* Category heading */}
                    <div className="mb-4 flex items-center justify-between">
                      <div>
                        <h2 className="text-xl font-bold text-gray-900">
                          {category}
                        </h2>

                        <p className="text-sm text-gray-500">
                          {items.length} question
                          {items.length === 1 ? "" : "s"}
                        </p>
                      </div>

                      <span className="rounded-full bg-indigo-100 px-3 py-1 text-sm font-medium text-indigo-700">
                        {category}
                      </span>
                    </div>

                    {/* Questions */}
                    <div className="space-y-3">
                      {items.map((question, index) => (
                        <div
                          key={
                            question.id ||
                            question.question_id ||
                            `${category}-${index}`
                          }
                          className="rounded-lg border border-gray-200 p-4 hover:bg-gray-50"
                        >
                          <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                            <div className="flex-1">
                              <p className="font-medium text-gray-900">
                                {question.text ||
                                  question.question ||
                                  "Untitled question"}
                              </p>

                              {question.tags?.length > 0 && (
                                <div className="mt-3 flex flex-wrap gap-2">
                                  {question.tags.map((tag) => (
                                    <span
                                      key={tag}
                                      className="rounded-full bg-gray-100 px-2 py-1 text-xs text-gray-600"
                                    >
                                      #{tag}
                                    </span>
                                  ))}
                                </div>
                              )}
                            </div>

                            <div className="flex gap-2">
                              {question.difficulty && (
                                <span className="rounded-full bg-yellow-100 px-3 py-1 text-xs font-medium text-yellow-700">
                                  {question.difficulty}
                                </span>
                              )}

                              <span className="rounded-full bg-green-100 px-3 py-1 text-xs font-medium text-green-700">
                                {category}
                              </span>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </section>
                )
              )}
            </div>
          )}
      </div>
    </main>
  );
}