"use client";

import { useState, useMemo } from "react";
import Card from "@/components/Card";
import { Badge } from "@/components/Badge";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import {
  Sparkles,
  Wrench,
  Bug,
  Calendar,
  History,
  CheckCircle2,
  Filter
} from "lucide-react";

/**
 * Static Changelog Data Source
 * 
 * To add a new entry manually:
 * Insert a new object at the top of the `CHANGELOG_DATA` array below.
 */
export const CHANGELOG_DATA = [
  {
    id: "unreleased",
    version: "Unreleased",
    date: "2026-08-26",
    title: "Production Hardening & System Enhancements",
    features: [
      "Added in-app changelog page (/changelog) for tracking platform releases and updates.",
      "Added production hardening with connection pool management (pool_pre_ping & pool_recycle) for database resilience.",
      "Added graceful lifespan shutdown for Redis-backed resources.",
      "Added token authentication on privileged admin endpoints.",
      "Added deterministic signal generation for RiskScoringEngine and AI pipelines (video, audio, evaluation).",
      "Added skip-to-content accessibility link, focus trap, and prefers-reduced-motion support across UI components.",
      "Added hallucination detection module using semantic similarity and NLI entailment in evaluation pipeline (#67)."
    ],
    improvements: [
      "Updated analytics Risk Distribution pie chart to read live per-session risk scores.",
      "Replaced worker entrypoints with streamlined worker_entrypoint.py architecture.",
      "Updated Docker containers to run as non-root with explicit HEALTHCHECK configurations.",
      "Expanded CI checks including ruff format, mypy typechecking, and production Next.js builds."
    ],
    fixes: [
      "Fixed RiskScoringEngine returning 0.0 scores by ensuring non-trivial boolean signals fire correctly.",
      "Fixed missing logging handler cleanups during module import."
    ]
  },
  {
    id: "v0.2.0",
    version: "v0.2.0",
    date: "2026-06-21",
    title: "UI Refresh & Platform Metrics",
    features: [
      "Added command palette (cmdk), mobile navigation sidebar, and keyboard shortcuts help dialog.",
      "Added session detail modal with live polling and search filters.",
      "Added structured JSON logging and request ID tracing middleware (X-Request-ID).",
      "Added Prometheus-style metric collector hooks."
    ],
    improvements: [
      "Migrated all backend read paths to SQLAlchemy 2.0 select() syntax.",
      "Tightened StartInterviewRequest request body validation rules."
    ],
    fixes: [
      "Wrapped bare exception clauses across API service handlers with narrow error types."
    ]
  },
  {
    id: "v0.1.0",
    version: "v0.1.0",
    date: "2026-06-01",
    title: "Initial Orchestrator Release",
    features: [
      "Initial launch of AI-Intelliview Orchestrator featuring FastAPI backend, Celery worker pool, Redis cache, and Next.js dashboard."
    ],
    improvements: [],
    fixes: []
  }
];

