import React from "react";
import { render, screen, act } from "@testing-library/react";
import { describe, it, expect, vi, afterEach } from "vitest";
import VoiceInterviewUI, {
  VoiceInterviewUIDemo,
} from "../VoiceInterviewUI";

vi.mock("@/components/Card", () => ({
  default: ({ children, title }) => (
    <section>
      <h2>{title}</h2>
      {children}
    </section>
  ),
}));

describe("VoiceInterviewUI Component", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders voice interview interface", () => {
    render(<VoiceInterviewUI />);

    expect(screen.getByText("Voice Interview")).toBeInTheDocument();
    expect(screen.getByText("Question")).toBeInTheDocument();
    expect(screen.getByText("Live Transcript")).toBeInTheDocument();
  });

  it("shows asking state by default", () => {
    render(<VoiceInterviewUI />);

    expect(screen.getByText("Asking")).toBeInTheDocument();
    expect(
      screen.getByText("The interviewer is asking a question.")
    ).toBeInTheDocument();
  });

  it("renders standalone demo component and updates interview state", async () => {
    vi.useFakeTimers();

    render(<VoiceInterviewUIDemo />);

    expect(screen.getByText("Asking")).toBeInTheDocument();

    await act(async () => {
      vi.advanceTimersByTime(3000);
    });

    expect(screen.getByText("Listening")).toBeInTheDocument();

    await act(async () => {
      vi.advanceTimersByTime(3000);
    });

    expect(screen.getByText("Processing")).toBeInTheDocument();
  });
});