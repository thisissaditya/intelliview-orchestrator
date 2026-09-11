"use client";

import { ErrorBoundary } from "@/components/ErrorBoundary";
import { useEffect, useMemo, useState } from "react";
import useSWR from "swr";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Users,
} from "lucide-react";

import Card from "@/components/Card";
import Stat from "@/components/Stat";
import { StatusBadge } from "@/components/Badge";
import { Skeleton, ErrorState, EmptyState } from "@/components/States";
import Sparkline from "@/components/Sparkline";
import { formatPercent, formatRelative } from "@/lib/utils";
import { Table, Thead, Tbody, Tr, Th, Td } from "@/components/ui";

const MAX_SAMPLES = 20;

export default function OverviewPage() {
 
  const health = useSWR("/system-health", { refreshInterval: 3000 });
  const workers = useSWR("/workers", { refreshInterval: 5000 });
  const stats = useSWR("/session-statistics", { refreshInterval: 5000 });
  const active = useSWR("/active-sessions", { refreshInterval: 3000 });
  const upcomingSchedules = useSWR("/api/schedule/upcoming", { refreshInterval: 5000 });


  const [completedHist, setCompletedHist] = useState([]);
  const [failedHist, setFailedHist] = useState([]);
  const [riskHist, setRiskHist] = useState([]);

  const completed = stats.data?.completed_sessions;
  const failed = stats.data?.failed_sessions;
  const avgRisk =
    stats.data?.risk_score_stats?.average_risk_score;

  useEffect(() => {
    if (completed == null) return;

    setCompletedHist((history) =>
      [...history, completed].slice(-MAX_SAMPLES)
    );
  }, [completed]);

  useEffect(() => {
    if (failed == null) return;

    setFailedHist((history) =>
      [...history, failed].slice(-MAX_SAMPLES)
    );
  }, [failed]);

  useEffect(() => {
    if (avgRisk == null) return;

    setRiskHist((history) =>
      [...history, avgRisk].slice(-MAX_SAMPLES)
    );
  }, [avgRisk]);

  const utilization = useMemo(() => {
    const list = workers.data?.workers ?? [];

    if (list.length === 0) {
      return 0;
    }

    const total = list.reduce(
      (acc, worker) =>
        acc +
        (worker.capacity
          ? (worker.active_tasks / worker.capacity) * 100
          : 0),
      0
    );

    return total / list.length;
  }, [workers.data?.workers]);

  return (
    <ErrorBoundary>
      <div className="space-y-6 animate-fade-in">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-zinc-50">
              Overview
            </h1>

            <p className="text-sm text-muted">
              Real-time system health and throughput.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-xs text-muted">
              Live
            </span>
          </div>
        </div>

        {/* Statistics */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {/* System */}
          <div className="glass-card p-4 animate-slide-in-up delay-0">
            <Stat
              label="System"
              value={
                health.data ? (
                  <StatusBadge
                    status={health.data.overall_status}
                  />
                ) : (
                  <Skeleton className="h-7 w-20" />
                )
              }
              hint={
                health.data
                  ? `Updated ${formatRelative(
                      health.data.timestamp
                    )}`
                  : ""
              }
              icon={<Activity size={16} />}
            />
          </div>

          {/* Workers */}
          <div className="glass-card p-4 animate-slide-in-up delay-[50ms]">
            <Stat
              label="Workers"
              value={
                workers.data ? (
                  `${workers.data.healthy_workers}/${workers.data.total_workers}`
                ) : (
                  <Skeleton className="h-7 w-12" />
                )
              }
              hint={
                workers.data
                  ? `${formatPercent(
                      utilization
                    )} utilization`
                  : ""
              }
              icon={<Users size={16} />}
            />
          </div>

          {/* Completed */}
          <div className="glass-card p-4 animate-slide-in-up delay-100">
            <Stat
              label="Completed"
              value={
                stats.data ? (
                  stats.data.completed_sessions
                ) : (
                  <Skeleton className="h-7 w-12" />
                )
              }
              hint={
                stats.data
                  ? `${stats.data.active_sessions} active · ${stats.data.failed_sessions} failed`
                  : ""
              }
              icon={<CheckCircle2 size={16} />}
            />
          </div>

          {/* Average Risk */}
          <div className="glass-card p-4 animate-slide-in-up delay-150">
            <Stat
              label="Avg risk"
              value={
                stats.data ? (
                  stats.data.risk_score_stats.average_risk_score.toFixed(
                    3
                  )
                ) : (
                  <Skeleton className="h-7 w-16" />
                )
              }
              hint={
                stats.data
                  ? `${stats.data.risk_score_stats.high_risk_sessions} high risk`
                  : ""
              }
              icon={<AlertTriangle size={16} />}
            />
          </div>
        </div>

        {/* Historical Statistics */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {/* Completed Sessions */}
          <Card
            title="Completed sessions"
            description={`Last ${MAX_SAMPLES} samples`}
          >
            <div className="flex items-center justify-between">
              <div className="text-2xl font-semibold text-zinc-50">
                {stats.data?.completed_sessions ?? "—"}
              </div>

              <Sparkline
                data={completedHist}
                color="#10b981"
                width={140}
                height={40}
              />
            </div>
          </Card>

          {/* Failed Sessions */}
          <Card
            title="Failed sessions"
            description={`Last ${MAX_SAMPLES} samples`}
          >
            <div className="flex items-center justify-between">
              <div className="text-2xl font-semibold text-zinc-50">
                {stats.data?.failed_sessions ?? "—"}
              </div>

              <Sparkline
                data={failedHist}
                color="#ef4444"
                width={140}
                height={40}
              />
            </div>
          </Card>

          {/* Average Risk */}
          <Card
            title="Average risk"
            description={`Last ${MAX_SAMPLES} samples`}
          >
            <div className="flex items-center justify-between">
              <div className="text-2xl font-semibold text-zinc-50">
                {stats.data?.risk_score_stats?.average_risk_score !=
                null
                  ? stats.data.risk_score_stats.average_risk_score.toFixed(
                      3
                    )
                  : "—"}
              </div>

              <Sparkline
                data={riskHist}
                color="#f59e0b"
                width={140}
                height={40}
              />
            </div>
          </Card>
        </div>

        {/* Component Health and Active Sessions */}
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {/* Component Health */}
          <Card
            title="Component health"
            description="Live status of each dependency."
          >
            {health.error ? (
              <ErrorState
                error={health.error}
                onRetry={() => health.mutate()}
              />
            ) : !health.data ? (
              <Skeleton className="h-32 w-full" />
            ) : (
              <ul className="space-y-2 text-sm">
                {Object.entries(
                  health.data.components || {}
                ).map(([key, value]) => (
                  <li
                    key={key}
                    className="flex items-center justify-between rounded-md border border-border bg-bg-card px-3 py-2 transition-colors hover:border-accent/30"
                  >
                    <span className="capitalize text-zinc-300">
                      {key}
                    </span>

                    <StatusBadge
                      status={value?.status || "unknown"}
                    />
                  </li>
                ))}
              </ul>
            )}
          </Card>

          {/* Active Sessions */}
          <Card
            title="Active sessions"
            description="In-flight interviews across the cluster."
          >
            {active.error ? (
              <ErrorState
                error={active.error}
                onRetry={() => active.mutate()}
              />
            ) : !active.data ? (
              <Skeleton className="h-32 w-full" />
            ) : active.data.sessions.length === 0 ? (
              <EmptyState
                title="No active sessions"
                description="Start a new interview to see it here."
              />
            ) : (
              <ul className="space-y-2 text-sm">
                {active.data.sessions
                  .slice(0, 6)
                  .map((session) => (
                    <li
                      key={session.session_id}
                      className="flex items-center justify-between rounded-md border border-border bg-bg-card px-3 py-2 transition-colors hover:border-accent/30"
                    >
                      <div>
                        <div className="font-mono text-xs text-zinc-300">
                          {session.session_id}
                        </div>

                        <div className="text-xs text-muted">
                          {session.candidate_id}
                        </div>
                      </div>

                      <StatusBadge
                        status={session.status}
                      />
                    </li>
                  ))}
              </ul>
            )}
          </Card>
        </div>

        {/* Workers */}
        <Card
          title="Workers"
          description="Currently registered worker nodes."
        >
          {workers.error ? (
            <ErrorState
              error={workers.error}
              onRetry={() => workers.mutate()}
            />
          ) : !workers.data ? (
            <Skeleton className="h-24 w-full" />
          ) : workers.data.workers.length === 0 ? (
            <EmptyState
              title="No workers registered"
              description="Workers self-register via the worker_agent on startup."
            />
          ) : (
            <Table>
              <Thead>
                <Tr>
                  <Th>Worker</Th>
                  <Th>Status</Th>
                  <Th>Load</Th>
                  <Th>Last heartbeat</Th>
                </Tr>
              </Thead>

              <Tbody>
                {workers.data.workers.map((worker) => (
                  <Tr key={worker.worker_id}>
                    <Td className="font-mono text-xs text-zinc-200">
                      {worker.worker_id}
                    </Td>

                    <Td>
                      <StatusBadge
                        status={worker.health_status}
                      />
                    </Td>

                    <Td>
                      {worker.active_tasks}/{worker.capacity}
                    </Td>

                    <Td className="text-muted">
                      {formatRelative(worker.last_heartbeat)}
                    </Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          )}
        </Card>

      <Card title="Upcoming Scheduled Interviews" description="Interviews scheduled in advance with candidate confirmation emails.">
        {upcomingSchedules.error ? (
          <ErrorState error={upcomingSchedules.error} onRetry={() => upcomingSchedules.mutate()} />
        ) : !upcomingSchedules.data ? (
          <Skeleton className="h-20 w-full" />
        ) : upcomingSchedules.data.upcoming.length === 0 ? (
          <EmptyState title="No upcoming interviews scheduled" description="Use the Schedule page to book interviews with candidate email notifications." />
        ) : (
          <Table>
            <Thead>
              <Tr>
                <Th>Candidate</Th>
                <Th>Date & Time</Th>
                <Th>Interviewer</Th>
                <Th>Status</Th>
              </Tr>
            </Thead>
            <Tbody>
              {upcomingSchedules.data.upcoming.map((sched) => (
                <Tr key={sched.id}>
                  <Td>
                    <div className="font-medium text-zinc-100">{sched.candidate_name}</div>
                    <div className="text-xs text-muted">{sched.candidate_email}</div>
                  </Td>
                  <Td className="text-indigo-300 font-mono text-xs">
                    {new Date(sched.scheduled_at).toLocaleString()}
                  </Td>
                  <Td className="text-zinc-300">{sched.interviewer_id}</Td>
                  <Td><StatusBadge status={sched.status} /></Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        )}
      </Card>
    </div>
    </ErrorBoundary>
  );
}
