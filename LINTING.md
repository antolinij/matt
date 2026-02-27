# Code Quality & Linting Guide

Complete guide for code quality tools, linters, and formatters in the Mattilda project.

## Quick Start

```bash
# Install all development dependencies (Python)
make install-dev

# Install frontend dependencies
make webapp-install

# Install git hooks (runs linters automatically on commit)
make pre-commit-install

# Run all checks (backend + frontend)
make check-all
```

## Table of Contents

1. [Python Tools](#python-tools)
2. [Frontend Tools](#frontend-tools)
3. [Pre-commit Hooks](#pre-commit-hooks)
4. [Configuration Files](#configuration-files)
5. [Common Workflows](#common-workflows)
6. [CI/CD Integration](#cicd-integration)

---

## Python Tools

### Black (Code Formatter)

**What it does**: Automatically formats Python code to a consistent style.

**Configuration**: `pyproject.toml`

**Usage**:
```bash
# Format all Python code
make format

# Check formatting without changing files
make format-check

# Format specific files
black app/main.py
```

**Settings**:
- Line length: 100 characters
- Target Python version: 3.11
- Excludes: alembic migrations

### isort (Import Sorter)

**What it does**: Sorts and organizes Python imports.

**Configuration**: `pyproject.toml`

**Usage**:
```bash
# Already included in 'make format'
isort app tests scripts

# Check import sorting
isort --check-only app tests scripts
```

**Settings**:
- Compatible with Black
- Line length: 100
- Known first-party: `app`

### Flake8 (Linter)

**What it does**: Checks code for style violations and potential bugs.

**Configuration**: `setup.cfg`

**Usage**:
```bash
# Lint Python code
make lint

# Lint specific files
flake8 app/main.py
```

**Plugins installed**:
- `flake8-docstrings`: Check docstring presence and style
- `flake8-bugbear`: Find likely bugs and design problems
- `flake8-comprehensions`: Better list/dict/set comprehensions
- `flake8-simplify`: Suggest code simplifications

**Settings**:
- Max line length: 100
- Docstring convention: Google style
- Max complexity: 10

### mypy (Type Checker)

**What it does**: Static type checking for Python code.

**Configuration**: `pyproject.toml`

**Usage**:
```bash
# Type check Python code
make type-check

# Type check specific files
mypy app/main.py
```

**Settings**:
- Python version: 3.11
- Ignores missing imports
- Tests are excluded from strict checking

### Bandit (Security Scanner)

**What it does**: Finds common security issues in Python code.

**Configuration**: `pyproject.toml`

**Usage**:
```bash
# Run security checks
make security

# Scan specific directories
bandit -r app
```

**Settings**:
- Excludes: tests, alembic
- Skips: B101 (assert), B601 (shell=True in specific contexts)

### Safety (Dependency Checker)

**What it does**: Checks dependencies for known security vulnerabilities.

**Usage**:
```bash
# Check dependencies
make safety-check

# Check with pip
safety check
```

### pytest-cov (Coverage)

**What it does**: Measures test coverage.

**Configuration**: `pyproject.toml`, `pytest.ini`

**Usage**:
```bash
# Run tests with coverage
make test-cov

# Generate HTML report
pytest --cov=app --cov-report=html
```

---

## Frontend Tools

### ESLint (Linter)

**What it does**: Lints JavaScript/React code for errors and style issues.

**Configuration**: `webapp/.eslintrc.json`

**Usage**:
```bash
# Lint frontend code
make webapp-lint

# Auto-fix issues
make webapp-lint-fix

# Using npm
cd webapp && npm run lint
cd webapp && npm run lint:fix
```

**Plugins**:
- `eslint-plugin-react`: React-specific rules
- `eslint-plugin-react-hooks`: Hooks rules
- `eslint-plugin-react-refresh`: Vite/React Refresh rules

**Key Rules**:
- No unused variables (warn)
- No console.log (warn, allows warn/error)
- React Hooks rules (error)
- Prefer const over let (error)
- No var (error)

### Prettier (Code Formatter)

**What it does**: Automatically formats JavaScript/React code.

**Configuration**: `webapp/.prettierrc`

**Usage**:
```bash
# Format frontend code
make webapp-format

# Check formatting
make webapp-format-check

# Using npm
cd webapp && npm run format
cd webapp && npm run format:check
```

**Settings**:
- Print width: 100 characters
- Semi-colons: Yes
- Single quotes: Yes (except JSX)
- Trailing commas: ES5
- Tab width: 2 spaces

### TypeScript (Optional)

**What it does**: Type checking for JavaScript code.

**Configuration**: TypeScript dependencies installed but not enforced yet.

**Usage**:
```bash
cd webapp && npm run type-check
```

---

## Pre-commit Hooks

Pre-commit hooks automatically run linters before each commit, catching issues early.

### Installation

```bash
# Install hooks
make pre-commit-install

# Hooks will now run automatically on 'git commit'
```

### Manual Execution

```bash
# Run on all files
make pre-commit-run

# Run on staged files only
pre-commit run

# Update hooks to latest versions
make pre-commit-update
```

### What Runs on Commit

**Python files**:
1. Trailing whitespace removal
2. End-of-file fixer
3. Black formatting
4. isort import sorting
5. Flake8 linting
6. mypy type checking
7. Bandit security checks

**Frontend files**:
1. Prettier formatting
2. ESLint linting

**All files**:
1. YAML/JSON/TOML validation
2. Large file detection (>1MB)
3. Merge conflict detection
4. Private key detection

### Skipping Hooks

```bash
# Skip all hooks for one commit (NOT RECOMMENDED)
git commit --no-verify -m "message"

# Skip specific hook
SKIP=flake8 git commit -m "message"
```

---

## Configuration Files

### Backend

| File | Purpose |
|------|---------|
| `pyproject.toml` | Black, isort, mypy, pytest, coverage, bandit config |
| `setup.cfg` | Flake8 configuration |
| `pytest.ini` | Pytest configuration |
| `requirements-dev.txt` | Development dependencies |
| `.pre-commit-config.yaml` | Git hooks configuration |

### Frontend

| File | Purpose |
|------|---------|
| `webapp/.eslintrc.json` | ESLint configuration |
| `webapp/.prettierrc` | Prettier configuration |
| `webapp/.prettierignore` | Files to exclude from Prettier |
| `webapp/package.json` | npm scripts and dependencies |

---

## Common Workflows

### Before Committing

```bash
# Format and check everything
make check-all

# Or step by step:
make format           # Format Python code
make lint-all         # Lint, type-check, security
make test             # Run tests
make webapp-check     # Check frontend
```

### Fixing Issues

```bash
# Fix Python formatting
make format

# Fix Python linting issues (manual)
flake8 app  # Review warnings
# ... make changes ...

# Fix frontend issues
make webapp-lint-fix
make webapp-format

# Type checking issues (manual)
make type-check
# ... add type hints ...
```

### CI/CD Pipeline

```bash
# Typical CI pipeline commands:
make install-dev
make format-check      # Fail if not formatted
make lint-all          # Fail on linting errors
make test-cov          # Run tests with coverage
make webapp-install
make webapp-check      # Check frontend
```

### Generating Reports

```bash
# Comprehensive quality report
make quality-report

# This generates:
# - Coverage report in htmlcov/index.html
# - Flake8 report
# - mypy report
# - Bandit security report
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Code Quality

on: [push, pull_request]

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements-dev.txt
      - run: make format-check
      - run: make lint-all
      - run: make test-cov

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - run: make webapp-install
      - run: make webapp-check
```

---

## Makefile Commands Reference

### Backend

| Command | Description |
|---------|-------------|
| `make install-dev` | Install development dependencies |
| `make format` | Format Python code (black + isort) |
| `make format-check` | Check formatting without changes |
| `make lint` | Lint with flake8 |
| `make type-check` | Type check with mypy |
| `make security` | Security check with bandit |
| `make safety-check` | Check dependencies for vulnerabilities |
| `make lint-all` | Run all linting checks |
| `make check` | Run all backend checks |

### Frontend

| Command | Description |
|---------|-------------|
| `make webapp-install` | Install frontend dependencies |
| `make webapp-lint` | Lint with ESLint |
| `make webapp-lint-fix` | Auto-fix ESLint issues |
| `make webapp-format` | Format with Prettier |
| `make webapp-format-check` | Check Prettier formatting |
| `make webapp-check` | Run all frontend checks |

### All

| Command | Description |
|---------|-------------|
| `make check-all` | Run all checks (backend + frontend) |
| `make pre-commit-install` | Install git hooks |
| `make pre-commit-run` | Run pre-commit on all files |
| `make quality-report` | Generate comprehensive report |

---

## IDE Integration

### VS Code

Install these extensions:
- Python (Microsoft)
- Pylance (Microsoft)
- Black Formatter
- Flake8
- ESLint
- Prettier

Add to `.vscode/settings.json`:
```json
{
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.linting.mypyEnabled": true,
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "[javascript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "[javascriptreact]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  }
}
```

### PyCharm

1. Enable Black: Settings → Tools → Black
2. Enable Flake8: Settings → Tools → External Tools
3. Enable mypy: Settings → Tools → External Tools
4. Enable Prettier: Settings → Languages → JavaScript → Prettier

---

## Troubleshooting

### "Command not found" errors

```bash
# Install dev dependencies
make install-dev

# For frontend
make webapp-install
```

### Pre-commit fails

```bash
# Update hooks
make pre-commit-update

# Run manually to see errors
make pre-commit-run
```

### Conflicting formatting

Black and Prettier are configured to be compatible (both use 100 char lines).
If conflicts occur:
1. Run formatters in order: Black → isort → Prettier
2. Check configuration files match this guide

### Type checking errors

```bash
# Add type hints gradually
# Use # type: ignore for third-party libraries
# Check pyproject.toml for mypy settings
```

---

## Best Practices

1. **Run checks before committing**: Use `make check-all`
2. **Install pre-commit hooks**: Catches issues automatically
3. **Fix formatting first**: Run `make format` before investigating lint errors
4. **Don't skip type hints**: They catch bugs early
5. **Review security warnings**: Don't ignore bandit warnings
6. **Keep dependencies updated**: Run `make pre-commit-update` regularly
7. **Use IDE integration**: Get real-time feedback while coding
8. **Document exceptions**: Add comments when ignoring lint rules

---

For more details, see individual tool documentation:
- [Black](https://black.readthedocs.io/)
- [isort](https://pycqa.github.io/isort/)
- [Flake8](https://flake8.pycqa.org/)
- [mypy](https://mypy.readthedocs.io/)
- [Bandit](https://bandit.readthedocs.io/)
- [ESLint](https://eslint.org/)
- [Prettier](https://prettier.io/)
- [pre-commit](https://pre-commit.com/)
