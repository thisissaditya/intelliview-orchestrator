import React from "react";
import { render, screen, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { useWebSocket } from "../useWebSocket";

vi.mock("@/lib/api", () => ({
  api: {
    wsUrl: vi.fn(() => "ws://localhost:8000/test"),
  },
}));

function TestComponent() {
  const {
    connected,
    reconnecting,
    retryAttempt,
    error,
  } = useWebSocket({
    path: "/test",
    enabled: true,
  });

  return (
    <div>
      <span data-testid="connected">{String(connected)}</span>
      <span data-testid="reconnecting">{String(reconnecting)}</span>
      <span data-testid="retryAttempt">{retryAttempt}</span>
      <span data-testid="error">{error || ""}</span>
    </div>
  );
}

describe("useWebSocket voice error handling", () => {
  let sockets = [];

  beforeEach(() => {
    vi.useFakeTimers();
    sockets = [];

    class MockWebSocket {
      static OPEN = 1;
      static CONNECTING = 0;
      static CLOSED = 3;

      constructor() {
        this.readyState = MockWebSocket.CONNECTING;
        this.send = vi.fn();

        this.close = vi.fn(() => {
          this.readyState = MockWebSocket.CLOSED;
          this.onclose?.();
        });

        sockets.push(this);
      }
    }

    globalThis.WebSocket = MockWebSocket;
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("shows an error and automatically retries after a network drop", async () => {
    render(<TestComponent />);

    expect(sockets).toHaveLength(1);

    await act(async () => {
      sockets[0].readyState = WebSocket.OPEN;
      sockets[0].onopen?.();
    });

    expect(screen.getByTestId("connected")).toHaveTextContent("true");

    await act(async () => {
      sockets[0].onerror?.();
      sockets[0].onclose?.();
    });

    expect(screen.getByTestId("connected")).toHaveTextContent("false");
    expect(screen.getByTestId("reconnecting")).toHaveTextContent("true");
    expect(screen.getByTestId("error")).toHaveTextContent(
      "Voice stream connection failed."
    );

    await act(async () => {
      vi.advanceTimersByTime(500);
    });

    expect(sockets).toHaveLength(2);
    expect(screen.getByTestId("retryAttempt")).toHaveTextContent("1");

    await act(async () => {
      sockets[1].readyState = WebSocket.OPEN;
      sockets[1].onopen?.();
    });

    expect(screen.getByTestId("connected")).toHaveTextContent("true");
    expect(screen.getByTestId("reconnecting")).toHaveTextContent("false");
    expect(screen.getByTestId("retryAttempt")).toHaveTextContent("0");
    expect(screen.getByTestId("error")).toHaveTextContent("");
  });
});