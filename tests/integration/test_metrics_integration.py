"""
Integration tests for Prometheus metrics exposure and counter behavior.
"""

import re

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


def _parse_metric_samples(
    metrics_text: str, metric_name: str
) -> list[tuple[dict[str, str], float]]:
    """Parse Prometheus exposition lines for one metric."""
    samples: list[tuple[dict[str, str], float]] = []
    prefix = f"{metric_name}{{"

    for line in metrics_text.splitlines():
        if not line.startswith(prefix):
            continue

        end = line.rfind("}")
        labels_raw = line[len(prefix) : end]
        value_raw = line[end + 1 :].strip().split(" ", 1)[0]

        labels = {
            k: v
            for k, v in re.findall(r'([a-zA-Z_][a-zA-Z0-9_]*)="([^"]*)"', labels_raw)
        }
        samples.append((labels, float(value_raw)))

    return samples


def _metric_value(
    metrics_text: str, metric_name: str, expected_labels: dict[str, str]
) -> float:
    """Get exact-label metric value; return 0 when missing."""
    for labels, value in _parse_metric_samples(metrics_text, metric_name):
        if labels == expected_labels:
            return value
    return 0.0


@pytest.mark.asyncio
async def test_success_request_increments_attempt_and_success_metrics():
    """A successful request should increment attempt and success counters."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        before = (await client.get("/metrics")).text

        response = await client.get("/health")
        assert response.status_code == 200

        after = (await client.get("/metrics")).text

    attempts_before = _metric_value(
        before,
        "mattilda_http_operation_attempt_total",
        {"method": "GET", "path": "/health"},
    )
    attempts_after = _metric_value(
        after,
        "mattilda_http_operation_attempt_total",
        {"method": "GET", "path": "/health"},
    )
    assert attempts_after - attempts_before == 1.0

    success_before = _metric_value(
        before,
        "mattilda_http_operation_success_total",
        {"method": "GET", "path": "/health", "status": "200"},
    )
    success_after = _metric_value(
        after,
        "mattilda_http_operation_success_total",
        {"method": "GET", "path": "/health", "status": "200"},
    )
    assert success_after - success_before == 1.0


@pytest.mark.asyncio
async def test_failed_request_increments_attempt_and_error_metrics(
    authenticated_client,
):
    """A controlled 4xx request should increment attempt and error counters."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        before = (await client.get("/metrics")).text

        # Try to create a student with invalid FK - should return 400
        response = await authenticated_client.post(
            "/api/students",
            json={
                "school_id": 999999,  # Invalid FK on purpose
                "first_name": "Load",
                "last_name": "Error",
            },
        )
        assert response.status_code == 400

        after = (await client.get("/metrics")).text

    attempts_before = _metric_value(
        before,
        "mattilda_http_operation_attempt_total",
        {"method": "POST", "path": "/api/students"},
    )
    attempts_after = _metric_value(
        after,
        "mattilda_http_operation_attempt_total",
        {"method": "POST", "path": "/api/students"},
    )
    assert attempts_after - attempts_before == 1.0

    error_before = _metric_value(
        before,
        "mattilda_http_operation_error_total",
        {"method": "POST", "path": "/api/students", "status": "400"},
    )
    error_after = _metric_value(
        after,
        "mattilda_http_operation_error_total",
        {"method": "POST", "path": "/api/students", "status": "400"},
    )
    assert error_after - error_before == 1.0
