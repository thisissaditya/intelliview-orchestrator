import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { buildIcsContent, downloadIcsFile } from "../generateIcs";

describe("buildIcsContent", () => {
  it("produces a valid VCALENDAR/VEVENT structure", () => {
    const content = buildIcsContent({
      title: "Interview: Jane Doe",
      start: "2026-09-01T10:00:00Z",
      durationMinutes: 45,
    });

    expect(content).toContain("BEGIN:VCALENDAR");
    expect(content).toContain("BEGIN:VEVENT");
    expect(content).toContain("SUMMARY:Interview: Jane Doe");
    expect(content).toContain("DTSTART:20260901T100000Z");
    expect(content).toContain("DTEND:20260901T104500Z");
    expect(content).toContain("END:VEVENT");
    expect(content).toContain("END:VCALENDAR");
  });

  it("uses CRLF line endings as required by RFC 5545", () => {
    const content = buildIcsContent({
      title: "Interview",
      start: "2026-09-01T10:00:00Z",
    });

    expect(content).toContain("\r\n");
  });

  it("defaults to a 60 minute duration when end is not provided", () => {
    const content = buildIcsContent({
      title: "Interview",
      start: "2026-09-01T09:00:00Z",
    });

    expect(content).toContain("DTSTART:20260901T090000Z");
    expect(content).toContain("DTEND:20260901T100000Z");
  });

  it("uses an explicit end time over durationMinutes when both are given", () => {
    const content = buildIcsContent({
      title: "Interview",
      start: "2026-09-01T09:00:00Z",
      end: "2026-09-01T11:30:00Z",
      durationMinutes: 30,
    });

    expect(content).toContain("DTEND:20260901T113000Z");
  });

  it("escapes commas, semicolons, and newlines in text fields", () => {
    const content = buildIcsContent({
      title: "Interview: Jane Doe, Backend Engineer",
      start: "2026-09-01T10:00:00Z",
      description: "Interviewer: Alex Kim\nNotes: bring laptop; discuss design, briefly.",
    });

    expect(content).toContain("SUMMARY:Interview: Jane Doe\\, Backend Engineer");
    expect(content).toContain(
      "DESCRIPTION:Interviewer: Alex Kim\\nNotes: bring laptop\\; discuss design\\, briefly.",
    );
  });

  it("includes LOCATION only when provided", () => {
    const withLocation = buildIcsContent({
      title: "Interview",
      start: "2026-09-01T10:00:00Z",
      location: "https://meet.example.com/abc",
    });
    expect(withLocation).toContain("LOCATION:https://meet.example.com/abc");

    const withoutLocation = buildIcsContent({
      title: "Interview",
      start: "2026-09-01T10:00:00Z",
    });
    expect(withoutLocation).not.toContain("LOCATION:");
  });

  it("accepts Date objects as well as ISO strings", () => {
    const content = buildIcsContent({
      title: "Interview",
      start: new Date("2026-09-01T10:00:00Z"),
      durationMinutes: 30,
    });

    expect(content).toContain("DTSTART:20260901T100000Z");
    expect(content).toContain("DTEND:20260901T103000Z");
  });
});

describe("downloadIcsFile", () => {
  let createObjectURLSpy;
  let revokeObjectURLSpy;
  let clickSpy;

  beforeEach(() => {
    createObjectURLSpy = vi.fn(() => "blob:mock-url");
    revokeObjectURLSpy = vi.fn();
    global.URL.createObjectURL = createObjectURLSpy;
    global.URL.revokeObjectURL = revokeObjectURLSpy;
    clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("creates a Blob URL and triggers a click to download", () => {
    downloadIcsFile(
      { title: "Interview", start: "2026-09-01T10:00:00Z" },
      "interview-jane-doe.ics",
    );

    expect(createObjectURLSpy).toHaveBeenCalledTimes(1);
    expect(clickSpy).toHaveBeenCalledTimes(1);
  });

  it("appends .ics to the filename if missing", () => {
    let capturedDownload = "";
    const originalCreateElement = document.createElement.bind(document);
    vi.spyOn(document, "createElement").mockImplementation((tag) => {
      const el = originalCreateElement(tag);
      if (tag === "a") {
        Object.defineProperty(el, "download", {
          get: () => capturedDownload,
          set: (v) => {
            capturedDownload = v;
          },
        });
      }
      return el;
    });

    downloadIcsFile({ title: "Interview", start: "2026-09-01T10:00:00Z" }, "interview-jane");

    expect(capturedDownload).toBe("interview-jane.ics");
  });
});
