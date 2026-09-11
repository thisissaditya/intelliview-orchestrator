"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import useSWR from "swr";
import { cn } from "@/lib/utils";
import { endpoints } from "@/lib/api";

import {
  LayoutDashboard,
  Users,
  Activity,
  BarChart3,
  Settings,
  Shield,
  Video,
  UserCircle,
  Mail,
  Calendar
} from "lucide-react";

const items = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/schedule", label: "Schedule", icon: Calendar },
  { href: "/interview", label: "Interview", icon: Video },
  { href: "/sessions", label: "Sessions", icon: Activity },
  { href: "/candidates", label: "Candidates", icon: UserCircle },
  { href: "/workers", label: "Workers", icon: Users },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/settings", label: "Settings", icon: Settings },
  {
    href: "http://localhost:8080",
    label: "Digest Control",
    icon: Mail,
    external: true,
  },
];

function Sidebar({ mobile = false, onNavigate }) {
  const pathname = usePathname();

  const { data: settings } = useSWR("/settings");

  const companyName = settings?.company_name || "AI-Intelliview";

  return (
    <aside
      className={cn(
        mobile
          ? "flex w-full flex-col"
          : "hidden w-60 shrink-0 border-r border-border bg-bg-panel md:flex md:flex-col"
      )}
    >
      <div className="flex h-14 items-center gap-2 border-b border-border px-5">
        <div className="flex h-8 w-8 items-center justify-center rounded-md bg-accent text-white">
          <Shield size={16} />
        </div>

        <div className="min-w-0">
          <div className="truncate text-sm font-semibold text-zinc-100">
            {companyName}
          </div>
          <div className="text-[10px] uppercase tracking-wider text-muted">
            Orchestrator
          </div>
        </div>
      </div>

      <nav
        className="flex-1 space-y-0.5 p-3"
        data-tour="sidebar"
      >
        {items.map((it) => {
          const active =
            pathname === it.href ||
            (it.href !== "/" && pathname.startsWith(it.href));

          const tourTarget =
            it.href === "/interview"
              ? "nav-interview"
              : it.href === "/sessions"
                ? "nav-sessions"
                : it.href === "/analytics"
                  ? "nav-analytics"
                  : it.href === "/settings"
                    ? "nav-settings"
                    : undefined;

          const linkClassName = cn(
            "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition",
            it.external
              ? "text-zinc-400 hover:bg-bg-card hover:text-zinc-100"
              : active
                ? "bg-accent/15 text-accent-light"
                : "text-zinc-400 hover:bg-bg-card hover:text-zinc-100"
          );

          const commonProps = {
            onClick: onNavigate,
            className: linkClassName,
            ...(tourTarget ? { "data-tour": tourTarget } : {}),
          };

          if (it.external) {
            return (
              <a
                key={it.href}
                href={it.href}
                target="_blank"
                rel="noopener noreferrer"
                {...commonProps}
              >
                <it.icon size={16} />
                <span>{it.label}</span>
              </a>
            );
          }

          return (
            <Link
              key={it.href}
              href={it.href}
              {...commonProps}
            >
              <it.icon size={16} />
              <span>{it.label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-border p-4 text-[10px] text-muted">
        v0.2.0 · © Mukta Redij
      </div>
    </aside>
  );
}

export { Sidebar };
