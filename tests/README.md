# Test Suite Documentation

## Current Structure

```
tests/
├── api/                         # API-level tests via FastAPI + httpx
│   ├── test_account_status.py
│   ├── test_auth.py
│   ├── test_global_exception_handlers.py
│   └── test_schools.py
├── domain/                      # Domain/event-driven behavior tests
│   ├── test_event_driven_accounting.py
│   └── test_exceptions.py
├── repositories/                # Repository/database exception tests
│   └── test_repository_exceptions.py
├── integration/                 # Cross-cutting integration tests
│   └── test_metrics_integration.py
├── conftest.py                  # Shared fixtures and cleanup
└── __init__.py
```

## Running Tests

Run all tests:

```bash
pytest
```

Run a folder:

```bash
pytest tests/api
pytest tests/domain
pytest tests/repositories
pytest tests/integration
```

Run one file:

```bash
pytest tests/integration/test_metrics_integration.py
```

Run by marker:

```bash
pytest -m integration
pytest -m asyncio
```

## Notes

- `pytest.ini` uses `testpaths = tests`, so all subfolders under `tests/` are discovered automatically.
- Integration tests rely on local test databases and shared cleanup in `tests/conftest.py`.
