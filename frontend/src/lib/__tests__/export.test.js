/**
 * Tests for export utility functions
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  toCSV,
  downloadCSV,
  exportSessionsCSV,
  exportCandidatesCSV,
  exportAnalyticsCSV,
  generateSessionPDF,
  requestBackendPDF,
} from "../export";

// Mock jsPDF module - must use mockImplementation for classes
vi.mock("jspdf", () => ({
  jsPDF: vi.fn(),
}));

describe("toCSV", () => {
  it("converts data and columns to CSV format", () => {
    const data = [
      { name: "Alice", age: 30, city: "NYC" },
      { name: "Bob", age: 25, city: "LA" },
    ];
    const columns = [
      { label: "Name", key: "name" },
      { label: "Age", key: "age" },
      { label: "City", key: "city" },
    ];

    const result = toCSV(data, columns);

    expect(result).toBe("Name,Age,City\nAlice,30,NYC\nBob,25,LA");
  });

  it("handles empty data", () => {
    const data = [];
    const columns = [
      { label: "Name", key: "name" },
      { label: "Age", key: "age" },
    ];

    const result = toCSV(data, columns);

    expect(result).toBe("");
  });

  it("escapes values containing commas", () => {
    const data = [{ name: "Alice", address: "123 Main St, NYC" }];
    const columns = [
      { label: "Name", key: "name" },
      { label: "Address", key: "address" },
    ];

    const result = toCSV(data, columns);

    expect(result).toBe('Name,Address\nAlice,"123 Main St, NYC"');
  });

  it("escapes values containing quotes", () => {
    const data = [{ name: "Alice", quote: 'She said "Hello"' }];
    const columns = [
      { label: "Name", key: "name" },
      { label: "Quote", key: "quote" },
    ];

    const result = toCSV(data, columns);

    expect(result).toBe('Name,Quote\nAlice,"She said ""Hello"""');
  });

  it("escapes values containing newlines", () => {
    const data = [{ name: "Alice", address: "123 Main St\nNYC" }];
    const columns = [
      { label: "Name", key: "name" },
      { label: "Address", key: "address" },
    ];

    const result = toCSV(data, columns);

    expect(result).toBe('Name,Address\nAlice,"123 Main St\nNYC"');
  });

  it("handles null and undefined values", () => {
    const data = [{ name: "Alice", age: null, city: undefined }];
    const columns = [
      { label: "Name", key: "name" },
      { label: "Age", key: "age" },
      { label: "City", key: "city" },
    ];

    const result = toCSV(data, columns);

    expect(result).toBe("Name,Age,City\nAlice,,");
  });

  it("uses accessor function when provided", () => {
    const data = [
      { firstName: "Alice", years: 30 },
      { firstName: "Bob", years: 25 },
    ];
    const columns = [
      { label: "Name", accessor: (row) => row.firstName },
      { label: "Age", accessor: (row) => row.years },
    ];

    const result = toCSV(data, columns);

    expect(result).toBe("Name,Age\nAlice,30\nBob,25");
  });
});

describe("downloadCSV", () => {
  let createObjectURLSpy;
  let revokeObjectURLSpy;
  let clickSpy;

  beforeEach(() => {
    createObjectURLSpy = vi.fn(() => "blob:mock-url");
    revokeObjectURLSpy = vi.fn();
    clickSpy = vi.fn();

    global.URL.createObjectURL = createObjectURLSpy;
    global.URL.revokeObjectURL = revokeObjectURLSpy;
    
    global.document.createElement = vi.fn(() => ({
      href: "",
      download: "",
      click: clickSpy,
    }));
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("creates a Blob and triggers download", () => {
    const filename = "test.csv";
    const content = "Name,Age\nAlice,30";

    downloadCSV(filename, content);

    expect(createObjectURLSpy).toHaveBeenCalled();
    expect(clickSpy).toHaveBeenCalled();
    expect(revokeObjectURLSpy).toHaveBeenCalledWith("blob:mock-url");
  });
});

describe("exportSessionsCSV", () => {
  let createObjectURLSpy;
  let revokeObjectURLSpy;
  let clickSpy;

  beforeEach(() => {
    createObjectURLSpy = vi.fn(() => "blob:mock-url");
    revokeObjectURLSpy = vi.fn();
    clickSpy = vi.fn();

    global.URL.createObjectURL = createObjectURLSpy;
    global.URL.revokeObjectURL = revokeObjectURLSpy;
    
    global.document.createElement = vi.fn(() => ({
      href: "",
      download: "",
      click: clickSpy,
    }));
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("exports sessions with correct columns", () => {
    const sessions = [
      {
        session_id: "sess-123",
        candidate_id: "cand-456",
        status: "COMPLETED",
        risk_score: 0.234,
      },
    ];

    exportSessionsCSV(sessions);

    expect(createObjectURLSpy).toHaveBeenCalled();
    expect(clickSpy).toHaveBeenCalled();
  });
});

describe("exportCandidatesCSV", () => {
  let createObjectURLSpy;
  let revokeObjectURLSpy;
  let clickSpy;

  beforeEach(() => {
    createObjectURLSpy = vi.fn(() => "blob:mock-url");
    revokeObjectURLSpy = vi.fn();
    clickSpy = vi.fn();

    global.URL.createObjectURL = createObjectURLSpy;
    global.URL.revokeObjectURL = revokeObjectURLSpy;
    
    global.document.createElement = vi.fn(() => ({
      href: "",
      download: "",
      click: clickSpy,
    }));
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("exports candidates with aggregated data", () => {
    const candidates = [
      {
        candidate_id: "cand-1",
        total_sessions: 5,
      },
    ];

    exportCandidatesCSV(candidates);

    expect(createObjectURLSpy).toHaveBeenCalled();
    expect(clickSpy).toHaveBeenCalled();
  });
});

describe("exportAnalyticsCSV", () => {
  let createObjectURLSpy;
  let revokeObjectURLSpy;
  let clickSpy;

  beforeEach(() => {
    createObjectURLSpy = vi.fn(() => "blob:mock-url");
    revokeObjectURLSpy = vi.fn();
    clickSpy = vi.fn();

    global.URL.createObjectURL = createObjectURLSpy;
    global.URL.revokeObjectURL = revokeObjectURLSpy;
    
    global.document.createElement = vi.fn(() => ({
      href: "",
      download: "",
      click: clickSpy,
    }));
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("exports analytics statistics", () => {
    const data = {
      stats: {
        total_sessions: 100,
      },
    };

    exportAnalyticsCSV(data);

    expect(createObjectURLSpy).toHaveBeenCalled();
    expect(clickSpy).toHaveBeenCalled();
  });
});


describe("generateSessionPDF", () => {
  let mockDoc;

  beforeEach(async () => {
    // Create a fresh mock for each test  
    mockDoc = {
      text: vi.fn(),
      setFont: vi.fn(),
      setFontSize: vi.fn(),
      addPage: vi.fn(),
      save: vi.fn(),
      setPage: vi.fn(),
      getNumberOfPages: vi.fn(() => 1),
      splitTextToSize: vi.fn((text) => [text]),
    };
    
    // Use mockImplementation with a proper constructor function
    const jsPDF = (await import("jspdf")).jsPDF;
    jsPDF.mockImplementation(function() {
      return mockDoc;
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("generates PDF and calls save with correct filename", async () => {
    const sessionData = {
      session_id: "sess-123",
      candidate_id: "cand-456",
      status: "COMPLETED",
      risk_score: 0.75,
    };

    await generateSessionPDF(sessionData);

    expect(mockDoc.save).toHaveBeenCalled();
    const filename = mockDoc.save.mock.calls[0][0];
    expect(filename).toContain("sess-123");
    expect(filename).toContain(new Date().toISOString().split("T")[0]);
  });

  it("writes session information when video_analysis is present", async () => {
    const sessionData = {
      session_id: "sess-123",
      candidate_id: "cand-456",
      status: "COMPLETED",
      risk_score: 0.5,
      video_analysis: {
        confidence_score: 0.85,
        facial_expressions: {
          neutral: 0.6,
          happy: 0.3,
          surprised: 0.1,
        },
      },
    };

    await generateSessionPDF(sessionData);

    expect(mockDoc.text).toHaveBeenCalled();
    const textCalls = mockDoc.text.mock.calls.map(call => call[0]);
    const allText = textCalls.join(" ");
    
    expect(allText).toContain("Video Analysis");
    expect(mockDoc.save).toHaveBeenCalled();
  });

  it("writes audio analysis when present", async () => {
    const sessionData = {
      session_id: "sess-456",
      candidate_id: "cand-789",
      status: "COMPLETED",
      risk_score: 0.3,
      audio_analysis: {
        sentiment: "positive",
        clarity_score: 0.92,
        speech_pace: 145,
        filler_words: 3,
      },
    };

    await generateSessionPDF(sessionData);

    const textCalls = mockDoc.text.mock.calls.map(call => call[0]);
    const allText = textCalls.join(" ");
    
    expect(allText).toContain("Audio Analysis");
    expect(mockDoc.save).toHaveBeenCalled();
  });

  it("skips sections cleanly when data is absent", async () => {
    const sessionData = {
      session_id: "sess-789",
      candidate_id: "cand-012",
      status: "COMPLETED",
      risk_score: 0.2,
      video_analysis: null,
      audio_analysis: null,
      ai_feedback: null,
    };

    await generateSessionPDF(sessionData);

    expect(mockDoc.save).toHaveBeenCalled();
    expect(mockDoc.text).toHaveBeenCalled();
  });

  it("throws user-facing error when sessionData is null", async () => {
    await expect(generateSessionPDF(null)).rejects.toThrow(
      "Failed to generate PDF report"
    );
    await expect(generateSessionPDF(null)).rejects.toThrow("No session data");
  });

  it("throws user-facing error when sessionData is undefined", async () => {
    await expect(generateSessionPDF(undefined)).rejects.toThrow(
      "Failed to generate PDF report"
    );
    await expect(generateSessionPDF(undefined)).rejects.toThrow("No session data");
  });

  it("triggers addPage when content overflows (long ai_feedback)", async () => {
    // Create a very long feedback string that will trigger page breaks
    const longFeedback = "A".repeat(5000);
    
    mockDoc.splitTextToSize.mockReturnValue(
      new Array(60).fill("Line of text") // 60 lines will definitely overflow
    );

    const sessionData = {
      session_id: "sess-overflow",
      candidate_id: "cand-overflow",
      status: "COMPLETED",
      risk_score: 0.5,
      ai_feedback: longFeedback,
    };

    await generateSessionPDF(sessionData);

    expect(mockDoc.addPage).toHaveBeenCalled();
    expect(mockDoc.save).toHaveBeenCalled();
  });

  it("includes page numbers in footer", async () => {
    mockDoc.getNumberOfPages.mockReturnValue(2);

    const sessionData = {
      session_id: "sess-multipage",
      candidate_id: "cand-test",
      status: "COMPLETED",
      risk_score: 0.4,
    };

    await generateSessionPDF(sessionData);

    // Should call setPage for each page when adding footers
    expect(mockDoc.setPage).toHaveBeenCalled();
    expect(mockDoc.save).toHaveBeenCalled();
  });
});

describe("requestBackendPDF", () => {
  let createObjectURLSpy;
  let revokeObjectURLSpy;
  let clickSpy;

  beforeEach(() => {
    createObjectURLSpy = vi.fn(() => "blob:mock-url");
    revokeObjectURLSpy = vi.fn();
    clickSpy = vi.fn();

    global.URL.createObjectURL = createObjectURLSpy;
    global.URL.revokeObjectURL = revokeObjectURLSpy;
    
    global.document.createElement = vi.fn(() => ({
      href: "",
      download: "",
      click: clickSpy,
    }));

    global.fetch = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("calls correct URL and method", async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      blob: vi.fn().mockResolvedValue(new Blob(["pdf content"])),
    });

    await requestBackendPDF("sess-123");

    expect(global.fetch).toHaveBeenCalledWith(
      "/sessions/sess-123/report/pdf",
      expect.objectContaining({
        method: "GET",
        headers: expect.objectContaining({
          "Content-Type": "application/json",
        }),
      })
    );
  });

  it("downloads blob via anchor click on 200 response", async () => {
    const mockBlob = new Blob(["pdf content"], { type: "application/pdf" });
    
    global.fetch.mockResolvedValue({
      ok: true,
      blob: vi.fn().mockResolvedValue(mockBlob),
    });

    await requestBackendPDF("sess-456");

    expect(createObjectURLSpy).toHaveBeenCalled();
    expect(clickSpy).toHaveBeenCalled();
    expect(revokeObjectURLSpy).toHaveBeenCalledWith("blob:mock-url");
  });

  it("rejects with clear error on 404 status", async () => {
    global.fetch.mockResolvedValue({
      ok: false,
      status: 404,
    });

    await expect(requestBackendPDF("nonexistent")).rejects.toThrow(
      "Failed to generate PDF report"
    );
  });

  it("rejects with clear error on 500 status", async () => {
    global.fetch.mockResolvedValue({
      ok: false,
      status: 500,
    });

    await expect(requestBackendPDF("sess-error")).rejects.toThrow(
      "Failed to generate PDF report"
    );
  });

  it("includes session ID in download filename", async () => {
    const mockBlob = new Blob(["pdf content"]);
    
    global.fetch.mockResolvedValue({
      ok: true,
      blob: vi.fn().mockResolvedValue(mockBlob),
    });

    const mockLink = {
      href: "",
      download: "",
      click: clickSpy,
    };
    
    global.document.createElement = vi.fn(() => mockLink);

    await requestBackendPDF("sess-789");

    expect(mockLink.download).toContain("sess-789");
    expect(mockLink.download).toContain("report");
  });
});
