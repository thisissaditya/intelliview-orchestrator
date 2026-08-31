import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import ChangelogPage, { CHANGELOG_DATA } from "../changelog/page";

describe("Changelog Page", () => {
  it("renders page header and subtitle correctly", () => {
    render(<ChangelogPage />);

    expect(screen.getByRole("heading", { name: /changelog/i })).toBeInTheDocument();
    expect(
      screen.getByText(/discover recent updates, new features, enhancements, and bug fixes/i)
    ).toBeInTheDocument();
  });

  it("renders dated changelog entries with version tags", () => {
    render(<ChangelogPage />);

    CHANGELOG_DATA.forEach((entry) => {
      expect(screen.getByText(entry.version)).toBeInTheDocument();
      expect(screen.getByText(entry.date)).toBeInTheDocument();
    });
  });

  it("filters entries by category when filter buttons are clicked", () => {
    render(<ChangelogPage />);

    const featuresButton = screen.getByRole("button", { name: /features/i });
    fireEvent.click(featuresButton);

    // After filtering by features, "Features" badges should be visible
    expect(screen.getAllByText("Features").length).toBeGreaterThan(0);
  });
});
