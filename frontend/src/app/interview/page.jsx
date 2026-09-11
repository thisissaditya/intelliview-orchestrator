"use client";
import { useState, useRef, useEffect, useCallback } from "react";
import useSWR from "swr";
import {
  Video,
  VideoOff,
  Mic,
  MicOff,
  Phone,
  PhoneOff,
  Pause,
  Play,
  AlertTriangle,
  Activity,
  Radio,
  Volume2,
} from "lucide-react";
import Card from "@/components/Card";
import { Badge } from "@/components/Badge";
import { Skeleton, ErrorState, EmptyState } from "@/components/States";
import VideoPlayer from "@/components/VideoPlayer";
import { endpoints } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import { toast } from "@/lib/toast";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useMomentTracking } from "@/hooks/useMomentTracking";
import  RiskTimeline  from "@/components/RiskTimeline";
import { cn, riskColor } from "@/lib/utils";
import { ErrorBoundary } from "@/components/ErrorBoundary";

// Persisted so a refresh doesn't silently drop a paused interview back to
// the "start a new one" screen. Only UI state is restored here (not the
// camera/mic stream, which the browser can't hand back without a fresh
// getUserMedia call) — risk-scoring is untouched by any of this.
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
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const audioCtxRef = useRef(null);
  const animFrameRef = useRef(null);

  const persisted = useRef(typeof window !== "undefined" ? readPersistedSession() : null);

  const [videoEnabled, setVideoEnabled] = useState(false);
  const [audioEnabled, setAudioEnabled] = useState(true);
  const [isPaused, setIsPaused] = useState(() => persisted.current?.isPaused ?? false);
  const [isLive, setIsLive] = useState(() => persisted.current?.isLive ?? false);
  const [activeSession, setActiveSession] = useState(() => persisted.current?.activeSession ?? null);
  const [riskScore, setRiskScore] = useState(0);
  const [feedback, setFeedback] = useState([]);
  const [audioLevels, setAudioLevels] = useState(new Array(32).fill(0));
  const [candidate, setCandidate] = useState(() => persisted.current?.candidate ?? "");
  const [starting, setStarting] = useState(false);

  // Keep the persisted copy in sync while an interview is live; clear it
  // once the interview ends so a later refresh doesn't resurrect it.
  useEffect(() => {
    if (typeof window === "undefined") return;
    if (!isLive) {
      window.localStorage.removeItem(SESSION_STORAGE_KEY);
      return;
    }
    window.localStorage.setItem(
      SESSION_STORAGE_KEY,
      JSON.stringify({ isLive, isPaused, activeSession, candidate })
    );
  }, [isLive, isPaused, activeSession, candidate]);

  const {
    moments,
    isTracking,
    startTracking,
    stopTracking,
    trackEvent,
  } = useMomentTracking(activeSession);

  const { connected } = useWebSocket({
    path: "/monitoring/ws/metrics",
    enabled: !!token && isLive,
    onMessage: (data) => {
      if (data?.risk_score != null) setRiskScore(data.risk_score);
      if (data?.feedback) setFeedback((prev) => [...prev, data.feedback].slice(-20));
    },
  });

  const startCamera = useCallback(async () => {
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
    } catch (err) {
      toast.error("Camera access denied", err instanceof Error ? err.message : String(err));
    }
  }, []);

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    if (audioCtxRef.current) {
      audioCtxRef.current.close();
      audioCtxRef.current = null;
    }
    if (animFrameRef.current) {
      cancelAnimationFrame(animFrameRef.current);
      animFrameRef.current = null;
    }
    if (videoRef.current) videoRef.current.srcObject = null;
    setVideoEnabled(false);
    setAudioLevels(new Array(32).fill(0));
  }, []);

  useEffect(() => {
    return () => stopCamera();
  }, [stopCamera]);

  const toggleAudio = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getAudioTracks().forEach((t) => {
        t.enabled = !audioEnabled;
      });
    }
    setAudioEnabled((v) => !v);
  }, [audioEnabled]);

  const handleStart = async () => {
    if (!candidate.trim()) {
      toast.warn("Enter a candidate ID", "Required to start the interview");
      return;
    }
    setStarting(true);
    try {
      const r = await endpoints.startInterview({ candidate_id: candidate.trim(), priority: "high" });
      setActiveSession(r.session_id);
      setIsLive(true);
      await startCamera();
      startTracking();
      trackEvent("session_start", { candidate_id: candidate.trim() });
      toast.success("Interview started", `Session ${r.session_id}`);
    } catch (err) {
      toast.error("Failed to start", err instanceof Error ? err.message : String(err));
    } finally {
      setStarting(false);
    }
  };

  const handleStop = () => {
    trackEvent("session_end", { duration: moments.length * 1000 });
    stopTracking();
    stopCamera();
    setIsLive(false);
    setActiveSession(null);
    setIsPaused(false);
    setRiskScore(0);
    setFeedback([]);
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(SESSION_STORAGE_KEY);
    }
    toast.info("Interview ended");
  };

  const handlePause = () => {
    setIsPaused((v) => !v);
    if (streamRef.current) {
      streamRef.current.getVideoTracks().forEach((t) => {
        t.enabled = isPaused;
      });
    }
    toast.info(isPaused ? "Resumed" : "Paused");
  };

  const maxLevel = Math.max(...audioLevels, 1);

  return (
    <ErrorBoundary>
      <div className="space-y-6 animate-fade-in">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="text-xl font-semibold text-zinc-50 sm:text-2xl">Live Interview</h1>
            <p className="text-sm text-muted">Real-time video feed with AI-powered analysis.</p>
          </div>
          {isLive && (
            <div className="flex items-center gap-2">
              <Radio size={12} className="text-emerald-400 animate-pulse" />
              <span className="text-xs text-emerald-400">LIVE</span>
              {isPaused && (
                <Badge variant="warn" className="ml-1">
                  Paused
                </Badge>
              )}
            </div>
          )}
        </div>

        {isLive && isPaused && (
          <div className="flex items-center gap-2 rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2.5 text-sm text-amber-300 sm:gap-3">
            <Pause size={16} className="shrink-0" />
            <span className="font-medium">Interview Paused</span>
            <span className="hidden text-amber-300/70 sm:inline">
              Camera, mic, and controls are on hold until you resume.
            </span>
          </div>
        )}

        {!isLive && (
          <Card title="Start interview" description="Begin a new live interview session.">
            <div className="flex flex-col items-stretch gap-3 sm:flex-row sm:flex-wrap sm:items-end">
              <div className="w-full sm:min-w-[200px] sm:flex-1">
                <label className="block text-xs text-muted">Candidate ID</label>
                <input
                  value={candidate}
                  onChange={(e) => setCandidate(e.target.value)}
                  placeholder="cand-1234"
                  className="mt-1 w-full rounded-md border border-border bg-bg-card px-3 py-2 text-sm text-zinc-100 placeholder:text-muted focus:border-accent focus:outline-none"
                />
              </div>
              <button
                onClick={handleStart}
                disabled={!token || starting || !candidate.trim()}
                className="flex w-full items-center justify-center gap-2 rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-dark disabled:opacity-50 sm:w-auto sm:justify-start"
              >
                <Video size={14} /> {starting ? "Starting..." : "Start Interview"}
              </button>
            </div>
            {!token && (
              <div className="mt-2 text-xs text-amber-400">Set an API token in the top bar first.</div>
            )}
          </Card>
        )}

          <Card title="Interview Recording Playback" description="Review a local interview video with WebVTT captions.">
            <VideoPlayer />
          </Card>

          <Card title="Audio Visualization">
          <div className="relative flex items-end gap-px h-12 overflow-hidden sm:h-16 sm:gap-[2px]">
              {audioLevels.map((level, i) => (
                <div
                  key={i}
                  className="flex-1 rounded-t transition-all duration-75"
                  style={{
                    height: `${Math.max(2, (level / maxLevel) * 100)}%`,
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
                  <VideoOff size={48} className="mb-3 opacity-30" />
                  <p className="text-sm">Camera is off</p>
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
                      audioEnabled ? "text-zinc-300 hover:bg-bg-card" : "text-rose-400 bg-rose-500/10"
                    )}
                    aria-label={audioEnabled ? "Mute" : "Unmute"}
                  >
                    {audioEnabled ? <Mic size={16} /> : <MicOff size={16} />}
                  </button>
                  <button
                    onClick={handlePause}
                    className="rounded-md border border-border p-2 text-zinc-300 hover:bg-bg-card"
                    aria-label={isPaused ? "Resume" : "Pause"}
                  >
                    {isPaused ? <Play size={16} /> : <Pause size={16} />}
                  </button>
                  <button
                    onClick={handleStop}
                    className="ml-auto rounded-md bg-rose-500 px-3 py-1.5 text-xs font-medium text-white hover:bg-rose-600"
                  >
                    <PhoneOff size={14} className="inline mr-1" />
                    End
                  </button>
                </div>
              )}
            </Card>

          <div className="space-y-4">
            <Card title="Risk Score" description="Real-time risk assessment">
              <div className="flex flex-col items-center py-4">
                <div
                  className={cn(
                    "flex h-24 w-24 items-center justify-center rounded-full border-4 text-2xl font-bold",
                    riskColor(riskScore) === "danger" && "border-rose-500 text-rose-400",
                    riskColor(riskScore) === "warn" && "border-amber-500 text-amber-400",
                    riskColor(riskScore) === "success" && "border-emerald-500 text-emerald-400",
                    riskColor(riskScore) === "muted" && "border-zinc-500 text-zinc-400"
                  )}
                >
                  {isLive ? riskScore.toFixed(2) : "—"}
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

            <Card title="Live AI Feedback" description="Real-time analysis feed">
              <div className="max-h-64 space-y-2 overflow-y-auto">
                {feedback.length === 0 ? (
                  <div className="py-4 text-center text-xs text-muted">
                    {isLive ? "Waiting for analysis..." : "Start an interview to see feedback"}
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

            <Card title="Session Info">
              <div className="space-y-2 text-sm">
                <div className="flex items-center justify-between gap-3">
                  <span className="shrink-0 text-muted">Session</span>
                  <span className="truncate font-mono text-xs text-zinc-300">{activeSession || "—"}</span>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <span className="shrink-0 text-muted">Candidate</span>
                  <span className="truncate text-zinc-300">{candidate || "—"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted">Status</span>
                  {isLive ? (
                    <Badge variant="success">Live</Badge>
                  ) : (
                    <Badge variant="muted">Idle</Badge>
                  )}
                </div>
                <div className="flex justify-between">
                  <span className="text-muted">WS</span>
                  {connected ? (
                    <Badge variant="success">Connected</Badge>
                  ) : (
                    <Badge variant="muted">Disconnected</Badge>
                  )}
                </div>
                <div className="flex justify-between">
                  <span className="text-muted">Tracking</span>
                  {isTracking ? (
                    <Badge variant="success">{moments.length} moments</Badge>
                  ) : (
                    <Badge variant="muted">Inactive</Badge>
                  )}
                </div>
              </div>
            </Card>

            <Card
    title="Risk Timeline"
    description={
      isLive
        ? "Real-time interview events and risk history."
        : "Timeline will appear after the interview starts."
    }
  >
    {isLive ? (
      <RiskTimeline moments={moments} />
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

