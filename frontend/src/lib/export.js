/**
 * CSV and PDF export utilities
 */

import { jsPDF } from "jspdf";

/**
 * Convert array of objects to CSV string
 */
export function toCSV(data, columns) {
  if (!data || data.length === 0) return "";

  const headers = columns.map((col) => col.label);
  const rows = data.map((row) =>
    columns.map((col) => {
      const value = col.accessor ? col.accessor(row) : row[col.key];
      // Escape quotes and wrap in quotes if contains comma
      const str = String(value ?? "");
      return str.includes(",") || str.includes('"') || str.includes("\n")
        ? `"${str.replace(/"/g, '""')}"`
        : str;
    })
  );

  return [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
}

/**
 * Download CSV file
 */
export function downloadCSV(filename, csvContent) {
  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

/**
 * Export sessions data as CSV
 */
export function exportSessionsCSV(sessions) {
  const columns = [
    { label: "Session ID", key: "session_id" },
    { label: "Candidate ID", key: "candidate_id" },
    { label: "Status", key: "status" },
    { label: "Risk Score", accessor: (s) => s.risk_score?.toFixed(3) ?? "" },
    { label: "Worker Node", key: "assigned_node" },
    { label: "Created At", key: "created_at" },
    { label: "Updated At", key: "updated_at" },
    { label: "Start Time", key: "start_time" },
    { label: "End Time", key: "end_time" },
  ];

  const csv = toCSV(sessions, columns);
  const filename = `sessions-${new Date().toISOString().split("T")[0]}.csv`;
  downloadCSV(filename, csv);
}

/**
 * Export candidates data as CSV
 */
export function exportCandidatesCSV(candidates) {
  const columns = [
    { label: "Candidate ID", key: "candidate_id" },
    { label: "Total Sessions", key: "total_sessions" },
    { label: "Completed Sessions", key: "completed_sessions" },
    { label: "Failed Sessions", key: "failed_sessions" },
    { label: "Active Sessions", key: "active_sessions" },
    {
      label: "Average Risk Score",
      accessor: (c) => c.avg_risk_score?.toFixed(3) ?? "",
    },
    {
      label: "Latest Session",
      accessor: (c) => c.latest_session?.session_id ?? "",
    },
    {
      label: "Latest Status",
      accessor: (c) => c.latest_session?.status ?? "",
    },
    {
      label: "Latest Updated",
      accessor: (c) => c.latest_session?.updated_at ?? "",
    },
  ];

  const csv = toCSV(candidates, columns);
  const filename = `candidates-${new Date().toISOString().split("T")[0]}.csv`;
  downloadCSV(filename, csv);
}

/**
 * Export analytics data as CSV
 */
export function exportAnalyticsCSV(data) {
  const { candidates, stats, faults } = data;

  // Export candidate evaluations if present
  if (candidates && candidates.length > 0) {
    const columns = [
      { label: "Candidate", key: "name" },
      { label: "Role", key: "role" },
      { label: "Status", key: "status" },
      { label: "Score", key: "score" },
      { label: "Risk", key: "risk" },
    ];

    const csv = toCSV(candidates, columns);
    const filename = `analytics-candidates-${
      new Date().toISOString().split("T")[0]
    }.csv`;
    downloadCSV(filename, csv);
    return;
  }

  // Otherwise export session statistics
  const rows = [
    ["Metric", "Value"],
    ["Total Sessions", stats?.total_sessions ?? 0],
    [
      "Average Risk Score",
      stats?.risk_score_stats?.average_risk_score?.toFixed(3) ?? "N/A",
    ],
    ["High Risk Sessions", stats?.risk_score_stats?.high_risk_sessions ?? 0],
  ];

  const csv = rows.map((r) => r.join(",")).join("\n");
  const filename = `analytics-${new Date().toISOString().split("T")[0]}.csv`;
  downloadCSV(filename, csv);
}

/**
 * Generate PDF report for a session (browser-based)
 * This is the fallback for when backend PDF generation fails
 */
export async function generateSessionPDF(sessionData) {
  try {
    // Defensive null checks
    if (!sessionData) {
      throw new Error("No session data provided");
    }

    const doc = new jsPDF();
    let y = 20;

    // Helper to check if we need a new page
    const checkPageBreak = (requiredSpace = 20) => {
      if (y + requiredSpace > 270) {
        doc.addPage();
        y = 20;
        return true;
      }
      return false;
    };

    // Title
    checkPageBreak(30);
    doc.setFontSize(18);
    doc.setFont(undefined, 'bold');
    doc.text("Interview Session Report", 20, y);
    y += 10;

    // Session ID
    checkPageBreak(40);
    doc.setFontSize(12);
    doc.setFont(undefined, 'normal');
    doc.text(`Session ID: ${sessionData.session_id || "N/A"}`, 20, y);
    y += 8;
    doc.text(`Candidate: ${sessionData.candidate_id || "N/A"}`, 20, y);
    y += 8;
    doc.text(`Status: ${sessionData.status || "N/A"}`, 20, y);
    y += 8;
    doc.text(
      `Risk Score: ${sessionData.risk_score != null ? sessionData.risk_score.toFixed(3) : "N/A"}`,
      20,
      y
    );
    y += 12;

    // Timestamps Section
    checkPageBreak(40);
    doc.setFont(undefined, 'bold');
    doc.text("Timeline", 20, y);
    y += 8;
    doc.setFont(undefined, 'normal');
    doc.setFontSize(10);
    doc.text(`Created: ${sessionData.created_at || "N/A"}`, 20, y);
    y += 6;
    doc.text(`Updated: ${sessionData.updated_at || "N/A"}`, 20, y);
    y += 6;
    doc.text(`Started: ${sessionData.start_time || "N/A"}`, 20, y);
    y += 6;
    doc.text(`Ended: ${sessionData.end_time || "N/A"}`, 20, y);
    y += 10;

    // Worker info
    if (sessionData.assigned_node) {
      checkPageBreak(20);
      doc.setFontSize(12);
      doc.setFont(undefined, 'bold');
      doc.text("Processing", 20, y);
      y += 8;
      doc.setFontSize(10);
      doc.setFont(undefined, 'normal');
      doc.text(`Worker Node: ${sessionData.assigned_node}`, 20, y);
      y += 10;
    }

    // Video Analysis
    if (sessionData.video_analysis) {
      checkPageBreak(40);
      doc.setFontSize(12);
      doc.setFont(undefined, 'bold');
      doc.text("Video Analysis", 20, y);
      y += 8;
      doc.setFontSize(10);
      doc.setFont(undefined, 'normal');
      
      if (sessionData.video_analysis.confidence_score != null) {
        doc.text(
          `Confidence Score: ${(sessionData.video_analysis.confidence_score * 100).toFixed(1)}%`,
          25,
          y
        );
        y += 6;
      }
      
      if (sessionData.video_analysis.facial_expressions) {
        try {
          const expressions = Object.entries(sessionData.video_analysis.facial_expressions)
            .sort(([, a], [, b]) => b - a)
            .slice(0, 3)
            .map(([k, v]) => `${k} (${(v * 100).toFixed(0)}%)`)
            .join(", ");
          doc.text(`Expressions: ${expressions || "N/A"}`, 25, y);
          y += 6;
        } catch (error) {
          // Silently skip malformed expressions data
          doc.text(`Expressions: Error parsing data`, 25, y);
          y += 6;
        }
      }
      y += 6;
    }

    // Audio Analysis
    if (sessionData.audio_analysis) {
      checkPageBreak(40);
      
      doc.setFontSize(12);
      doc.setFont(undefined, 'bold');
      doc.text("Audio Analysis", 20, y);
      y += 8;
      doc.setFontSize(10);
      doc.setFont(undefined, 'normal');
      
      if (sessionData.audio_analysis.sentiment) {
        doc.text(`Sentiment: ${sessionData.audio_analysis.sentiment}`, 25, y);
        y += 6;
      }
      
      if (sessionData.audio_analysis.clarity_score != null) {
        doc.text(
          `Clarity Score: ${(sessionData.audio_analysis.clarity_score * 100).toFixed(1)}%`,
          25,
          y
        );
        y += 6;
      }
      
      if (sessionData.audio_analysis.speech_pace != null) {
        doc.text(`Speech Pace: ${sessionData.audio_analysis.speech_pace} wpm`, 25, y);
        y += 6;
      }
      
      if (sessionData.audio_analysis.filler_words != null) {
        doc.text(`Filler Words: ${sessionData.audio_analysis.filler_words}`, 25, y);
        y += 6;
      }
      y += 6;
    }

    // AI Feedback
    if (sessionData.ai_feedback) {
      checkPageBreak(30);
      
      doc.setFontSize(12);
      doc.setFont(undefined, 'bold');
      doc.text("AI Feedback", 20, y);
      y += 8;
      doc.setFontSize(10);
      doc.setFont(undefined, 'normal');
      
      // Split long text into multiple lines
      try {
        const splitText = doc.splitTextToSize(String(sessionData.ai_feedback), 170);
        const textHeight = splitText.length * 6;
        checkPageBreak(textHeight);
        doc.text(splitText, 25, y);
        y += textHeight;
      } catch (error) {
        doc.text("Feedback available but could not be rendered", 25, y);
        y += 6;
      }
    }

    // Footer with page numbers and timestamp
    const pageCount = doc.getNumberOfPages();
    const timestamp = new Date().toISOString();
    
    for (let i = 1; i <= pageCount; i++) {
      doc.setPage(i);
      doc.setFontSize(8);
      doc.setFont(undefined, 'normal');
      doc.text(
        `Page ${i} of ${pageCount} | Generated: ${timestamp}`,
        20,
        285,
        { align: 'left' }
      );
    }

    // Save PDF
    const filename = `session-${sessionData.session_id || 'unknown'}-${
      new Date().toISOString().split("T")[0]
    }.pdf`;
    doc.save(filename);
  } catch (error) {
    // Wrap any internal errors in a user-friendly message
    const message = error.message || "An unknown error occurred";
    throw new Error(`Failed to generate PDF report: ${message}`);
  }
}

/**
 * Request backend to generate complex PDF report
 */
export async function requestBackendPDF(sessionId) {
  const response = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL || ""}/sessions/${sessionId}/report/pdf`,
    {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    }
  );

  if (!response.ok) {
    throw new Error("Failed to generate PDF report");
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `session-${sessionId}-report.pdf`;
  link.click();
  URL.revokeObjectURL(url);
}

export async function exportAnalyticsPDF(data) {
  const response = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}/analytics/export/pdf`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        candidates: data?.candidates ?? [],
        stats: data?.stats ?? null,
        faults: data?.faults ?? null,
      }),
    }
  );

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to export PDF: ${errorText}`);
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);

  const link = document.createElement("a");
  link.href = url;
  link.download = `analytics-report-${
    new Date().toISOString().split("T")[0]
  }.pdf`;

  document.body.appendChild(link);
  link.click();
  link.remove();

  URL.revokeObjectURL(url);
}

