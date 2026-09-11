"use client";

import { useEffect, useState } from "react";
import { LoaderCircle, Mic, Volume2 } from "lucide-react";
import Card from "@/components/Card";

const interviewStates = [
  {
    id: "asking",
    label: "Asking",
    icon: Volume2,
    description: "The interviewer is asking a question.",
  },
  {
    id: "listening",
    label: "Listening",
    icon: Mic,
    description: "Listening to the candidate response.",
  },
  {
    id: "processing",
    label: "Processing",
    icon: LoaderCircle,
    description: "Analyzing the response.",
  },
];

const mockInterviewData = {
  question: "Tell me about your experience with distributed systems.",
  transcript:
    "I have worked on backend systems using Python and designed scalable services.",
};

function VoiceInterviewUI({
  state = interviewStates[0],
  question = mockInterviewData.question,
  transcript = mockInterviewData.transcript,
}) {
  const StateIcon = state.icon;

  return (
    <Card title="Voice Interview" description="Real-time interview interaction demo">
      <div className="space-y-5">
        <div className="flex items-center gap-3 rounded-lg border border-border bg-bg-card p-4">
          <div className="rounded-full bg-blue-600/20 p-3">
            <StateIcon
              className={`h-6 w-6 text-blue-400 ${
                state.id === "processing" ? "animate-spin" : ""
              }`}
            />
          </div>

          <div>
            <p className="text-sm font-semibold text-zinc-100">
              {state.label}
            </p>
            <p className="text-xs text-muted">{state.description}</p>
          </div>
        </div>

        <div className="rounded-lg border border-border bg-bg-panel p-4">
          <h4 className="text-xs font-semibold uppercase text-muted">
            Question
          </h4>

          <p className="mt-2 text-sm text-zinc-200">{question}</p>
        </div>

        <div className="rounded-lg border border-border bg-bg-panel p-4">
          <h4 className="text-xs font-semibold uppercase text-muted">
            Live Transcript
          </h4>

          <p className="mt-2 text-sm text-zinc-200">{transcript}</p>
        </div>
      </div>
    </Card>
  );
}

export function VoiceInterviewUIDemo() {
  const [currentState, setCurrentState] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentState((previous) =>
        previous === interviewStates.length - 1 ? 0 : previous + 1
      );
    }, 3000);

    return () => clearInterval(timer);
  }, []);

  return (
    <div className="mx-auto max-w-3xl p-6">
      <VoiceInterviewUI state={interviewStates[currentState]} />
    </div>
  );
}

export default VoiceInterviewUI;