export default function ChangelogPage() {
  const [selectedCategory, setSelectedCategory] = useState("ALL");

  const filteredEntries = useMemo(() => {
    if (selectedCategory === "ALL") return CHANGELOG_DATA;

    return CHANGELOG_DATA.map((entry) => {
      if (selectedCategory === "FEATURES") {
        return { ...entry, improvements: [], fixes: [] };
      }
      if (selectedCategory === "IMPROVEMENTS") {
        return { ...entry, features: [], fixes: [] };
      }
      if (selectedCategory === "FIXES") {
        return { ...entry, features: [], improvements: [] };
      }
      return entry;
    }).filter((entry) => {
      return (
        (entry.features && entry.features.length > 0) ||
        (entry.improvements && entry.improvements.length > 0) ||
        (entry.fixes && entry.fixes.length > 0)
      );
    });
  }, [selectedCategory]);

  return (
    <ErrorBoundary>
      <div className="mx-auto max-w-4xl space-y-6">
        {/* Header section */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-border pb-5">
          <div>
            <div className="flex items-center gap-2">
              <History className="h-6 w-6 text-accent" />
              <h1 className="text-xl font-semibold text-zinc-100">Changelog</h1>
            </div>
            <p className="mt-1 text-sm text-muted">
              Discover recent updates, new features, enhancements, and bug fixes in IntelliView.
            </p>
          </div>

          {/* Category Filter Pills */}
          <div className="flex flex-wrap items-center gap-1.5 rounded-lg border border-border bg-bg-panel p-1">
            <button
              onClick={() => setSelectedCategory("ALL")}
              className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-all ${
                selectedCategory === "ALL"
                  ? "bg-accent text-white shadow-sm"
                  : "text-zinc-400 hover:bg-bg-card hover:text-zinc-200"
              }`}
            >
              <Filter size={12} />
              All
            </button>
            <button
              onClick={() => setSelectedCategory("FEATURES")}
              className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-all ${
                selectedCategory === "FEATURES"
                  ? "bg-indigo-600 text-white shadow-sm"
                  : "text-zinc-400 hover:bg-bg-card hover:text-zinc-200"
              }`}
            >
              <Sparkles size={12} className="text-indigo-300" />
              Features
            </button>
            <button
              onClick={() => setSelectedCategory("IMPROVEMENTS")}
              className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-all ${
                selectedCategory === "IMPROVEMENTS"
                  ? "bg-amber-600 text-white shadow-sm"
                  : "text-zinc-400 hover:bg-bg-card hover:text-zinc-200"
              }`}
            >
              <Wrench size={12} className="text-amber-300" />
              Improvements
            </button>
            <button
              onClick={() => setSelectedCategory("FIXES")}
              className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-all ${
                selectedCategory === "FIXES"
                  ? "bg-rose-600 text-white shadow-sm"
                  : "text-zinc-400 hover:bg-bg-card hover:text-zinc-200"
              }`}
            >
              <Bug size={12} className="text-rose-300" />
              Fixes
            </button>
          </div>
        </div>

        {/* Changelog Entries List */}
        {filteredEntries.length === 0 ? (
          <Card className="text-center py-12">
            <p className="text-sm text-muted">No updates found for the selected category filter.</p>
          </Card>
        ) : (
          <div className="space-y-6">
            {filteredEntries.map((entry) => {
              const hasFeatures = entry.features && entry.features.length > 0;
              const hasImprovements = entry.improvements && entry.improvements.length > 0;
              const hasFixes = entry.fixes && entry.fixes.length > 0;

              return (
                <Card
                  key={entry.id}
                  title={
                    <div className="flex flex-wrap items-center gap-3">
                      <span className="text-base font-semibold text-zinc-100">
                        {entry.version}
                      </span>
                      {entry.title && (
                        <span className="text-sm font-normal text-zinc-400">
                          — {entry.title}
                        </span>
                      )}
                    </div>
                  }
                  action={
                    <div className="flex items-center gap-2 text-xs text-muted">
                      <Calendar size={14} className="text-zinc-400" />
                      <span>{entry.date}</span>
                    </div>
                  }
                >
                  <div className="space-y-5">
                    {/* Features Section */}
                    {hasFeatures && (
                      <div className="space-y-2">
                        <div className="flex items-center gap-2">
                          <Badge variant="accent">
                            <Sparkles size={12} className="mr-1 inline-block" />
                            Features
                          </Badge>
                        </div>
                        <ul className="space-y-2 pl-1">
                          {entry.features.map((item, idx) => (
                            <li key={idx} className="flex items-start gap-2 text-sm text-zinc-300">
                              <CheckCircle2 size={15} className="mt-0.5 shrink-0 text-indigo-400" />
                              <span>{item}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Improvements Section */}
                    {hasImprovements && (
                      <div className="space-y-2">
                        <div className="flex items-center gap-2">
                          <Badge variant="warn">
                            <Wrench size={12} className="mr-1 inline-block" />
                            Improvements
                          </Badge>
                        </div>
                        <ul className="space-y-2 pl-1">
                          {entry.improvements.map((item, idx) => (
                            <li key={idx} className="flex items-start gap-2 text-sm text-zinc-300">
                              <CheckCircle2 size={15} className="mt-0.5 shrink-0 text-amber-400" />
                              <span>{item}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Fixes Section */}
                    {hasFixes && (
                      <div className="space-y-2">
                        <div className="flex items-center gap-2">
                          <Badge variant="danger">
                            <Bug size={12} className="mr-1 inline-block" />
                            Fixes
                          </Badge>
                        </div>
                        <ul className="space-y-2 pl-1">
                          {entry.fixes.map((item, idx) => (
                            <li key={idx} className="flex items-start gap-2 text-sm text-zinc-300">
                              <CheckCircle2 size={15} className="mt-0.5 shrink-0 text-rose-400" />
                              <span>{item}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </ErrorBoundary>
  );
}
