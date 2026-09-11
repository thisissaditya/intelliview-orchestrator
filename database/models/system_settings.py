"""System settings ORM model."""

from sqlalchemy import Column, DateTime, Integer, String

from database.models._base import Base, utcnow


class SystemSettings(Base):
    """Application-wide system settings."""

    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)

    company_name = Column(
        String(255),
        nullable=False,
        default="AI-Intelliview",
    )

    default_theme = Column(
        String(50),
        nullable=False,
        default="system",
    )

    scheduling_strategy = Column(
        String(50),
        nullable=False,
        default="LEAST_LOADED",
    )

    created_at = Column(
        DateTime,
        nullable=False,
        default=utcnow,
    )

    updated_at = Column(
        DateTime,
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    def __repr__(self):
        return f"<SystemSettings(id={self.id}, " f"company_name='{self.company_name}')>"
