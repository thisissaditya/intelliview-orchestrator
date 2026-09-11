"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { toast } from "@/lib/toast";

const NotificationContext = createContext(null);

const MAX_NOTIFICATIONS = 50;

export function NotificationProvider({ children }) {
  const [notifications, setNotifications] = useState([]);

  const addNotification = useCallback((notification) => {
    if (!notification?.message) {
      return;
    }

    const newNotification = {
      id:
        notification.id ||
        `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
      message: notification.message,
      timestamp: notification.timestamp || Date.now(),
      isRead: false,
    };

    setNotifications((current) =>
      [newNotification, ...current].slice(0, MAX_NOTIFICATIONS)
    );

    /*
     * Reuse the project's existing toast system.
     *
     * Worker/system failures get a warning toast.
     * Successful interview events get a success toast.
     * Everything else gets an informational toast.
     */
    const message = notification.message.toLowerCase();

    if (
      message.includes("down") ||
      message.includes("failed") ||
      message.includes("failure") ||
      message.includes("unhealthy")
    ) {
      toast.warn("System notification", notification.message);
    } else if (
      message.includes("completed") ||
      message.includes("complete")
    ) {
      toast.success("Interview update", notification.message);
    } else {
      toast.info("New notification", notification.message);
    }
  }, []);

  const markAllAsRead = useCallback(() => {
    setNotifications((current) =>
      current.map((notification) => ({
        ...notification,
        isRead: true,
      }))
    );
  }, []);

  const markAsRead = useCallback((id) => {
    setNotifications((current) =>
      current.map((notification) =>
        notification.id === id
          ? { ...notification, isRead: true }
          : notification
      )
    );
  }, []);

  const clearNotifications = useCallback(() => {
    setNotifications([]);
  }, []);

  /*
   * Generic browser event handler.
   *
   * This gives us a clean bridge between the notification UI
   * and the eventual real WebSocket/backend implementation.
   *
   * Example:
   *
   * window.dispatchEvent(
   *   new CustomEvent("intelliview-notification", {
   *     detail: {
   *       message: "Interview completed",
   *     },
   *   })
   * );
   */
  useEffect(() => {
    const handleNotification = (event) => {
      const data = event.detail;

      if (!data?.message) {
        return;
      }

      addNotification(data);
    };

    window.addEventListener(
      "intelliview-notification",
      handleNotification
    );

    return () => {
      window.removeEventListener(
        "intelliview-notification",
        handleNotification
      );
    };
  }, [addNotification]);

  /*
   * Local mock real-time notifications.
   *
   * Disabled by default.
   *
   * Enable from browser console:
   *
   * localStorage.setItem(
   *   "intelliview_mock_notifications",
   *   "true"
   * );
   *
   * Then refresh the page.
   */
  useEffect(() => {
    if (
      typeof window === "undefined" ||
      localStorage.getItem("intelliview_mock_notifications") !==
        "true"
    ) {
      return;
    }

    const mockMessages = [
      "Interview completed",
      "Worker down",
      "Interview started",
      "Candidate joined the interview",
      "Interview report is ready",
    ];

    const interval = window.setInterval(() => {
      const message =
        mockMessages[Math.floor(Math.random() * mockMessages.length)];

      addNotification({
        message,
      });
    }, 10000);

    return () => {
      window.clearInterval(interval);
    };
  }, [addNotification]);

  const unreadCount = notifications.filter(
    (notification) => !notification.isRead
  ).length;

  const value = useMemo(
    () => ({
      notifications,
      unreadCount,
      addNotification,
      markAllAsRead,
      markAsRead,
      clearNotifications,
    }),
    [
      notifications,
      unreadCount,
      addNotification,
      markAllAsRead,
      markAsRead,
      clearNotifications,
    ]
  );

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
}

export function useNotifications() {
  const context = useContext(NotificationContext);

  if (!context) {
    throw new Error(
      "useNotifications must be used inside NotificationProvider"
    );
  }

  return context;
}

