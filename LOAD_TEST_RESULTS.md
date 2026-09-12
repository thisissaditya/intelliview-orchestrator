# Load Test Results

## 1. Objective

Identify the actual system bottleneck under load and recommend how the system should scale.

## 2. Load Testing

The system was tested with **10, 50, 100, and 500 concurrent users** using realistic interview flows.

| Concurrent users | Requests | Error rate | Median response | p95 response | p99 response |
| ---------------- | -------- | ---------- | --------------- | ------------ | ------------ |
| 10               | 1,581    | 0.00%      | 97ms            | 450ms        | 680ms        |
| 50               | 2,936    | 0.10%      | 850ms           | 6,000ms      | 7,100ms      |
| 100              | 3,195    | 0.22%      | 2,300ms         | 16,000ms     | 18,000ms     |
| 500              | 3,472    | 0.58%      | 7,300ms         | 16,000ms     | 18,000ms     |

A monitored **100-user test** was also performed while observing CPU, memory, PostgreSQL connections, and Redis activity.

## 3. Findings

At 100 concurrent users:

- **91.22% of requests failed**
- Failures were mainly **HTTP 503** on `/start-interview`
- FastAPI CPU: **0.46%**
- FastAPI memory: **10.29%**
- PostgreSQL CPU: **3.26%**
- Database connections: **1–2 active**
- Redis: **~855 ops/sec peak**

These resources had significant available capacity, so **database, Redis, and CPU were not the bottleneck**.

## 4. Actual Bottleneck

The bottleneck is the **worker capacity**.

Only one worker was running with a capacity of **4**. Four sessions were assigned, after which no additional sessions were assigned because the worker's active-task count was not released after successful completion.

## 5. Scaling Recommendation

**First:** Fix the worker slot-release/completion handling.

**Then:** Increase worker capacity and/or add more worker instances.

Increasing capacity before fixing the release problem would only delay saturation.

## 6. Safe Capacity

With the current bug, the system can permanently saturate after approximately **4 sessions**.

After fixing the release issue, perform another monitored load test to determine the actual sustained safe concurrency.

## Conclusion

The main bottleneck is **worker capacity, not database, Redis, or compute resources**. The priority is to fix worker slot release, then scale workers and retest.

---

# J6 Baseline � 10 September 2026

## 7. Baseline Load Test

A representative load test was executed using the existing Locust interview-session flow.

| Metric | Result |
|---|---:|
| Concurrent users | 10 |
| Test duration | 60 seconds |
| Spawn rate | 2 users/second |
| Total requests | 203 |
| Total failures | 129 |
| Error rate | 63.55% |
| Rate-limited responses (429) | 0 |
| Median response time | 12 ms |
| p95 response time | 80 ms |
| p99 response time | 270 ms |
| Maximum response time | ~340 ms |
| `/start-interview` failures | 129 � HTTP 503 |

All recorded failures in this run were HTTP 503 responses from `/start-interview`. No rate-limited responses were observed.

## 8. Monitoring Baseline

The J6 Grafana dashboard is provisioned as **IntelliView J6 Load Test Baseline** and uses the Prometheus datasource.

The monitored metrics include:

- HTTP p95 latency
- HTTP error rate
- Worker active tasks and capacity
- Queue depth

Worker capacity reported by Prometheus was **4**. After the load test completed, worker active tasks were **0** and queue depth was **0**.

The active-task and queue-depth values above are post-test observations, not peak values during the load test.

## 9. Baseline Observation

The 10-user representative run produced a **63.55% non-rate-limit failure rate**, with all failures occurring on `/start-interview` as HTTP 503 responses.

This result is recorded as the J6 baseline for future comparison. No performance fixes were made as part of J6.

## 10. Grafana Dashboard

Dashboard: **IntelliView J6 Load Test Baseline**

Dashboard UID: `j6-load-baseline`

The dashboard is configured to visualize the Prometheus metrics required for J6 baseline monitoring.
