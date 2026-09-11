"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import useSWR from "swr";
import {
  Video,
  VideoOff,
  Mic,
  MicOff,
  PhoneOff,
  Pause,
  Play,
  Radio,
} from "lucide-react";

import Card from "@/components/Card";
import { Badge } from "@/components/Badge";
import VideoPlayer from "@/components/VideoPlayer";
import { endpoints } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import { toast } from "@/lib/toast";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useMomentTracking } from "@/hooks/useMomentTracking";
import RiskTimeline from "@/components/RiskTimeline";
import { cn, riskColor } from "@/lib/utils";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { useAudioPlayback } from "@/hooks/useAudioPlayback";
import AudioIndicator from "@/components/AudioIndicator";

// Persisted so a refresh doesn't silently drop a paused interview back to
// the "start a new one" screen.
const SESSION_STORAGE_KEY = "iv_interview_session_state";

function readPersistedSession() {
  if (typeof window === "undefined") return null;

  try {
    const raw = window.localStorage.getItem(SESSION_STORAGE_KEY);

    if (!raw) return null;

    const parsed = JSON.parse(raw);

    if (!parsed || !parsed.isLive) return null;

    return parsed;
  } catch {
    return null;
  }
}

export default function InterviewPage() {
  const token = useAppStore((s) => s.token);

  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const audioCtxRef = useRef(null);
  const animFrameRef = useRef(null);

  const persisted = useRef(
    typeof window !== "undefined"
      ? readPersistedSession()
      : null
  );

  const [videoEnabled, setVideoEnabled] = useState(false);
  const [audioEnabled, setAudioEnabled] = useState(true);

  const [isPaused, setIsPaused] = useState(
    () => persisted.current?.isPaused ?? false
  );

  const [isLive, setIsLive] = useState(
    () => persisted.current?.isLive ?? false
  );

  const [activeSession, setActiveSession] = useState(
    () => persisted.current?.activeSession ?? null
  );

  const [riskScore, setRiskScore] = useState(0);

  // ============================================================
  // ISSUE #18 - Integrity / Trust Score
  // ============================================================
  const [integrityScore, setIntegrityScore] = useState(null);

  const [feedback, setFeedback] = useState([]);
  const [audioLevels, setAudioLevels] = useState(
    new Array(32).fill(0)
  );

  const [candidate, setCandidate] = useState(
    () => persisted.current?.candidate ?? ""
  );

  const [starting, setStarting] = useState(false);
  const [voiceError, setVoiceError] = useState(null);

  // 💡 Task B3: State loop context tracker definition for active question data strings
  const [currentQuestion, setCurrentQuestion] = useState({
    text: "Welcome to your AI Interview. Please review the instructions and answer clearly.",
    audioUrl: ""
  });

  // 🔊 Task B3: Hook evaluation lifecycle deployment logic sequence
  const { isPlaying } = useAudioPlayback(currentQuestion?.audioUrl, () => {
    console.log("Question audio playback complete. Advancing turn machine states.");
    // If a transition trigger parameter exists within parent props, invoke it here
  });

  // Keep persisted copy in sync while interview is live.
  useEffect(() => {
    if (typeof window === "undefined") return;

    if (!isLive) {
      window.localStorage.removeItem(
        SESSION_STORAGE_KEY
      );

      return;
    }

    window.localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({
        isLive,
        isPaused,
        activeSession,
        candidate,
      })
    );
  }, [
    isLive,
    isPaused,
    activeSession,
    candidate,
  ]);

  const {
    moments,
    isTracking,
    startTracking,
    stopTracking,
    trackEvent,
  } = useMomentTracking(activeSession);

  const {
    connected,
    reconnecting,
    retryAttempt,
    error: voiceStreamError,
  } = useWebSocket({
    path: "/monitoring/ws/metrics",

    enabled: !!token && isLive,

    onMessage: (data) => {
      if (data?.risk_score != null) {
        setRiskScore(data.risk_score);
      }

      if (data?.feedback) {
        setFeedback((prev) =>
          [...prev, data.feedback].slice(-20)
        );
      }
    },
  });

  // ============================================================
  // ISSUE #18
  // Poll session-status for live integrity score
  // ============================================================
  const {
    data: sessionStatus,
    error: sessionStatusError,
  } = useSWR(
    isLive && activeSession
      ? `/session-status/${activeSession}`
      : null,
    {
      refreshInterval: 3000,
      revalidateOnFocus: true,
    }
  );

  // Update integrity score when API provides it.
  useEffect(() => {
    if (
      sessionStatus?.integrity_score !== null &&
      sessionStatus?.integrity_score !== undefined
    ) {
      const score = Number(
        sessionStatus.integrity_score
      );

      if (Number.isFinite(score)) {
        setIntegrityScore(score);
      }
    }
  }, [sessionStatus]);

  const startCamera = useCallback(async () => {
    const maxAttempts = 3;
    let lastError = null;

    for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { width: 640, height: 480, facingMode: "user" },
          audio: true,
        });
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
        setVideoEnabled(true);
        setVoiceError(null);

        audioCtxRef.current = new (window.AudioContext || window.webkitAudioContext)();
        const source = audioCtxRef.current.createMediaStreamSource(stream);
        const analyzer = audioCtxRef.current.createAnalyser();
        analyzer.fftSize = 64;
        source.connect(analyzer);

        const dataArray = new Uint8Array(analyzer.frequencyBinCount);
        const draw = () => {
          analyzer.getByteFrequencyData(dataArray);
          setAudioLevels(Array.from(dataArray));
          animFrameRef.current = requestAnimationFrame(draw);
        };
        draw();
        return true;
      } catch (err) {
        lastError = err;

        const recoverable =
          err?.name === "NotReadableError" || err?.name === "AbortError";

        if (!recoverable || attempt === maxAttempts - 1) {
          break;
        }

        const delay = 500 * 2 ** attempt;
        await new Promise((resolve) => setTimeout(resolve, delay));
      }
    }

    const message =
      lastError?.name === "NotAllowedError" ||
      lastError?.name === "PermissionDeniedError"
        ? "Microphone and camera permission is required. Please allow access and try again."
        : lastError?.name === "NotFoundError"
          ? "No microphone or camera was found. Please connect a device and try again."
          : lastError?.name === "NotReadableError"
            ? "The microphone or camera is currently unavailable. Please close other apps using it and try again."
            : lastError?.name === "AbortError"
              ? "The microphone or camera could not be started. Please try again."
              : "Unable to access the microphone or camera. Please try again.";

    setVoiceError(message);
    toast.error("Voice access failed", message);
    return false;
  }, []);
  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current
        .getTracks()
        .forEach((t) => t.stop());

      streamRef.current = null;
    }

    if (audioCtxRef.current) {
      audioCtxRef.current.close();
      audioCtxRef.current = null;
    }

    if (animFrameRef.current) {
      cancelAnimationFrame(
        animFrameRef.current
      );

      animFrameRef.current = null;
    }

    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }

    setVideoEnabled(false);
    setAudioLevels(new Array(32).fill(0));
  }, []);

  useEffect(() => {
    return () => stopCamera();
  }, [stopCamera]);

  const toggleAudio = useCallback(() => {
    if (streamRef.current) {
      streamRef.current
        .getAudioTracks()
        .forEach((t) => {
          t.enabled = !audioEnabled;
        });
    }

    setAudioEnabled((v) => !v);
  }, [audioEnabled]);

  const handleStart = async () => {
    if (!candidate.trim()) {
      toast.warn(
        "Enter a candidate ID",
        "Required to start the interview"
      );

      return;
    }

    setStarting(true);

    try {
      const r =
        await endpoints.startInterview({
          candidate_id: candidate.trim(),
          priority: "high",
        });

      setActiveSession(r.session_id);
      setIsLive(true);

      // Reset Issue #18 score for new session.
      setIntegrityScore(null);

      const cameraStarted = await startCamera();
      if (!cameraStarted) {
        setIsLive(false);
        setActiveSession(null);
        return;
      }
      startTracking();

      trackEvent("session_start", {
        candidate_id: candidate.trim(),
      });

      toast.success(
        "Interview started",
        `Session ${r.session_id}`
      );
    } catch (err) {
      toast.error(
        "Failed to start",
        err instanceof Error
          ? err.message
          : String(err)
      );
    } finally {
      setStarting(false);
    }
  };

  const handleStop = () => {
    trackEvent("session_end", {
      duration: moments.length * 1000,
    });

    stopTracking();
    stopCamera();

    setIsLive(false);
    setActiveSession(null);
    setIsPaused(false);

    setRiskScore(0);

    // ============================================================
    // ISSUE #18 - Reset integrity score
    // ============================================================
    setIntegrityScore(null);

    setFeedback([]);

    if (typeof window !== "undefined") {
      window.localStorage.removeItem(
        SESSION_STORAGE_KEY
      );
    }

    toast.info("Interview ended");
  };

  const handlePause = () => {
    setIsPaused((v) => !v);

    if (streamRef.current) {
      streamRef.current
        .getVideoTracks()
        .forEach((t) => {
          t.enabled = isPaused;
        });
    }

    toast.info(
      isPaused ? "Resumed" : "Paused"
    );
  };

  const maxLevel = Math.max(
    ...audioLevels,
    1
  );

  return (
    <ErrorBoundary>
      <div className="space-y-6 animate-fade-in">

        {/* ======================================================
            HEADER
        ====================================================== */}

        <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="text-xl font-semibold text-zinc-50 sm:text-2xl">
              Live Interview
            </h1>

            <p className="text-sm text-muted">
              Real-time video feed with AI-powered
              analysis.
            </p>
          </div>

          {isLive && (
            <div className="flex items-center gap-2">
              <Radio
                size={12}
                className="text-emerald-400 animate-pulse"
              />

              <span className="text-xs text-emerald-400">
                LIVE
              </span>

              {isPaused && (
                <Badge
                  variant="warn"
                  className="ml-1"
                >
                  Paused
                </Badge>
              )}
            </div>
          )}
        </div>

        {/* ======================================================
            PAUSED MESSAGE
        ====================================================== */}

        {isLive && isPaused && (
          <div className="flex items-center gap-2 rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2.5 text-sm text-amber-300 sm:gap-3">

            <Pause
              size={16}
              className="shrink-0"
            />

            <span className="font-medium">
              Interview Paused
            </span>

            <span className="hidden text-amber-300/70 sm:inline">
              Camera, mic, and controls are on hold
              until you resume.
            </span>
          </div>
        )}

        {/* ======================================================
            START INTERVIEW
        ====================================================== */}



        {/* 🔊 Task B3: Visual Audio Playback State Component Layout Render */}
        <Card className="p-6 bg-zinc-900 border-zinc-800">
          <div className="mb-4">
            <AudioIndicator isPlaying={isPlaying} />
            <h3 className="text-xl font-semibold text-zinc-100 mt-3">
              {currentQuestion?.text}
            </h3>
          </div>
        </Card>

        {!isLive && (
          <Card
            title="Start interview"
            description="Begin a new live interview session."
          >
            <div className="flex flex-col items-stretch gap-3 sm:flex-row sm:flex-wrap sm:items-end">

              <div className="w-full sm:min-w-[200px] sm:flex-1">
                <label className="block text-xs text-muted">
                  Candidate ID
                </label>

                <input
                  value={candidate}
                  onChange={(e) =>
                    setCandidate(e.target.value)
                  }
                  placeholder="cand-1234"
                  className="mt-1 w-full rounded-md border border-border bg-bg-card px-3 py-2 text-sm text-zinc-100 placeholder:text-muted focus:border-accent focus:outline-none"
                />
              </div>
              {voiceError && (
                <div
                  role="alert"
                  className="flex w-full items-center gap-2 rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-400"
                >
                  <AlertTriangle size={16} />
                  <span>{voiceError}</span>
                </div>
              )}
              <button
                onClick={handleStart}
                disabled={
                  !token ||
                  starting ||
                  !candidate.trim()
                }
                className="flex w-full items-center justify-center gap-2 rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-dark disabled:opacity-50 sm:w-auto sm:justify-start"
              >
                <Video size={14} />

                {starting
                  ? "Starting..."
                  : "Start Interview"}
              </button>
            </div>

            {!token && (
              <div className="mt-2 text-xs text-amber-400">
                Set an API token in the top bar first.
              </div>
            )}
          </Card>
        )}

        {/* ======================================================
            VIDEO PLAYER
        ====================================================== */}

        <Card
          title="Interview Recording Playback"
          description="Review a local interview video with WebVTT captions."
        >
          <VideoPlayer />
        </Card>

        {/* ======================================================
            AUDIO VISUALIZATION
        ====================================================== */}

        <Card title="Audio Visualization">
          <div className="relative flex h-12 items-end gap-px overflow-hidden sm:h-16 sm:gap-[2px]">

            {audioLevels.map((level, i) => (
              <div
                key={i}
                className="flex-1 rounded-t transition-all duration-75"
                style={{
                  height: `${Math.max(
                    2,
                    (level / maxLevel) * 100
                  )}%`,

                  backgroundColor:
                    level / maxLevel > 0.7
                      ? "#ef4444"
                      : level / maxLevel > 0.4
                        ? "#f59e0b"
                        : "#6366f1",

                  opacity: isLive ? 1 : 0.3,
                }}
              />
            ))}

            {!videoEnabled && (
              <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center text-muted">
                <VideoOff
                  size={48}
                  className="mb-3 opacity-30"
                />

                <p className="text-sm">
                  Camera is off
                </p>
              </div>
            )}

            {isPaused && videoEnabled && (
              <div className="pointer-events-none absolute inset-0 flex items-center justify-center bg-black/50">
                <div className="flex items-center gap-2 rounded-md bg-bg-panel px-4 py-2 text-sm text-zinc-300">
                  <Pause size={16} />
                  Paused
                </div>
              </div>
            )}

            {isLive && activeSession && (
              <div className="pointer-events-none left-3 top-3 rounded-md bg-black/60 px-2 py-1 text-[10px] font-mono text-zinc-300">
                {activeSession}
              </div>
            )}
          </div>

          {isLive && (
            <div className="flex flex-wrap items-center gap-2 border-t border-border px-3 py-3 sm:px-4">

              <button
                onClick={toggleAudio}
                disabled={isPaused}
                className={cn(
                  "rounded-md border border-border p-2 transition-colors disabled:cursor-not-allowed disabled:opacity-40",
                  audioEnabled
                    ? "text-zinc-300 hover:bg-bg-card"
                    : "bg-rose-500/10 text-rose-400"
                )}
                aria-label={
                  audioEnabled
                    ? "Mute"
                    : "Unmute"
                }
              >
                {audioEnabled ? (
                  <Mic size={16} />
                ) : (
                  <MicOff size={16} />
                )}
              </button>

              <button
                onClick={handlePause}
                className="rounded-md border border-border p-2 text-zinc-300 hover:bg-bg-card"
                aria-label={
                  isPaused
                    ? "Resume"
                    : "Pause"
                }
              >
                {isPaused ? (
                  <Play size={16} />
                ) : (
                  <Pause size={16} />
                )}
              </button>

              <button
                onClick={handleStop}
                className="ml-auto rounded-md bg-rose-500 px-3 py-1.5 text-xs font-medium text-white hover:bg-rose-600"
              >
                <PhoneOff
                  size={14}
                  className="mr-1 inline"
                />

                End
              </button>
            </div>
          )}
        </Card>

        {/* ======================================================
            SCORES + FEEDBACK
        ====================================================== */}

        <div className="space-y-4">

          {/* ====================================================
              EXISTING RISK SCORE
          ==================================================== */}

          <Card
            title="Risk Score"
            description="Real-time risk assessment"
          >
            <div className="flex flex-col items-center py-4">

              <div
                className={cn(
                  "flex h-24 w-24 items-center justify-center rounded-full border-4 text-2xl font-bold",

                  riskColor(riskScore) ===
                    "danger" &&
                    "border-rose-500 text-rose-400",

                  riskColor(riskScore) ===
                    "warn" &&
                    "border-amber-500 text-amber-400",

                  riskColor(riskScore) ===
                    "success" &&
                    "border-emerald-500 text-emerald-400",

                  riskColor(riskScore) ===
                    "muted" &&
                    "border-zinc-500 text-zinc-400"
                )}
              >
                {isLive
                  ? riskScore.toFixed(2)
                  : "—"}
              </div>

              <div className="mt-3 text-xs text-muted">
                {riskScore >= 0.8
                  ? "Critical risk"
                  : riskScore >= 0.6
                    ? "High risk"
                    : riskScore >= 0.3
                      ? "Medium risk"
                      : "Low risk"}
              </div>
            </div>
          </Card>

          {/* ====================================================
              ISSUE #18 - INTEGRITY SCORE
          ==================================================== */}

          <Card
            title="Integrity Score"
            description="Real-time interview integrity / trust score"
          >
            <div className="flex flex-col items-center py-4">

              <div
                className={cn(
                  "flex h-24 w-24 items-center justify-center rounded-full border-4 text-2xl font-bold",

                  integrityScore == null &&
                    "border-zinc-500 text-zinc-400",

                  integrityScore != null &&
                    integrityScore >= 0.8 &&
                    "border-emerald-500 text-emerald-400",

                  integrityScore != null &&
                    integrityScore >= 0.6 &&
                    integrityScore < 0.8 &&
                    "border-amber-500 text-amber-400",

                  integrityScore != null &&
                    integrityScore < 0.6 &&
                    "border-rose-500 text-rose-400"
                )}
              >
                {isLive &&
                integrityScore != null
                  ? integrityScore.toFixed(2)
                  : "—"}
              </div>

              <div className="mt-3 text-xs text-muted">
                {!isLive
                  ? "Start an interview to monitor integrity"
                  : integrityScore == null
                    ? sessionStatusError
                      ? "Integrity status unavailable"
                      : "Waiting for integrity analysis..."
                    : integrityScore >= 0.8
                      ? "High integrity"
                      : integrityScore >= 0.6
                        ? "Moderate integrity"
                        : "Low integrity"}
              </div>
            </div>
          </Card>

          {/* ====================================================
              LIVE AI FEEDBACK
          ==================================================== */}

          <Card
            title="Live AI Feedback"
            description="Real-time analysis feed"
          >
            <div className="max-h-64 space-y-2 overflow-y-auto">

              {feedback.length === 0 ? (
                <div className="py-4 text-center text-xs text-muted">
                  {isLive
                    ? "Waiting for analysis..."
                    : "Start an interview to see feedback"}
                </div>
              ) : (
                feedback.map((f, i) => (
                  <div
                    key={i}
                    className="rounded-md border border-border bg-bg-card px-3 py-2 text-xs text-zinc-300"
                  >
                    {f}
                  </div>
                ))
              )}
            </div>
          </Card>

          {/* ====================================================
              SESSION INFO
          ==================================================== */}

          <Card title="Session Info">
            <div className="space-y-2 text-sm">

              <div className="flex items-center justify-between gap-3">
                <span className="shrink-0 text-muted">
                  Session
                </span>

                <span className="truncate font-mono text-xs text-zinc-300">
                  {activeSession || "—"}
                </span>
              </div>

              <div className="flex items-center justify-between gap-3">
                <span className="shrink-0 text-muted">
                  Candidate
                </span>

                <span className="truncate text-zinc-300">
                  {candidate || "—"}
                </span>
              </div>

              <div className="flex justify-between">
                <span className="text-muted">
                  Status
                </span>

                {isLive ? (
                  <Badge variant="success">
                    Live
                  </Badge>
                ) : (
                  <Badge variant="muted">
                    Idle
                  </Badge>
                )}
              </div>
          </div>
        </Card>



            
              {/* ==================================================
                  ISSUE #18 - Integrity status
              ================================================== */}

              <div className="flex justify-between">
                <span className="text-muted">
                  Integrity
                </span>

                {integrityScore != null ? (
                  <Badge variant="success">
                    {integrityScore.toFixed(2)}
                  </Badge>
                ) : (
                  <Badge variant="muted">
                    —
                  </Badge>
                )}
              </div>

         

          {/* ====================================================
              RISK TIMELINE
          ==================================================== */}

          <Card
            title="Risk Timeline"
            description={
              isLive
                ? "Real-time interview events and risk history."
                : "Timeline will appear after the interview starts."
            }
          >
            {isLive ? (
              <RiskTimeline
                moments={moments}
              />
            ) : (
              <div className="flex h-32 items-center justify-center text-center text-sm text-muted">
                Interview not started
              </div>
            )}
          </Card>

        </div>
      </div>
    </ErrorBoundary>
  );
}
