"""Prometheus metrics for API observability."""

from time import perf_counter
from typing import Optional

from fastapi import Request
from prometheus_client import Counter, Histogram

HTTP_REQUESTS_TOTAL = Counter(
    "mattilda_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "mattilda_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path", "status"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)

HTTP_ERRORS_TOTAL = Counter(
    "mattilda_http_errors_total",
    "Total HTTP error responses by exception type",
    ["exception_type", "path", "status"],
)

HTTP_OPERATION_ATTEMPTS_TOTAL = Counter(
    "mattilda_http_operation_attempt_total",
    "Total HTTP operation attempts",
    ["method", "path"],
)

HTTP_OPERATION_SUCCESS_TOTAL = Counter(
    "mattilda_http_operation_success_total",
    "Total HTTP operation successes",
    ["method", "path", "status"],
)

HTTP_OPERATION_ERROR_TOTAL = Counter(
    "mattilda_http_operation_error_total",
    "Total HTTP operation errors",
    ["method", "path", "status"],
)


def request_timer() -> float:
    """Start a request timer."""
    return perf_counter()


def request_path_label(request: Request) -> str:
    """Return stable route template label when available."""
    route = request.scope.get("route")
    route_path = getattr(route, "path", None)
    if route_path:
        return route_path
    return request.url.path


def observe_request(request: Request, status_code: int, started_at: float) -> None:
    """Record request count and latency."""
    path = request_path_label(request)
    method = request.method
    status = str(status_code)
    duration = perf_counter() - started_at

    HTTP_REQUESTS_TOTAL.labels(method=method, path=path, status=status).inc()
    HTTP_REQUEST_DURATION_SECONDS.labels(
        method=method, path=path, status=status
    ).observe(duration)


def observe_error(
    request: Request, status_code: int, exception_type: Optional[str]
) -> None:
    """Record error counter by exception type."""
    path = request_path_label(request)
    HTTP_ERRORS_TOTAL.labels(
        exception_type=exception_type or "unknown",
        path=path,
        status=str(status_code),
    ).inc()


def observe_attempt(request: Request) -> None:
    """Record operation attempt."""
    HTTP_OPERATION_ATTEMPTS_TOTAL.labels(
        method=request.method,
        path=request.url.path,
    ).inc()


def observe_success(request: Request, status_code: int) -> None:
    """Record operation success (HTTP < 400)."""
    HTTP_OPERATION_SUCCESS_TOTAL.labels(
        method=request.method,
        path=request_path_label(request),
        status=str(status_code),
    ).inc()


def observe_failure(request: Request, status_code: int) -> None:
    """Record operation error (HTTP >= 400 or unhandled exception)."""
    HTTP_OPERATION_ERROR_TOTAL.labels(
        method=request.method,
        path=request_path_label(request),
        status=str(status_code),
    ).inc()
