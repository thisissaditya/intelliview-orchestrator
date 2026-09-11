
"use client";

import { useAppStore } from "@/lib/store";
import { useThemeStore } from "@/lib/theme";
import { useUIStore } from "@/lib/ui-store";
import { useNotifications } from "@/lib/notification-context";

import { useEffect, useRef, useState } from "react";

import {
  Bell,
  CheckCheck,
  Keyboard,
  Lock,
  LogIn,
  LogOut,
  Menu,
  Monitor,
  Moon,
  Radio,
  Search,
  Sun,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { Tooltip } from "@/components/Tooltip";
import { useWebSocket } from "@/hooks/useWebSocket";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

/**
 * Format notification timestamps without adding another dependency.
 */
function formatNotificationTime(timestamp) {
  const diff = Date.now() - timestamp;

  if (diff < 60 * 1000) {
    return "Just now";
  }

  if (diff < 60 * 60 * 1000) {
    return `${Math.floor(diff / (60 * 1000))}m ago`;
  }

  if (diff < 24 * 60 * 60 * 1000) {
    return `${Math.floor(diff / (60 * 60 * 1000))}h ago`;
  }

  return new Date(timestamp).toLocaleDateString();
}

/**
 * Topbar — the main navigation header of the dashboard.
 *
 * Contains:
 * - Mobile menu
 * - Command palette
 * - Live WebSocket status
 * - Notification bell + unread count
 * - Theme toggle
 * - Keyboard shortcuts
 * - Screen lock
 * - API token management
 */
function Topbar() {
  const { token, setToken } = useAppStore();

  const theme = useThemeStore((s) => s.theme);
  const cycleTheme = useThemeStore((s) => s.cycle);

  const setMobile = useUIStore((s) => s.setMobileSidebar);

  const {
    notifications,
    unreadCount,
    markAllAsRead,
    markAsRead,
  } = useNotifications();

  const [draft, setDraft] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);

  const notificationRef = useRef(null);

  useEffect(() => {
    setDraft(token || "");
  }, [token]);

  useEffect(() => {
    const onPalette = () => setPaletteOpen(true);
    const onHelp = () => setHelpOpen(true);

    window.addEventListener("open-command-palette", onPalette);
    window.addEventListener("open-shortcuts-help", onHelp);

    return () => {
      window.removeEventListener(
        "open-command-palette",
        onPalette
      );
      window.removeEventListener(
        "open-shortcuts-help",
        onHelp
      );
    };
  }, []);

  /*
   * Close notification dropdown when clicking outside.
   */
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (
        notificationRef.current &&
        !notificationRef.current.contains(event.target)
      ) {
        setNotificationsOpen(false);
      }
    };

    document.addEventListener(
      "mousedown",
      handleClickOutside
    );

    return () => {
      document.removeEventListener(
        "mousedown",
        handleClickOutside
      );
    };
  }, []);

  const { connected } = useWebSocket({
    path: "/monitoring/ws/metrics",
    enabled: !!token,
  });

  const ThemeIcon =
    theme === "dark" ? Moon : theme === "light" ? Sun : Monitor;

  const themeLabel =
    theme === "dark"
      ? "Dark"
      : theme === "light"
        ? "Light"
        : "System";

  return (
    <header className="flex h-14 items-center justify-between border-b border-border bg-bg-panel px-3 sm:px-4">
      {/* Left: mobile menu + command palette trigger */}
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setMobile(true)}
          icon={<Menu size={16} />}
          aria-label="Open menu"
          className="md:hidden"
        />

        <button
          id="topbar-command-palette"
          onClick={() =>
            window.dispatchEvent(
              new CustomEvent("open-command-palette")
            )
          }
          className="flex items-center gap-2 rounded-md border border-border bg-bg-card px-3 py-1.5 text-xs text-muted transition-colors hover:border-accent/40 hover:text-zinc-200"
        >
          <Search size={14} />

          <span className="hidden sm:inline">
            Search&hellip;
          </span>

          <kbd className="hidden rounded border border-border bg-bg-panel px-1 text-[10px] sm:inline">
            ⌘K
          </kbd>
        </button>
      </div>

      {/* Right: status indicators + notifications + auth */}
      <div className="flex items-center gap-1.5">
        {/* Live WebSocket indicator */}
        <Tooltip
          content={
            connected
              ? "Live updates connected"
              : "Live updates disconnected"
          }
        >
          <div className="flex items-center gap-1.5 rounded-md border border-border bg-bg-card px-2.5 py-1.5 text-[10px] text-muted">
            <Radio
              size={11}
              className={
                connected
                  ? "text-emerald-400"
                  : "text-muted"
              }
            />

            <span
              className={cn(
                "hidden sm:inline",
                connected && "text-emerald-400"
              )}
            >
              {connected ? "Live" : "Offline"}
            </span>
          </div>
        </Tooltip>

        {/* Notifications */}
        <div
          ref={notificationRef}
          className="relative"
        >
          <Tooltip content="Notifications">
            <Button
              variant="secondary"
              size="sm"
              onClick={() =>
                setNotificationsOpen((open) => !open)
              }
              icon={<Bell size={14} />}
              aria-label={
                unreadCount > 0
                  ? `${unreadCount} unread notifications`
                  : "Notifications"
              }
              aria-expanded={notificationsOpen}
              className="relative"
            >
              {unreadCount > 0 && (
                <span
                  className="absolute -right-1 -top-1 flex min-w-[16px] items-center justify-center rounded-full border border-bg-panel bg-red-500 px-1 text-[9px] font-semibold leading-4 text-white"
                  aria-hidden="true"
                >
                  {unreadCount > 99 ? "99+" : unreadCount}
                </span>
              )}
            </Button>
          </Tooltip>

          {/* Notification dropdown */}
          {notificationsOpen && (
            <div className="absolute right-0 top-full z-50 mt-2 w-[320px] overflow-hidden rounded-lg border border-border bg-bg-card shadow-xl sm:w-[360px]">
              {/* Header */}
              <div className="flex items-center justify-between border-b border-border px-4 py-3">
                <div>
                  <h3 className="text-sm font-semibold text-zinc-100">
                    Notifications
                  </h3>

                  <p className="text-[11px] text-muted">
                    {unreadCount > 0
                      ? `${unreadCount} unread`
                      : "You're all caught up"}
                  </p>
                </div>

                {unreadCount > 0 && (
                  <button
                    type="button"
                    onClick={markAllAsRead}
                    className="flex items-center gap-1 text-[11px] text-accent transition-colors hover:text-accent/80"
                  >
                    <CheckCheck size={13} />
                    Mark all as read
                  </button>
                )}
              </div>

              {/* Notification list */}
              <div className="max-h-[360px] overflow-y-auto">
                {notifications.length === 0 ? (
                  <div className="flex flex-col items-center justify-center px-4 py-10 text-center">
                    <Bell
                      size={22}
                      className="mb-2 text-muted"
                    />

                    <p className="text-xs text-zinc-300">
                      No notifications
                    </p>

                    <p className="mt-1 text-[11px] text-muted">
                      New interview and system events will
                      appear here.
                    </p>
                  </div>
                ) : (
                  notifications.map((notification) => (
                    <button
                      key={notification.id}
                      type="button"
                      onClick={() =>
                        markAsRead(notification.id)
                      }
                      className={cn(
                        "flex w-full gap-3 border-b border-border px-4 py-3 text-left transition-colors hover:bg-bg-panel",
                        !notification.isRead &&
                          "bg-accent/[0.04]"
                      )}
                    >
                      {/* Unread dot */}
                      <span className="mt-1.5 flex h-2 w-2 shrink-0">
                        {!notification.isRead && (
                          <span className="h-2 w-2 rounded-full bg-accent" />
                        )}
                      </span>

                      <span className="min-w-0 flex-1">
                        <span
                          className={cn(
                            "block text-xs",
                            notification.isRead
                              ? "text-muted"
                              : "text-zinc-100"
                          )}
                        >
                          {notification.message}
                        </span>

                        <span className="mt-1 block text-[10px] text-muted">
                          {formatNotificationTime(
                            notification.timestamp
                          )}
                        </span>
                      </span>
                    </button>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        {/* Theme toggle */}
        <Tooltip
          content={`Theme: ${themeLabel} (click to cycle)`}
        >
          <Button
            variant="secondary"
            size="sm"
            onClick={cycleTheme}
            icon={<ThemeIcon size={14} />}
            aria-label="Toggle theme"
          />
        </Tooltip>

        {/* Keyboard shortcuts */}
        <Tooltip content="Keyboard shortcuts (?)">
          <Button
            variant="secondary"
            size="sm"
            onClick={() =>
              window.dispatchEvent(
                new CustomEvent("open-shortcuts-help")
              )
            }
            icon={<Keyboard size={14} />}
            aria-label="Show shortcuts"
          />
        </Tooltip>

        {/* Screen lock */}
        <Tooltip content="Lock screen">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              localStorage.setItem(
                "intelliview_screen_lock",
                "locked"
              );
              window.location.reload();
            }}
            icon={<Lock size={14} />}
            aria-label="Lock screen"
          />
        </Tooltip>

        {/* API token management */}
        {showForm ? (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              setToken(draft.trim() || null);
              setShowForm(false);
            }}
            className="flex items-center gap-2"
          >
            <Input
              type="password"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="API token"
              inputClassName="py-1.5 text-xs"
            />

            <Button
              type="submit"
              variant="primary"
              size="sm"
            >
              Save
            </Button>

            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => setShowForm(false)}
            >
              Cancel
            </Button>
          </form>
        ) : token ? (
          <Button
            variant="danger"
            size="sm"
            onClick={() => setToken(null)}
            icon={<LogOut size={14} />}
          >
            <span className="hidden sm:inline">
              Sign out
            </span>
          </Button>
        ) : (
          <Button
            variant="primary"
            size="sm"
            onClick={() => setShowForm(true)}
            icon={<LogIn size={14} />}
          >
            <span className="hidden sm:inline">
              Set API token
            </span>
          </Button>
        )}
      </div>
    </header>
  );
}

export { Topbar };
