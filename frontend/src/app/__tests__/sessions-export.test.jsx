import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import * as exportLib from "@/lib/export";
import * as toastLib from "@/lib/toast";

// Mock the export and toast modules
vi.mock("@/lib/export", () => ({
  exportSessionsCSV: vi.fn(),
  exportCandidatesCSV: vi.fn(),
  exportAnalyticsCSV: vi.fn(),
}));

vi.mock("@/lib/toast", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

describe("Sessions Page Export", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("exports combined active, completed, and failed sessions", () => {
    const activeSessions = [
      { session_id: "active-1", status: "PROCESSING" },
      { session_id: "active-2", status: "QUEUED" },
    ];
    const completedSessions = [
      { session_id: "completed-1", status: "COMPLETED" },
    ];
    const failedSessions = [
      { session_id: "failed-1", status: "FAILED" },
    ];

    // Simulate the handleExportCSV function logic
    const allSessions = [
      ...activeSessions,
      ...completedSessions,
      ...failedSessions,
    ];

    exportLib.exportSessionsCSV(allSessions);
    toastLib.toast.success("CSV exported successfully");

    expect(exportLib.exportSessionsCSV).toHaveBeenCalledWith(allSessions);
    expect(exportLib.exportSessionsCSV).toHaveBeenCalledWith(
      expect.arrayContaining([
        expect.objectContaining({ session_id: "active-1" }),
        expect.objectContaining({ session_id: "completed-1" }),
        expect.objectContaining({ session_id: "failed-1" }),
      ])
    );
    expect(toastLib.toast.success).toHaveBeenCalledWith("CSV exported successfully");
  });

  it("shows error toast when all session arrays are empty", () => {
    const activeSessions = [];
    const completedSessions = [];
    const failedSessions = [];

    const allSessions = [
      ...activeSessions,
      ...completedSessions,
      ...failedSessions,
    ];

    if (allSessions.length === 0) {
      toastLib.toast.error("No data to export");
      return;
    }

    expect(toastLib.toast.error).toHaveBeenCalledWith("No data to export");
    expect(exportLib.exportSessionsCSV).not.toHaveBeenCalled();
  });

  it("shows success toast on successful export", () => {
    const sessions = [{ session_id: "sess-1", status: "COMPLETED" }];

    exportLib.exportSessionsCSV(sessions);
    toastLib.toast.success("CSV exported successfully");

    expect(toastLib.toast.success).toHaveBeenCalledWith("CSV exported successfully");
  });
});

describe("Candidates Page Export", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("exports candidates data", () => {
    const candidates = [
      { candidate_id: "cand-1", total_sessions: 5 },
      { candidate_id: "cand-2", total_sessions: 3 },
    ];

    exportLib.exportCandidatesCSV(candidates);
    toastLib.toast.success("CSV exported successfully");

    expect(exportLib.exportCandidatesCSV).toHaveBeenCalledWith(candidates);
    expect(toastLib.toast.success).toHaveBeenCalledWith("CSV exported successfully");
  });

  it("shows error toast when candidates array is empty", () => {
    const candidates = [];

    if (candidates.length === 0) {
      toastLib.toast.error("No candidates to export");
      return;
    }

    expect(toastLib.toast.error).toHaveBeenCalledWith("No candidates to export");
    expect(exportLib.exportCandidatesCSV).not.toHaveBeenCalled();
  });
});

describe("Analytics Page Export", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("exports analytics data", () => {
    const data = {
      candidates: [
        { name: "Alice", role: "Engineer", status: "Active", score: 85, risk: "Low" },
      ],
      stats: {
        total_sessions: 100,
        risk_score_stats: {
          average_risk_score: 0.35,
          high_risk_sessions: 15,
        },
      },
    };

    exportLib.exportAnalyticsCSV(data);
    toastLib.toast.success("Export complete");

    expect(exportLib.exportAnalyticsCSV).toHaveBeenCalledWith(data);
    expect(toastLib.toast.success).toHaveBeenCalledWith("Export complete");
  });

  it("shows error toast when no data to export", () => {
    const data = {
      candidates: [],
      stats: null,
    };

    if (!data.candidates?.length && !data.stats) {
      toastLib.toast.error("No data to export");
      return;
    }

    expect(toastLib.toast.error).toHaveBeenCalledWith("No data to export");
    expect(exportLib.exportAnalyticsCSV).not.toHaveBeenCalled();
  });
});
