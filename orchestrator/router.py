"""
router.py — Risk Weight Configuration API
Exposes CRUD endpoints for recruiters to manage per-position risk weights.
"""

from fastapi import APIRouter, HTTPException, status

from orchestrator import store
from orchestrator.models import RiskConfigCreate, RiskConfigResponse, RiskConfigUpdate

router = APIRouter(prefix="/risk-configs", tags=["Risk Weight Configuration"])
engine_router = APIRouter(prefix="/risk-engine", tags=["Risk Engine Integration"])


@engine_router.get(
    "/weights/{job_position}",
    summary="Get risk weights for a given job position",
)
def get_risk_engine_weights(job_position: str):
    """
    Used by the risk engine to get weights for scoring.
    Returns custom weights if configured, else defaults.
    """
    from orchestrator.models import RiskWeights

    config = store.get_config_by_position(job_position)
    if config:
        return {"is_custom": True, "weights": config.weights.model_dump()}
    return {"is_custom": False, "weights": RiskWeights().model_dump()}


@router.post(
    "/",
    response_model=RiskConfigResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a risk weight configuration for a job position",
)
def create_config(data: RiskConfigCreate):
    """
    Create a new risk weight configuration for a specific job position.

    - **job_position**: unique name e.g. "Software Engineer"
    - **weights**: per-signal weights (all >= 0, at least one > 0)
    - **description**: optional notes for this config
    """
    try:
        return store.create_config(data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get(
    "/",
    response_model=list[RiskConfigResponse],
    summary="List all risk weight configurations",
)
def list_configs():
    """Return all stored job-position risk weight configurations."""
    return store.list_configs()


@router.get(
    "/{config_id}",
    response_model=RiskConfigResponse,
    summary="Get a specific risk weight configuration by ID",
)
def get_config(config_id: str):
    config = store.get_config(config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Config '{config_id}' not found",
        )
    return config


@router.get(
    "/by-position/{job_position}",
    response_model=RiskConfigResponse,
    summary="Get risk weight configuration by job position name",
)
def get_by_position(job_position: str):
    """Look up config by job position name (case-insensitive)."""
    config = store.get_config_by_position(job_position)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No config found for position '{job_position}'. Default weights will be used.",
        )
    return config


@router.put(
    "/{config_id}",
    response_model=RiskConfigResponse,
    summary="Update a risk weight configuration",
)
def update_config(config_id: str, data: RiskConfigUpdate):
    """
    Partially update an existing configuration.
    Only fields provided in the request body are updated.
    """
    config = store.update_config(config_id, data)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Config '{config_id}' not found",
        )
    return config


@router.delete(
    "/{config_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a risk weight configuration",
)
def delete_config(config_id: str):
    """Delete a configuration. The risk engine will fall back to defaults."""
    deleted = store.delete_config(config_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Config '{config_id}' not found",
        )
