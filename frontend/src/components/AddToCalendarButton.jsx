"use client";

import Button from "./Button";
import { Calendar } from "lucide-react";
import { downloadIcsFile } from "@/lib/generateIcs";

/**
 * AddToCalendarButton
 *
 * Generates and downloads a valid .ics file for a booked interview slot,
 * entirely client-side — no API keys or OAuth required. Works with
 * Google Calendar, Outlook, and Apple Calendar via their standard
 * "import calendar file" flow.
 *
 * Usage:
 *   <AddToCalendarButton
 *     title={`Interview: ${candidateName} — ${role}`}
 *     start={interview.scheduled_at}
 *     durationMinutes={60}
 *     interviewerName={interview.interviewer_name}
 *     candidateName={interview.candidate_name}
 *     location={interview.meeting_link}
 *     notes={interview.notes}
 *   />
 */
export default function AddToCalendarButton({
  title,
  start,
  end,
  durationMinutes = 60,
  interviewerName,
  candidateName,
  location,
  notes,
  variant = "secondary",
  size = "md",
  className = "",
}) {
  const handleClick = () => {
    if (!start) {
      console.error("AddToCalendarButton: 'start' (interview date/time) is required.");
      return;
    }

    const descriptionParts = [];
    if (interviewerName) descriptionParts.push(`Interviewer: ${interviewerName}`);
    if (candidateName) descriptionParts.push(`Candidate: ${candidateName}`);
    if (notes) descriptionParts.push(notes);

    downloadIcsFile(
      {
        title: title || "Interview",
        start,
        end,
        durationMinutes,
        description: descriptionParts.join("\n"),
        location,
      },
      `interview-${candidateName ? candidateName.replace(/\s+/g, "-").toLowerCase() : "invite"}.ics`,
    );
  };

  return (
    <Button
      variant={variant}
      size={size}
      onClick={handleClick}
      className={`inline-flex items-center gap-1.5 ${className}`}
    >
      <Calendar size={14} />
      Add to Calendar
    </Button>
  );
}
