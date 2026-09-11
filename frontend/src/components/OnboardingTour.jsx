"use client";

import { useEffect } from "react";
import "intro.js/introjs.css";

const TOUR_STORAGE_KEY = "intelliview_onboarding_completed";

export async function startOnboardingTour() {
  const { default: introJs } = await import("intro.js");

  const tour = introJs();

  tour.setOptions({
    showProgress: true,
    showBullets: true,
    exitOnOverlayClick: false,
    disableInteraction: false,
    nextLabel: "Next",
    prevLabel: "Back",
    skipLabel: "Skip",
    doneLabel: "Finish",
    steps: [
      {
        element: '[data-tour="sidebar"]',
        title: "Navigation",
        intro:
          "Use the sidebar to navigate through the IntelliView dashboard.",
      },
      {
        element: '[data-tour="nav-interview"]',
        title: "Start an Interview",
        intro:
          "Go to Interview to configure and start an AI-powered interview.",
      },
      {
        element: '[data-tour="nav-sessions"]',
        title: "Sessions",
        intro:
          "View and manage your interview sessions from this section.",
      },
      {
        element: '[data-tour="nav-analytics"]',
        title: "Analytics",
        intro:
          "Explore interview metrics and performance analytics here.",
      },
      {
        element: '[data-tour="nav-settings"]',
        title: "Settings",
        intro:
          "Configure application preferences and system settings here.",
      },
    ],
  });

  tour.onComplete(() => {
    localStorage.setItem(TOUR_STORAGE_KEY, "true");
  });

  tour.onExit(() => {
    localStorage.setItem(TOUR_STORAGE_KEY, "true");
  });

  tour.start();
}

export default function OnboardingTour() {
  useEffect(() => {
    const completed = localStorage.getItem(TOUR_STORAGE_KEY);

    if (!completed) {
      const timer = setTimeout(() => {
        startOnboardingTour();
      }, 1000);

      return () => clearTimeout(timer);
    }
  }, []);

  return null;
}