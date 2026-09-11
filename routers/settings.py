"""System settings routes."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database.db import get_db
from database.models.system_settings import SystemSettings
from workers.risk_engine import RiskScoringEngine

logger = logging.getLogger(__name__)


class SettingsUpdateRequest(BaseModel):
    """Request model for updating system settings."""

    company_name: str = Field(min_length=1, max_length=255)
    default_theme: str = Field(min_length=1, max_length=50)
    scheduling_strategy: str = Field(min_length=1, max_length=50)


def create_settings_routes() -> APIRouter:
    """Create system settings routes."""

    router = APIRouter()

    @router.get("/api/admin/risk-config")
    async def get_risk_config():
        """Return the current live risk engine configuration."""
        pipeline_weights = RiskScoringEngine.get_pipeline_weights()
        thresholds = RiskScoringEngine.get_thresholds()

        return {
            "pipeline_weights": {
                "video": pipeline_weights[0],
                "audio": pipeline_weights[1],
                "evaluation": pipeline_weights[2],
            },
            "thresholds": {
                "low": thresholds[0],
                "medium": thresholds[1],
                "high": thresholds[2],
            },
            "video_factors": RiskScoringEngine.get_video_factors(),
            "audio_factors": RiskScoringEngine.get_audio_factors(),
            "evaluation_factors": RiskScoringEngine.get_evaluation_factors(),
        }

    @router.get("/settings")
    async def get_settings(session_db: Session = Depends(get_db)):
        """Return the persisted system settings."""
        try:
            settings = session_db.query(SystemSettings).first()

            if settings is None:
                settings = SystemSettings()
                session_db.add(settings)
                session_db.flush()

            return {
                "company_name": settings.company_name,
                "default_theme": settings.default_theme,
                "scheduling_strategy": settings.scheduling_strategy,
            }

        except Exception as exc:
            logger.error("Error fetching settings: %s", exc)
            raise HTTPException(
                status_code=500,
                detail="Error fetching settings",
            ) from exc

    @router.put("/settings")
    async def update_settings(
        request: SettingsUpdateRequest,
        session_db: Session = Depends(get_db),
    ):
        """Update and persist system settings."""
        try:
            settings = session_db.query(SystemSettings).first()

            if settings is None:
                settings = SystemSettings()
                session_db.add(settings)

            settings.company_name = request.company_name.strip()
            settings.default_theme = request.default_theme
            settings.scheduling_strategy = request.scheduling_strategy

            session_db.flush()

            return {
                "message": "Settings saved successfully",
                "company_name": settings.company_name,
                "default_theme": settings.default_theme,
                "scheduling_strategy": settings.scheduling_strategy,
            }

        except Exception as exc:
            logger.error("Error updating settings: %s", exc)
            raise HTTPException(
                status_code=500,
                detail="Error updating settings",
            ) from exc

    return router
