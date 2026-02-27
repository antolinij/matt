"""
Mattilda School Management API

FastAPI application for managing schools, students, invoices, and payments.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from contextlib import asynccontextmanager
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.core.config import settings
from app.core.database import engine, Base
from app.core.cache import cache_service
from app.api.routes import schools_router, students_router, invoices_router, payments_router, auth_router
from app.services.event_service import event_service
from app.core.metrics import (
    observe_attempt,
    observe_error,
    observe_failure,
    observe_request,
    observe_success,
    request_timer,
)
from app.core.exceptions import (
    RepositoryException,
    DuplicateRecordException,
    RecordNotFoundException,
    DatabaseConnectionException,
    ForeignKeyViolationException,
    InvalidDataException,
    DatabaseOperationException,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events

    Startup: Create database tables
    Shutdown: Dispose of the database engine
    """
    # Startup: Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    # Shutdown: close cache connections
    await cache_service.close()

    # Shutdown: close event queue connections
    await event_service.close()

    # Shutdown: Dispose of the engine
    await engine.dispose()


# Initialize FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    ## Mattilda School Management System

    A comprehensive API for managing schools, students, invoices, and payments.

    ### Features

    * **Schools**: Complete CRUD operations for educational institutions
    * **Students**: Manage student enrollment and status
    * **Invoices**: Generate and track student invoices
    * **Payments**: Record and manage payments against invoices
    * **Account Status**: Financial summaries for schools and students

    ### Architecture

    * **Clean Architecture**: Separated layers (routes → services → repositories → models)
    * **Async/Await**: Fully asynchronous for better performance
    * **Connection Pooling**: Optimized for high-traffic scenarios
    * **Repository Pattern**: Clean data access layer
    * **Service Layer**: Business logic separation

    ### Performance Optimizations

    * **Async Database Operations**: Non-blocking I/O
    * **Connection Pool**: 20 base connections, 40 overflow (60 max)
    * **Optimized Queries**: N+1 problems eliminated with JOIN operations
    * **Pagination Support**: All list endpoints support skip/limit parameters

    ### API Structure

    All endpoints are prefixed with `/api`:

    * `/api/schools` - School management
    * `/api/students` - Student management
    * `/api/invoices` - Invoice management
    * `/api/payments` - Payment management
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.get_cors_methods(),
    allow_headers=settings.get_cors_headers(),
)


@app.middleware("http")
async def normalize_trailing_slash(request: Request, call_next):
    """Accept both `/path` and `/path/` without redirecting."""
    path = request.scope.get("path", "")
    if path not in ("", "/") and path.endswith("/"):
        request.scope["path"] = path.rstrip("/")
    return await call_next(request)


@app.middleware("http")
async def collect_http_metrics(request: Request, call_next):
    """Collect request count, latency, and unhandled error metrics."""
    started_at = request_timer()
    observe_attempt(request)
    try:
        response = await call_next(request)
        observe_request(request, response.status_code, started_at)
        if response.status_code < 400:
            observe_success(request, response.status_code)
        else:
            observe_failure(request, response.status_code)
        if response.status_code >= 500:
            observe_error(request, response.status_code, "server_error")
        return response
    except Exception:
        observe_failure(request, 500)
        observe_request(request, 500, started_at)
        observe_error(request, 500, "unhandled_exception")
        raise


# Global Exception Handlers
@app.exception_handler(DuplicateRecordException)
async def duplicate_record_exception_handler(request: Request, exc: DuplicateRecordException):
    """Handle duplicate record exceptions (409 Conflict)"""
    observe_error(request, 409, type(exc).__name__)
    return JSONResponse(
        status_code=409,
        content={
            "error": "Duplicate Record",
            "message": exc.message,
            "resource": exc.resource,
            "field": exc.field,
        },
    )


@app.exception_handler(RecordNotFoundException)
async def record_not_found_exception_handler(request: Request, exc: RecordNotFoundException):
    """Handle record not found exceptions (404 Not Found)"""
    observe_error(request, 404, type(exc).__name__)
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": exc.message,
            "resource": exc.resource,
            "identifier": str(exc.identifier),
        },
    )


@app.exception_handler(ForeignKeyViolationException)
async def foreign_key_violation_exception_handler(request: Request, exc: ForeignKeyViolationException):
    """Handle foreign key violation exceptions (400 Bad Request)"""
    observe_error(request, 400, type(exc).__name__)
    return JSONResponse(
        status_code=400,
        content={
            "error": "Invalid Reference",
            "message": exc.message,
            "resource": exc.resource,
            "foreign_key": exc.foreign_key,
        },
    )


@app.exception_handler(InvalidDataException)
async def invalid_data_exception_handler(request: Request, exc: InvalidDataException):
    """Handle invalid data exceptions (422 Unprocessable Entity)"""
    observe_error(request, 422, type(exc).__name__)
    return JSONResponse(
        status_code=422,
        content={
            "error": "Invalid Data",
            "message": exc.message,
            "resource": exc.resource,
            "details": exc.details,
        },
    )


@app.exception_handler(DatabaseConnectionException)
async def database_connection_exception_handler(request: Request, exc: DatabaseConnectionException):
    """Handle database connection exceptions (503 Service Unavailable)"""
    observe_error(request, 503, type(exc).__name__)
    return JSONResponse(
        status_code=503,
        content={
            "error": "Service Unavailable",
            "message": "Database connection error. Please try again later.",
            "details": exc.details if settings.DEBUG else None,
        },
    )


@app.exception_handler(DatabaseOperationException)
async def database_operation_exception_handler(request: Request, exc: DatabaseOperationException):
    """Handle database operation exceptions (500 Internal Server Error)"""
    observe_error(request, 500, type(exc).__name__)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Database Operation Failed",
            "message": f"Failed to {exc.operation} {exc.resource}",
            "details": exc.details if settings.DEBUG else None,
        },
    )


@app.exception_handler(RepositoryException)
async def repository_exception_handler(request: Request, exc: RepositoryException):
    """Handle generic repository exceptions (500 Internal Server Error)"""
    observe_error(request, 500, type(exc).__name__)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": exc.message,
            "details": exc.details if settings.DEBUG else None,
        },
    )


# Include API routers
app.include_router(auth_router, prefix=settings.API_PREFIX, tags=["authentication"])
app.include_router(schools_router, prefix=settings.API_PREFIX, tags=["schools"])
app.include_router(students_router, prefix=settings.API_PREFIX, tags=["students"])
app.include_router(invoices_router, prefix=settings.API_PREFIX, tags=["invoices"])
app.include_router(payments_router, prefix=settings.API_PREFIX, tags=["payments"])


@app.get("/", tags=["root"])
async def root():
    """
    Root endpoint

    Returns welcome message and links to documentation.
    """
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "redoc": "/redoc",
        "api_prefix": settings.API_PREFIX,
    }


@app.get("/health", tags=["health"])
async def health_check():
    """
    Health check endpoint

    Returns the health status of the application.
    Used by monitoring systems and load balancers.
    """
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@app.get("/metrics", tags=["observability"])
async def metrics():
    """Prometheus scrape endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
