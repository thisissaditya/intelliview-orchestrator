import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import AddToCalendarButton from "../AddToCalendarButton";
import * as generateIcsLib from "@/lib/generateIcs";

// Mock the .ics download logic — this component test only cares that it's
// called with the right data, not the .ics format itself (covered separately
// in generateIcs.test.js).
vi.mock("@/lib/generateIcs", () => ({
  downloadIcsFile: vi.fn(),
}));

// Mock the shared Button so this test isn't coupled to its internal markup.
vi.mock("../Button", () => ({
  default: ({ children, onClick, className }) => (
    <button onClick={onClick} className={className}>
      {children}
    </button>
  ),
}));

describe("AddToCalendarButton", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the button label", () => {
    render(<AddToCalendarButton title="Interview" start="2026-09-01T10:00:00Z" />);
    expect(screen.getByText("Add to Calendar")).toBeInTheDocument();
  });

  it("calls downloadIcsFile with the correct event details on click", () => {
    render(
      <AddToCalendarButton
        title="Interview: Jane Doe"
        start="2026-09-01T10:00:00Z"
        durationMinutes={45}
        interviewerName="Alex Kim"
        candidateName="Jane Doe"
        location="https://meet.example.com/abc"
        notes="Bring laptop"
      />,
    );

    fireEvent.click(screen.getByText("Add to Calendar"));

    expect(generateIcsLib.downloadIcsFile).toHaveBeenCalledTimes(1);
    const [eventArg, filenameArg] = generateIcsLib.downloadIcsFile.mock.calls[0];

    expect(eventArg.title).toBe("Interview: Jane Doe");
    expect(eventArg.start).toBe("2026-09-01T10:00:00Z");
    expect(eventArg.durationMinutes).toBe(45);
    expect(eventArg.location).toBe("https://meet.example.com/abc");
    expect(eventArg.description).toContain("Interviewer: Alex Kim");
    expect(eventArg.description).toContain("Candidate: Jane Doe");
    expect(eventArg.description).toContain("Bring laptop");
    expect(filenameArg).toBe("interview-jane-doe.ics");
  });

  it("falls back to a generic filename when candidateName is not provided", () => {
    render(<AddToCalendarButton title="Interview" start="2026-09-01T10:00:00Z" />);

    fireEvent.click(screen.getByText("Add to Calendar"));

    const [, filenameArg] = generateIcsLib.downloadIcsFile.mock.calls[0];
    expect(filenameArg).toBe("interview-invite.ics");
  });

  it("does not call downloadIcsFile when start is missing", () => {
    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    render(<AddToCalendarButton title="Interview" />);
    fireEvent.click(screen.getByText("Add to Calendar"));

    expect(generateIcsLib.downloadIcsFile).not.toHaveBeenCalled();
    expect(consoleErrorSpy).toHaveBeenCalled();

    consoleErrorSpy.mockRestore();
  });

  it("defaults the title to 'Interview' when not provided", () => {
    render(<AddToCalendarButton start="2026-09-01T10:00:00Z" />);
    fireEvent.click(screen.getByText("Add to Calendar"));

    const [eventArg] = generateIcsLib.downloadIcsFile.mock.calls[0];
    expect(eventArg.title).toBe("Interview");
  });
});
