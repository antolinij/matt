# Manual Test Scripts

This directory contains manual test scripts that are not part of the automated test suite.

**Note**: Database utility scripts (seed_data.py, db_shell.py) have been moved to the `scripts/` directory. See `scripts/README.md` for more information.

## Scripts

### test_cache.py
**Status**: ✅ Working

**Purpose**: Manual test script for Redis cache functionality.

**Usage**: Ensure Redis is running, then:
```bash
python tests/manual/test_cache.py
```

Tests cache operations including:
- Setting and getting cached values
- Cache expiration
- Cache invalidation

### test_nested_endpoint.py
**Status**: ⚠️ One-time use script (contains hardcoded IDs)

**Purpose**: Manual test script for the student account status nested endpoint.

**Note**: This functionality is now covered by automated tests in `tests/api/test_students_account_status.py`. This script is kept for reference only.

**Usage**: Contains hardcoded school and student IDs. Update IDs before running:
```bash
python tests/manual/test_nested_endpoint.py
```

## When to Use Manual Tests

- **Development**: Quick manual verification during feature development
- **Debugging**: Isolate specific functionality for troubleshooting
- **Data Seeding**: Populate database with test data for manual exploration

## Automated Tests

For automated testing, use the main test suite:
```bash
make test        # Run all tests
make test-cov    # Run tests with coverage report
```
