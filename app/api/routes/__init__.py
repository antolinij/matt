"""
API Routes Package

This module exports all API routers for the application.
Import this module to include all route handlers in your FastAPI application.
"""

from app.api.routes.auth import router as auth_router
from app.api.routes.invoices import router as invoices_router
from app.api.routes.payments import router as payments_router
from app.api.routes.schools import router as schools_router
from app.api.routes.students import router as students_router

__all__ = [
    "schools_router",
    "students_router",
    "invoices_router",
    "payments_router",
    "auth_router",
]
