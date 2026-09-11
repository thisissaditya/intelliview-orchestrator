import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import InterviewPage from "../page";

vi.mock("swr", () => ({
  default: () => ({ data: null, error: null, isLoading: false }),
}));

vi.mock("@/lib/store", () => ({
  useAppStore: (selector) => selector({ token: "test-token" }),
}));

vi.mock("@/lib/api", () => ({
  endpoints: {
    startInterview: vi.fn(),
  },
}));

vi.mock("@/lib/toast", () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
    warn: vi.fn(),
  },
}));

vi.mock("@/hooks/useWebSocket", () => ({
  useWebSocket: () => ({
    connected: true,
    reconnecting: false,
    retryAttempt: 0,
    error: null,
  }),
}));

vi.mock("@/hooks/useMomentTracking", () => ({
  useMomentTracking: () => ({
    moments: [],
    isTracking: false,
    startTracking: vi.fn(),
    stopTracking: vi.fn(),
    trackEvent: vi.fn(),
  }),
}));

vi.mock("@/components/Card", () => ({
  default: ({ children, title }) => (
    <section>
      <h2>{title}</h2>
      {children}
    </section>
  ),
}));

vi.mock("@/components/Badge", () => ({
  Badge: ({ children }) => <span>{children}</span>,
}));

vi.mock("@/components/States", () => ({
  Skeleton: () => <div />,
  ErrorState: () => <div />,
  EmptyState: () => <div />,
}));

vi.mock("@/components/VideoPlayer", () => ({
  default: () => <div>Video Player</div>,
}));

vi.mock("@/components/RiskTimeline", () => ({
  default: () => <div>Risk Timeline</div>,
}));

vi.mock("@/components/ErrorBoundary", () => ({
  ErrorBoundary: ({ children }) => <>{children}</>,
}));

vi.mock("lucide-react", () => ({
  Video: () => <span />,
  VideoOff: () => <span />,
  Mic: () => <span />,
  MicOff: () => <span />,
  Phone: () => <span />,
  PhoneOff: () => <span />,
  Pause: () => <span />,
  Play: () => <span />,
  AlertTriangle: () => <span />,
  Activity: () => <span />,
  Radio: () => <span />,
  Volume2: () => <span />,
}));

describe("InterviewPage voice error handling", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: {
        getUserMedia: vi.fn(),
      },
    });

    window.AudioContext = vi.fn(() => ({
      createMediaStreamSource: vi.fn(() => ({
        connect: vi.fn(),
      })),
      createAnalyser: vi.fn(() => ({
        fftSize: 64,
        frequencyBinCount: 32,
        getByteFrequencyData: vi.fn(),
      })),
      close: vi.fn(),
    }));

    window.requestAnimationFrame = vi.fn(() => 1);
    window.cancelAnimationFrame = vi.fn();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("shows a clear message when microphone permission is denied", async () => {
    const { endpoints } = await import("@/lib/api");

    endpoints.startInterview.mockResolvedValue({
      session_id: "session-123",
    });

    navigator.mediaDevices.getUserMedia.mockRejectedValue(
      Object.assign(new Error("Permission denied"), {
        name: "NotAllowedError",
      })
    );

    render(<InterviewPage />);

    fireEvent.change(screen.getByPlaceholderText("cand-1234"), {
      target: { value: "candidate-1" },
    });

    fireEvent.click(
      screen.getByRole("button", { name: /start interview/i })
    );

    expect(
      await screen.findByText(
        "Microphone and camera permission is required. Please allow access and try again."
      )
    ).toBeInTheDocument();
  });

  it("retries recoverable microphone failures before showing an error", async () => {
    const { endpoints } = await import("@/lib/api");

    endpoints.startInterview.mockResolvedValue({
      session_id: "session-456",
    });

    navigator.mediaDevices.getUserMedia
      .mockRejectedValueOnce(
        Object.assign(new Error("Device busy"), {
          name: "NotReadableError",
        })
      )
      .mockRejectedValueOnce(
        Object.assign(new Error("Device busy"), {
          name: "NotReadableError",
        })
      )
      .mockRejectedValueOnce(
        Object.assign(new Error("Device busy"), {
          name: "NotReadableError",
        })
      );

    render(<InterviewPage />);

    fireEvent.change(screen.getByPlaceholderText("cand-1234"), {
      target: { value: "candidate-2" },
    });

    fireEvent.click(
      screen.getByRole("button", { name: /start interview/i })
    );

    await waitFor(
    () => {
      expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalledTimes(3);
    },
    { timeout: 3000 }
  );
    expect(
      await screen.findByText(
        "The microphone or camera is currently unavailable. Please close other apps using it and try again."
      )
    ).toBeInTheDocument();
  });
});
