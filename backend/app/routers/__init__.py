"""API v1 router registry."""

from app.routers import (
    admin_catalog,
    assessments,
    auth,
    profile,
    progress,
    recommendations,
)

__all__ = [
    "admin_catalog",
    "assessments",
    "auth",
    "profile",
    "progress",
    "recommendations",
]
