"""Worker registration, heartbeat, and load/scheduling status routes."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from metrics.prometheus_metrics import (
    WORKER_ACTIVE_TASKS,
    WORKER_CAPACITY,
    WORKER_HEARTBEAT_AGE_SECONDS,
    WORKERS_HEALTHY,
    WORKERS_REGISTERED,
)
from orchestrator import http_cache
from orchestrator.auth import require_token

logger = logging.getLogger(__name__)


class WorkerRegistrationRequest(BaseModel):
    """Request model for worker registration"""

    worker_id: str
    capacity: int = 4


class WorkerHeartbeatRequest(BaseModel):
    """Request model for worker heartbeat"""

    worker_id: str
    active_tasks: int


class WorkerHealthReportRequest(BaseModel):
    """Request model for worker self-reported health metrics"""

    worker_id: str
    cpu_pct: float
    memory_pct: float
    queue_depth: int


def create_worker_routes(
    worker_registry, load_balancer, scheduler, session_tracker
) -> APIRouter:
    """Create worker registration, heartbeat, and load/scheduling status routes.

    Args:
        worker_registry: WorkerRegistry instance
        load_balancer: LoadBalancer instance
        scheduler: Scheduler instance
        session_tracker: SessionTracker instance

    Returns:
        APIRouter with worker routes
    """

    router = APIRouter()

    # ========== Worker Management Endpoints ==========

    @router.post("/register-worker", dependencies=[Depends(require_token)])
    async def register_worker(request: WorkerRegistrationRequest):
        """
        Register a new worker node.

        Args:
            request: Worker registration details (worker_id, capacity)

        Returns:
            dict: Registration confirmation
        """
        try:
            logger.info(
                f"Registering worker: {request.worker_id} "
                f"with capacity {request.capacity}"
            )

            worker_registry.register_worker(
                worker_id=request.worker_id,
                capacity=request.capacity,
            )

            logger.info(f"Worker registered successfully: {request.worker_id}")

            WORKERS_REGISTERED.inc()
            WORKERS_HEALTHY.inc()

            # Ensure dashboards immediately see the newly registered worker.
            http_cache.invalidate(
                "workers",
                "worker-statistics",
                "load-status",
            )

            return {
                "status": "success",
                "message": f"Worker {request.worker_id} registered",
                "worker_id": request.worker_id,
                "capacity": request.capacity,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Error registering worker: {e!s}")
            raise HTTPException()

    @router.post("/worker/heartbeat", dependencies=[Depends(require_token)])
    async def worker_heartbeat(request: WorkerHeartbeatRequest):
        """
        Process heartbeat from worker node.

        Workers send periodic heartbeats to indicate they are alive
        and to report current active task count.

        Args:
            request: Heartbeat data (worker_id, active_tasks)

        Returns:
            dict: Heartbeat confirmation
        """
        try:
            logger.debug(
                f"Heartbeat from worker: {request.worker_id} "
                f"(active_tasks: {request.active_tasks})"
            )

            worker_registry.heartbeat(
                worker_id=request.worker_id,
                active_tasks=request.active_tasks,
            )

            WORKER_HEARTBEAT_AGE_SECONDS.labels(worker_id=request.worker_id).set(0)

            WORKER_ACTIVE_TASKS.labels(worker_id=request.worker_id).set(
                request.active_tasks
            )

            worker_status = worker_registry.get_worker(request.worker_id)

            if worker_status:
                WORKER_CAPACITY.labels(worker_id=request.worker_id).set(
                    worker_status.get("capacity", 0)
                )

            # Invalidate the workers + load caches so the next dashboard poll
            # receives the latest worker state.
            http_cache.invalidate(
                "workers",
                "worker-statistics",
                "load-status",
            )

            worker_status = worker_registry.get_worker(request.worker_id)

            health_status = (
                "healthy"
                if worker_status and worker_status.get("health_status") == "healthy"
                else "unknown"
            )

            return {
                "status": "success",
                "message": "Heartbeat received",
                "worker_id": request.worker_id,
                "health": health_status,
                "active_tasks": request.active_tasks,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Error processing heartbeat: {e!s}")
            raise HTTPException(
                status_code=500,
                detail=f"Error processing heartbeat: {e!s}",
            )

    @router.post("/worker/health-report", dependencies=[Depends(require_token)])
    async def worker_health_report(request: WorkerHealthReportRequest):
        """
        Process a periodic self-health report from a worker node.

        Workers send CPU/memory/queue depth metrics at a regular interval
        so the registry can track resource utilization per worker.

        Args:
            request: Health report data (worker_id, cpu_pct, memory_pct, queue_depth)

        Returns:
            dict: Health report confirmation
        """
        try:
            logger.debug(
                f"Health report from worker: {request.worker_id} "
                f"(cpu_pct={request.cpu_pct}, memory_pct={request.memory_pct}, "
                f"queue_depth={request.queue_depth})"
            )

            ok = worker_registry.report_health(
                worker_id=request.worker_id,
                cpu_pct=request.cpu_pct,
                memory_pct=request.memory_pct,
                queue_depth=request.queue_depth,
            )

            if not ok:
                raise HTTPException(
                    status_code=404,
                    detail=f"Worker {request.worker_id} not found",
                )

            # Invalidate the workers + statistics caches so the next
            # dashboard poll receives fresh health information.
            http_cache.invalidate(
                "workers",
                "worker-statistics",
            )

            return {
                "status": "success",
                "message": "Health report received",
                "worker_id": request.worker_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except HTTPException:
            raise

        except Exception as e:
            logger.error(f"Error processing health report: {e!s}")
            raise HTTPException(
                status_code=500,
                detail=f"Error processing health report: {e!s}",
            )

    @router.get("/workers")
    @http_cache.cached("workers", ttl=2)
    async def list_workers():
        """
        Get list of all registered workers with status.

        Returns:
            dict: Worker nodes with status information
        """
        try:
            logger.debug("Fetching worker list")

            all_workers = worker_registry.get_all_workers()
            unhealthy = worker_registry.detect_unhealthy_workers()

            workers_list = []

            for worker_id, worker_data in all_workers.items():
                is_healthy = worker_id not in unhealthy

                workers_list.append(
                    {
                        "worker_id": worker_id,
                        "capacity": worker_data.get("capacity", 0),
                        "active_tasks": worker_data.get("active_tasks", 0),
                        "available_capacity": worker_data.get("capacity", 0)
                        - worker_data.get("active_tasks", 0),
                        "health_status": ("healthy" if is_healthy else "unhealthy"),
                        "last_heartbeat": worker_data.get("last_heartbeat", None),
                        "joined_at": worker_data.get("joined_at", None),
                    }
                )

            return {
                "total_workers": len(all_workers),
                "healthy_workers": len(all_workers) - len(unhealthy),
                "unhealthy_workers": len(unhealthy),
                "workers": workers_list,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Error fetching worker list: {e!s}")
            raise HTTPException(
                status_code=500,
                detail=f"Error fetching worker list: {e!s}",
            )

    @router.get("/worker-statistics")
    @http_cache.cached("worker-statistics", ttl=2)
    async def get_worker_stats():
        """
        Get detailed worker statistics and utilization metrics.

        Returns:
            dict: Worker utilization and performance metrics
        """
        try:
            logger.debug("Generating worker statistics")

            stats = worker_registry.get_worker_statistics()

            total_capacity = stats.get("total_capacity", 0)
            total_active = stats.get("total_active_tasks", 0)

            utilization = (
                (total_active / total_capacity * 100) if total_capacity > 0 else 0
            )

            return {
                "total_workers": stats.get("total_workers", 0),
                "total_capacity": total_capacity,
                "total_active_tasks": total_active,
                "system_utilization_percent": round(utilization, 2),
                "average_utilization_per_worker": stats.get("average_active_tasks", 0),
                "min_worker_load": stats.get("min_active_tasks", 0),
                "max_worker_load": stats.get("max_active_tasks", 0),
                "idle_workers": stats.get("idle_workers", 0),
                "worker_details": stats.get("workers", []),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Error generating worker statistics: {e!s}")
            raise HTTPException(
                status_code=500,
                detail=f"Error generating worker statistics: {e!s}",
            )

    @router.get("/load-status")
    async def get_load_status():
        """
        Get current system load and capacity status.

        Provides visualization of:
        - Overall system utilization
        - Queue depth
        - Worker availability
        - Load balancer strategy recommendations

        Returns:
            dict: System load information
        """
        try:
            logger.debug("Fetching system load status")

            load_status = load_balancer.get_load_status()

            return {
                "current_strategy": load_status.get("current_strategy", "unknown"),
                "system_utilization_percent": load_status.get("system_utilization", 0),
                "available_workers": load_status.get("total_workers", 0),
                "busy_workers": load_status.get("busy_workers", 0),
                "idle_workers": load_status.get("idle_workers", 0),
                "system_at_capacity": load_status.get("system_at_capacity", False),
                "system_overloaded": load_status.get("system_overloaded", False),
                "recommended_strategy": load_status.get(
                    "recommended_strategy",
                    "LEAST_LOADED",
                ),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Error fetching load status: {e!s}")
            raise HTTPException(
                status_code=500,
                detail=f"Error fetching load status: {e!s}",
            )

    @router.get("/scheduling-status")
    async def get_scheduling_status():
        """
        Get scheduler status and health information.

        Returns:
            dict: Scheduler operational status and metrics
        """
        try:
            logger.debug("Fetching scheduler status")

            status_info = scheduler.get_scheduling_status()

            return {
                "scheduler_active": True,
                "current_strategy": load_balancer.strategy.name,
                "system_overloaded": status_info.get(
                    "system_overloaded",
                    False,
                ),
                "available_workers": status_info.get(
                    "available_workers",
                    0,
                ),
                "can_accept_tasks": scheduler.can_accept_task(),
                "recommendation": status_info.get("recommendation"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Error fetching scheduling status: {e!s}")
            raise HTTPException(
                status_code=500,
                detail=f"Error fetching scheduling status: {e!s}",
            )

    @router.delete(
        "/deregister-worker/{worker_id}",
        dependencies=[Depends(require_token)],
    )
    async def deregister_worker(worker_id: str):
        """
        Gracefully deregister a worker from the active worker pool.

        The worker is expected to enter drain mode before calling this
        endpoint. Drain mode prevents new work from being assigned while
        allowing the worker's currently running task to finish.

        Once the worker has completed its current work, the worker calls
        this endpoint and is removed from the registry.

        Args:
            worker_id: ID of the worker to deregister.

        Returns:
            dict: Deregistration confirmation.

        Raises:
            HTTPException: 404 if the worker is not registered.
            HTTPException: 500 if deregistration fails.
        """
        try:
            logger.info(
                "Received graceful deregistration request for worker: %s",
                worker_id,
            )

            # Validate that the worker is currently registered before
            # attempting to remove it.
            worker_status = worker_registry.get_worker(worker_id)

            if worker_status is None:
                logger.warning(
                    "Deregistration requested for unknown worker: %s",
                    worker_id,
                )
                raise HTTPException(
                    status_code=404,
                    detail=f"Worker {worker_id} not found",
                )

            # The worker should have already entered drain mode and
            # completed its active work before reaching this endpoint.
            # The registry operation is therefore the final removal step.
            worker_registry.deregister_worker(worker_id)

            # Invalidate all caches that can contain worker/load information.
            # Without this, the dashboard could temporarily show a worker
            # that has already been removed from the registry.
            http_cache.invalidate(
                "workers",
                "worker-statistics",
                "load-status",
            )

            logger.info(
                "Worker deregistered successfully: %s",
                worker_id,
            )

            return {
                "status": "success",
                "message": (f"Worker {worker_id} gracefully deregistered"),
                "worker_id": worker_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except HTTPException:
            raise

        except Exception as e:
            logger.error(
                "Error gracefully deregistering worker %s: %s",
                worker_id,
                e,
            )
            raise HTTPException(
                status_code=500,
                detail=f"Error deregistering worker: {e!s}",
            )

    @router.get("/worker-distribution")
    async def get_worker_distribution():
        """
        Get distribution of sessions across worker nodes.

        Returns:
            dict: Worker node -> session count mapping
        """
        try:
            distribution = session_tracker.get_worker_distribution()

            return {
                "workers": distribution,
                "total_active": sum(distribution.values()),
            }

        except Exception as e:
            logger.error(f"Error fetching worker distribution: {e!s}")
            raise HTTPException(
                status_code=500,
                detail="Error fetching worker distribution",
            )

    return router
