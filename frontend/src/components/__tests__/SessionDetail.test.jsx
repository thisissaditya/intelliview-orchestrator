import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import SessionDetail from "../SessionDetail";
import * as exportLib from "@/lib/export";
import * as toastLib from "@/lib/toast";
import useSWR from "swr";

// Mock SWR
vi.mock("swr");

// Mock the export functions
vi.mock("@/lib/export", () => ({
  generateSessionPDF: vi.fn(),
  requestBackendPDF: vi.fn(),
}));

// Mock the toast function
vi.mock("@/lib/toast", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

// Mock the store
vi.mock("@/lib/store", () => ({
  useAppStore: vi.fn(() => ({
    token: "mock-token",
  })),
}));

// Mock the components that SessionDetail uses
vi.mock("@/components/Dialog", () => ({
  Dialog: ({ children, open }) => (open ? <div data-testid="dialog">{children}</div> : null),
  DialogContent: ({ children }) => <div data-testid="dialog-content">{children}</div>,
  DialogTitle: ({ children }) => <h2 data-testid="dialog-title">{children}</h2>,
}));

vi.mock("@/components/Pipeline", () => ({
  default: () => <div data-testid="pipeline">Pipeline</div>,
}));

vi.mock("@/components/Badge", () => ({
  StatusBadge: ({ status }) => <span data-testid="status-badge">{status}</span>,
  Badge: ({ children }) => <span data-testid="badge">{children}</span>,
}));

vi.mock("@/components/Shimmer", () => ({
  Shimmer: () => <div data-testid="shimmer">Loading...</div>,
}));

vi.mock("@/hooks/useMomentTracking", () => ({
  MomentTimeline: () => <div data-testid="moment-timeline">Timeline</div>,
}));

vi.mock("@/lib/utils", () => ({
  formatDate: (date) => date || "N/A",
  riskColor: () => "default",
  formatRelative: (date) => date || "N/A",
}));

vi.mock("./Button", () => ({
  default: ({ children, onClick, disabled, "aria-label": ariaLabel }) => (
    <button onClick={onClick} disabled={disabled} aria-label={ariaLabel}>
      {children}
    </button>
  ),
}));

describe("SessionDetail Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading state when data hasn't loaded", () => {
    useSWR.mockImplementation(() => ({
      data: null,
      error: null,
      isLoading: true,
      mutate: vi.fn(),
    }));

    render(<SessionDetail sessionId="sess-123" onClose={vi.fn()} />);

    expect(screen.getAllByTestId("shimmer")).toHaveLength(3);
  });

  it("disables Export PDF button while data is loading", () => {
    useSWR.mockImplementation(() => ({
      data: null,
      error: null,
      isLoading: true,
      mutate: vi.fn(),
    }));

    render(<SessionDetail sessionId="sess-123" onClose={vi.fn()} />);

    const exportButton = screen.getByLabelText("Export PDF");
    expect(exportButton).toBeDisabled();
  });

  it("enables Export PDF button when data is loaded", () => {
    useSWR.mockImplementation(() => ({
      data: {
        session_id: "sess-123",
        candidate_id: "cand-456",
        status: "COMPLETED",
        risk_score: 0.5,
      },
      error: null,
      isLoading: false,
      mutate: vi.fn(),
    }));

    render(<SessionDetail sessionId="sess-123" onClose={vi.fn()} />);

    const exportButton = screen.getByLabelText("Export PDF");
    expect(exportButton).not.toBeDisabled();
  });

  it("calls requestBackendPDF on Export PDF click (backend success)", async () => {
    const mockData = {
      session_id: "sess-123",
      candidate_id: "cand-456",
      status: "COMPLETED",
      risk_score: 0.5,
    };

    useSWR.mockImplementation(() => ({
      data: mockData,
      error: null,
      isLoading: false,
      mutate: vi.fn(),
    }));

    exportLib.requestBackendPDF.mockResolvedValue(undefined);

    render(<SessionDetail sessionId="sess-123" onClose={vi.fn()} />);

    const exportButton = screen.getByLabelText("Export PDF");
    fireEvent.click(exportButton);

    await waitFor(() => {
      expect(exportLib.requestBackendPDF).toHaveBeenCalledWith("sess-123");
    });

    await waitFor(() => {
      expect(toastLib.toast.success).toHaveBeenCalledWith(
        "Complex report generated successfully"
      );
    });

    // Should NOT call generateSessionPDF when backend succeeds
    expect(exportLib.generateSessionPDF).not.toHaveBeenCalled();
  });

  it("falls back to generateSessionPDF when backend fails", async () => {
    const mockData = {
      session_id: "sess-456",
      candidate_id: "cand-789",
      status: "COMPLETED",
      risk_score: 0.3,
    };

    useSWR.mockImplementation(() => ({
      data: mockData,
      error: null,
      isLoading: false,
      mutate: vi.fn(),
    }));

    exportLib.requestBackendPDF.mockRejectedValue(new Error("Backend failed"));
    exportLib.generateSessionPDF.mockResolvedValue(undefined);

    render(<SessionDetail sessionId="sess-456" onClose={vi.fn()} />);

    const exportButton = screen.getByLabelText("Export PDF");
    fireEvent.click(exportButton);

    await waitFor(() => {
      expect(exportLib.requestBackendPDF).toHaveBeenCalledWith("sess-456");
    });

    await waitFor(() => {
      expect(exportLib.generateSessionPDF).toHaveBeenCalledWith(mockData);
    });

    await waitFor(() => {
      expect(toastLib.toast.success).toHaveBeenCalledWith(
        "Basic report generated successfully"
      );
    });
  });

  it("shows error toast when both backend and fallback fail", async () => {
    const mockData = {
      session_id: "sess-789",
      candidate_id: "cand-012",
      status: "COMPLETED",
      risk_score: 0.7,
    };

    useSWR.mockImplementation(() => ({
      data: mockData,
      error: null,
      isLoading: false,
      mutate: vi.fn(),
    }));

    exportLib.requestBackendPDF.mockRejectedValue(new Error("Backend failed"));
    exportLib.generateSessionPDF.mockRejectedValue(new Error("Fallback failed"));

    render(<SessionDetail sessionId="sess-789" onClose={vi.fn()} />);

    const exportButton = screen.getByLabelText("Export PDF");
    fireEvent.click(exportButton);

    await waitFor(() => {
      expect(toastLib.toast.error).toHaveBeenCalledWith("Failed to export PDF");
    });
  });

  it("disables Export PDF button while export is in progress", async () => {
    const mockData = {
      session_id: "sess-abc",
      candidate_id: "cand-def",
      status: "COMPLETED",
      risk_score: 0.4,
    };

    useSWR.mockImplementation(() => ({
      data: mockData,
      error: null,
      isLoading: false,
      mutate: vi.fn(),
    }));

    // Make requestBackendPDF hang so we can check button state during export
    let resolveExport;
    exportLib.requestBackendPDF.mockReturnValue(
      new Promise((resolve) => {
        resolveExport = resolve;
      })
    );

    render(<SessionDetail sessionId="sess-abc" onClose={vi.fn()} />);

    const exportButton = screen.getByLabelText("Export PDF");
    expect(exportButton).not.toBeDisabled();

    fireEvent.click(exportButton);

    // Button should be disabled during export
    await waitFor(() => {
      expect(exportButton).toBeDisabled();
    });

    // Resolve the export
    resolveExport();

    // Button should be enabled again after export completes
    await waitFor(() => {
      expect(exportButton).not.toBeDisabled();
    });
  });
});
