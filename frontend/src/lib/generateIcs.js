/**
 * Client-side .ics (iCalendar) file generator.
 * No API keys, no OAuth — builds a valid RFC 5545 file entirely in the browser.
 *
 * Works with Google Calendar, Outlook, and Apple Calendar via the
 * standard "import/open .ics file" flow.
 */

/**
 * Escapes special characters per RFC 5545 §3.3.11 (TEXT value type).
 * Commas, semicolons, and backslashes must be escaped; newlines become \n.
 */
function escapeIcsText(value = "") {
  return String(value)
    .replace(/\\/g, "\\\\")
    .replace(/;/g, "\\;")
    .replace(/,/g, "\\,")
    .replace(/\r?\n/g, "\\n");
}

/**
 * Formats a Date as a UTC iCalendar timestamp: YYYYMMDDTHHMMSSZ
 */
function formatIcsDate(date) {
  return date
    .toISOString()
    .replace(/[-:]/g, "")
    .replace(/\.\d{3}Z$/, "Z");
}

/**
 * Generates a UID unique enough for a single-event .ics file.
 */
function generateUid() {
  const random =
    typeof crypto !== "undefined" && crypto.randomUUID
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  return `${random}@intelliview-orchestrator`;
}

/**
 * Builds the raw .ics file contents for a single event.
 *
 * @param {Object} event
 * @param {string} event.title - Event title (e.g. "Interview: Jane Doe — Backend Engineer")
 * @param {Date|string} event.start - Event start time (Date object or ISO string)
 * @param {Date|string} [event.end] - Event end time. If omitted, uses durationMinutes.
 * @param {number} [event.durationMinutes=60] - Used only if `end` is not provided.
 * @param {string} [event.description] - Longer event details (interviewer, notes, meeting link, etc.)
 * @param {string} [event.location] - Physical address or a meeting link (Zoom/Meet URL work fine here).
 * @returns {string} Raw .ics file content, CRLF line-endings per spec.
 */
export function buildIcsContent({
  title,
  start,
  end,
  durationMinutes = 60,
  description = "",
  location = "",
}) {
  const startDate = start instanceof Date ? start : new Date(start);
  const endDate = end
    ? end instanceof Date
      ? end
      : new Date(end)
    : new Date(startDate.getTime() + durationMinutes * 60 * 1000);

  const lines = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//IntelliView Orchestrator//Add to Calendar//EN",
    "CALSCALE:GREGORIAN",
    "METHOD:PUBLISH",
    "BEGIN:VEVENT",
    `UID:${generateUid()}`,
    `DTSTAMP:${formatIcsDate(new Date())}`,
    `DTSTART:${formatIcsDate(startDate)}`,
    `DTEND:${formatIcsDate(endDate)}`,
    `SUMMARY:${escapeIcsText(title)}`,
  ];

  if (description) {
    lines.push(`DESCRIPTION:${escapeIcsText(description)}`);
  }
  if (location) {
    lines.push(`LOCATION:${escapeIcsText(location)}`);
  }

  lines.push("END:VEVENT", "END:VCALENDAR");

  // RFC 5545 requires CRLF line endings.
  return lines.join("\r\n");
}

/**
 * Triggers a browser download of the given event as a .ics file.
 * Entirely client-side — no server round-trip required.
 *
 * @param {Object} event - Same shape as buildIcsContent's argument.
 * @param {string} [filename="interview.ics"]
 */
export function downloadIcsFile(event, filename = "interview.ics") {
  const content = buildIcsContent(event);
  const blob = new Blob([content], { type: "text/calendar;charset=utf-8" });
  const url = URL.createObjectURL(blob);

  const link = document.createElement("a");
  link.href = url;
  link.download = filename.endsWith(".ics") ? filename : `${filename}.ics`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  // Release the object URL after the click has been processed.
  setTimeout(() => URL.revokeObjectURL(url), 0);
}
