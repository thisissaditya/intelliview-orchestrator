"use client";

import useSWR from "swr";
import { Activity, CheckCircle2, XCircle } from "lucide-react";

import Card from "@/components/Card";
import { Skeleton, ErrorState } from "@/components/States";
import { endpoints } from "@/lib/api";

export default function StatusPage() {
  const health = useSWR("/health", endpoints.health);

  const isHealthy = health.data?.alive === true;

  return (
    <div className="mx-auto max-w-3xl space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-semibold text-zinc-50">
          System Status
        </h1>

        <p className="mt-1 text-sm text-muted">
          Current health status of the IntelliView system.
        </p>
      </div>

      <Card
        title="Overall System Health"
        description="Status reported by the system health-check endpoint."
      >
        {health.error ? (
          <div className="space-y-4">
            <div className="flex items-center gap-3 rounded-lg border border-rose-500/30 bg-rose-500/10 p-4">
              <XCircle className="text-rose-400" size={28} />

              <div>
                <div className="text-lg font-semibold text-rose-300">
                  Unhealthy
                </div>

                <p className="text-sm text-muted">
                  The system health endpoint is currently unavailable.
                </p>
              </div>
            </div>

            <ErrorState
              error={health.error}
              onRetry={() => health.mutate()}
            />
          </div>
        ) : !health.data ? (
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <Activity className="text-muted" size={28} />

              <div>
                <div className="text-sm text-muted">
                  Checking system health...
                </div>
              </div>
            </div>

            <Skeleton className="h-16 w-full" />
          </div>
        ) : isHealthy ? (
          <div className="flex items-center gap-3 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-4">
            <CheckCircle2 className="text-emerald-400" size={28} />

            <div>
              <div className="text-lg font-semibold text-emerald-300">
                Healthy
              </div>

              <p className="text-sm text-muted">
                {health.data.status || "The system is running normally."}
              </p>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-3 rounded-lg border border-rose-500/30 bg-rose-500/10 p-4">
            <XCircle className="text-rose-400" size={28} />

            <div>
              <div className="text-lg font-semibold text-rose-300">
                Unhealthy
              </div>

              <p className="text-sm text-muted">
                The system health check reports that the system is not healthy.
              </p>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}