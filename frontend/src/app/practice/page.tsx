"use client";

import { useState } from "react";

// TODO: Replace this mock object with your actual static question bank import
// Example: import { staticQuestionBank } from "@/lib/questionBank";

const mockQuestionBank: Record<string, string[]> = {
  Google: [
    "Design a URL Shortener system architecture.",
    "Explain the CAP theorem and trade-offs.",
    "Invert a binary tree in place."
  ],
  Meta: [
    "Design an Instagram feed backend infrastructure.",
    "Explain React reconciliation and the virtual DOM.",
    "Solve the merge overlapping intervals problem."
  ],
  Amazon: [
    "Design a high-throughput e-commerce checkout flow.",
    "Describe a time you dealt with ambiguity in a project.",
    "Solve the Two Sum problem efficiently."
  ]
};

export default function PracticePage() {
  const companies = Object.keys(mockQuestionBank);
  const [selectedCompany, setSelectedCompany] = useState<string>(companies[0] || "");

  const currentQuestions = mockQuestionBank[selectedCompany] || [];

  return (
    <main className="max-w-4xl mx-auto p-6 md:p-8">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Company Practice</h1>
        <p className="text-gray-600">
          Select a company to view tailored practice questions from the static question bank.
        </p>
      </header>

      {/* Company Selector */}
      <section className="mb-8">
        <label htmlFor="company-select" className="block text-sm font-medium text-gray-700 mb-2">
          Select Target Company
        </label>
        <select
          id="company-select"
          value={selectedCompany}
          onChange={(e) => setSelectedCompany(e.target.value)}
          className="w-full md:w-1/2 p-2.5 border border-gray-300 rounded-md shadow-sm text-gray-900 bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 focus:outline-none"
        >
          {companies.map((company) => (
            <option key={company} value={company}>
              {company}
            </option>
          ))}
        </select>
      </section>

      {/* Questions List */}
      <section className="space-y-4">
        <h2 className="text-xl font-semibold text-gray-800">
          {selectedCompany} Questions
        </h2>

        {currentQuestions.length > 0 ? (
          <ul className="space-y-3">
            {currentQuestions.map((question, index) => (
              <li
                key={index}
                className="p-4 border border-gray-200 rounded-lg bg-white shadow-sm text-gray-800"
              >
                {question}
              </li>
            ))}
          </ul>
        ) : (
          <div className="p-4 bg-gray-50 rounded-lg border border-gray-200 text-gray-500">
            No questions available for this company.
          </div>
        )}
      </section>
    </main>
  );
}