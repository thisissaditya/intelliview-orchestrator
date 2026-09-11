"use client";

import { useEffect, useState } from "react";
import { startOnboardingTour } from "@/components/OnboardingTour";
import useSWR from "swr";
import Card from "@/components/Card";
import { Skeleton, ErrorState } from "@/components/States";
import { endpoints } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import { useThemeStore } from "@/lib/theme";
import { toast } from "@/lib/toast";
import {
  Moon,
  Sun,
  Monitor,
  Shield,
  Trash2,
  RefreshCw,
} from "lucide-react";
import { ErrorBoundary } from "@/components/ErrorBoundary";

const THEME_OPTIONS = [
  { v: "dark", label: "Dark", icon: Moon },
  { v: "light", label: "Light", icon: Sun },
  { v: "system", label: "System", icon: Monitor },
];

const STRATEGIES = ["ROUND_ROBIN", "LEAST_LOADED", "QUEUE_BASED"];

export default function SettingsPage() {
  const token = useAppStore((s) => s.token);
  const setToken = useAppStore((s) => s.setToken);

  const theme = useThemeStore((s) => s.theme);
  const setTheme = useThemeStore((s) => s.setTheme);

  const [draft, setDraft] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [switching, setSwitching] = useState(null);
  const [detecting, setDetecting] = useState(false);
  const [clearingCache, setClearingCache] = useState(false);
  const [savingSettings, setSavingSettings] = useState(false);

  const scheduling = useSWR("/scheduling-status", {
    refreshInterval: 5000,
  });

  const settings = useSWR("/settings");

  useEffect(() => {
    if (settings.data?.company_name) {
      setCompanyName(settings.data.company_name);
    }
  }, [settings.data]);

  function handleSaveToken(e) {
    e.preventDefault();
    setToken(draft.trim() || null);
    toast.success("API token updated");
  }

  function handleClearToken() {
    setToken(null);
    setDraft("");
    toast.info("Signed out");
  }

  async function handleSaveSettings(e) {
    e.preventDefault();

    const trimmedCompanyName = companyName.trim();

    if (!trimmedCompanyName) {
      toast.error("Company name is required");
      return;
    }

    setSavingSettings(true);

    try {
      await endpoints.updateSettings({
        company_name: trimmedCompanyName,
        default_theme: theme,
        scheduling_strategy:
          scheduling.data?.current_strategy || "LEAST_LOADED",
      });

      await settings.mutate();

      toast.success("Settings saved");
    } catch (err) {
      toast.error(
        "Failed to save settings",
        err instanceof Error ? err.message : String(err),
      );
    } finally {
      setSavingSettings(false);
    }
  }

  async function handleSwitch(s) {
    setSwitching(s);

    try {
      await endpoints.switchStrategy(s);
      await scheduling.mutate();

      toast.success("Strategy switched", s);
    } catch (err) {
      toast.error(
        "Failed to switch",
        err instanceof Error ? err.message : String(err),
      );
    } finally {
      setSwitching(null);
    }
  }

  async function handleDetect() {
    setDetecting(true);

    try {
      const r = await endpoints.detectFailures();

      toast.success(
        "Detection complete",
        `${r.failed_sessions_detected} failed · ${r.unhealthy_workers_detected} unhealthy · ${r.stuck_sessions_detected} stuck`,
      );
    } catch (err) {
      toast.error(
        "Detection failed",
        err instanceof Error ? err.message : String(err),
      );
    } finally {
      setDetecting(false);
    }
  }

  async function handleClearCache() {
    setClearingCache(true);

    try {
      await endpoints.clearCache();
      toast.success("Cache cleared");
    } catch (err) {
      toast.error(
        "Failed to clear cache",
        err instanceof Error ? err.message : String(err),
      );
    } finally {
      setClearingCache(false);
    }
  }

  return (
    <ErrorBoundary>
      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-semibold text-zinc-100">Settings</h1>
          <p className="mt-1 text-sm text-muted">
            API credentials, theme, and runtime controls.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs text-emerald-400">
          <Shield size={14} />
          Secure
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div className="space-y-6">
            <Card
              title="Company"
              description="Set the company name displayed in the dashboard."
            >
              {settings.error ? (
                <ErrorState
                  error={settings.error}
                  onRetry={() => settings.mutate()}
                />
              ) : !settings.data ? (
                <Skeleton className="h-10 w-full" />
              ) : (
                <form
                  onSubmit={handleSaveSettings}
                  className="flex items-center gap-2"
                >
                  <input
                    type="text"
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    placeholder="Company name"
                    maxLength={255}
                    className="flex-1 rounded-md border border-border bg-bg-card px-3 py-2 text-sm text-zinc-100 placeholder:text-muted focus:border-accent focus:outline-none"
                  />

                  <button
                    type="submit"
                    disabled={savingSettings}
                    className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-dark disabled:opacity-50"
                  >
                    {savingSettings ? "Saving..." : "Save"}
                  </button>
                </form>
              )}
            </Card>

            <Card
              title="API token"
              description="Required for worker management and protected endpoints."
            >
              <form
                onSubmit={handleSaveToken}
                className="flex items-center gap-2"
              >
                <input
                  type="password"
                  value={draft || token || ""}
                  onChange={(e) => setDraft(e.target.value)}
                  placeholder="paste API_TOKEN"
                  className="flex-1 rounded-md border border-border bg-bg-card px-3 py-2 text-sm text-zinc-100 placeholder:text-muted focus:border-accent focus:outline-none"
                />

                <button
                  type="submit"
                  className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-dark"
                >
                  Save
                </button>

                {token && (
                  <button
                    type="button"
                    onClick={handleClearToken}
                    className="rounded-md border border-border bg-bg-card px-3 py-2 text-sm text-zinc-300 hover:bg-bg-panel"
                  >
                    Clear
                  </button>
                )}
              </form>
            </Card>

            <Card
              title="Appearance"
              description="Choose how the dashboard looks."
            >
              <div className="flex flex-wrap items-center gap-2">
                {THEME_OPTIONS.map((opt) => {
                  const Icon = opt.icon;
                  const active = theme === opt.v;

                  return (
                    <button
                      key={opt.v}
                      onClick={() => {
                        setTheme(opt.v);
                        toast.info(`Theme: ${opt.label}`);
                      }}
                      className={
                        "flex items-center gap-2 rounded-md border px-3 py-1.5 text-xs font-medium transition-all " +
                        (active
                          ? "border-accent bg-accent/15 text-accent-light"
                          : "border-border bg-bg-card text-zinc-300 hover:border-accent/40")
                      }
                    >
                      <Icon size={14} />
                      {opt.label}
                    </button>
                  );
                })}
              </div>
            </Card>
          </div>


        <div className="rounded-lg border border-border bg-bg-panel p-5">
          <h3 className="text-sm font-semibold text-zinc-100">
            Onboarding Tour
          </h3>

          <p className="mt-1 text-sm text-muted">
            Take a quick tour to learn about the main features of IntelliView.
          </p>

          <button
            type="button"
            onClick={startOnboardingTour}
            className="mt-4 rounded-md bg-accent px-4 py-2 text-sm font-medium text-white transition hover:opacity-90"
          >
            Take Tour
          </button>
        </div>
      </div>
          <div className="space-y-6">
            <Card
              title="Load balancing"
              description="Switch the active strategy at runtime."
            >
              {scheduling.error ? (
                <ErrorState
                  error={scheduling.error}
                  onRetry={() => scheduling.mutate()}
                />
              ) : !scheduling.data ? (
                <Skeleton className="h-20 w-full" />
              ) : (
                <div className="flex flex-wrap items-center gap-2">
                  {STRATEGIES.map((s) => {
                    const active =
                      scheduling.data.current_strategy === s;

                    return (
                      <button
                        key={s}
                        disabled={switching !== null}
                        onClick={() => handleSwitch(s)}
                        className={
                          "rounded-md border px-3 py-1.5 text-xs font-medium transition-all " +
                          (active
                            ? "border-accent bg-accent/15 text-accent-light"
                            : "border-border bg-bg-card text-zinc-300 hover:border-accent/40")
                        }
                      >
                        {s} {switching === s ? "..." : ""}
                      </button>
                    );
                  })}
                </div>
              )}
            </Card>

            <Card
              title="System maintenance"
              description="Run diagnostics and clear caches."
            >
              <div className="flex flex-wrap items-center gap-3">
                <button
                  disabled={detecting}
                  onClick={handleDetect}
                  className="flex items-center gap-2 rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-dark disabled:opacity-50"
                >
                  <RefreshCw
                    size={14}
                    className={detecting ? "animate-spin" : ""}
                  />
                  {detecting ? "Scanning..." : "Run detection"}
                </button>

                <button
                  disabled={clearingCache}
                  onClick={handleClearCache}
                  className="flex items-center gap-2 rounded-md border border-border bg-bg-card px-4 py-2 text-sm text-zinc-300 hover:border-rose-500/40 hover:text-rose-300 disabled:opacity-50"
                >
                  <Trash2 size={14} />
                  {clearingCache ? "Clearing..." : "Clear cache"}
                </button>
              </div>
            </Card>
          </div>
        </div>

    </ErrorBoundary>
  );
}
