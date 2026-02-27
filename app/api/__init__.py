"""
API Package

This module exports all API routers for the application.
Import routers from the routes subpackage to include them in your FastAPI application.
"""
from app.api.routes import (
    schools_router,
    students_router,
    invoices_router,
    payments_router,
)

__all__ = [
    "schools_router",
    "students_router",
    "invoices_router",
    "payments_router",
]
