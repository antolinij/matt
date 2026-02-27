# Scripts Directory

This directory contains utility scripts for development and database management.

## Available Scripts

### seed_data.py
**Purpose**: Seed the database with sample data for development and testing.

**Usage**:
```bash
# Using Makefile (recommended)
make seed

# Using Docker
docker-compose exec web python scripts/seed_data.py

# Local development
python scripts/seed_data.py
```

**What it does**:
- Creates 2 sample schools
- Creates 3 sample students (2 for school 1, 1 for school 2)
- Creates 4 sample invoices with different amounts and dates
- Creates 3 sample payments (full and partial payments)

**Requirements**:
- Database must be running and migrated
- Run `make up` and `make migrate` first

### db_shell.py
**Purpose**: Interactive Python shell with database access for exploring and debugging.

**Usage**:
```bash
# Using Makefile (recommended)
make db-shell

# Using Docker
docker-compose exec web python scripts/db_shell.py

# Local development
python scripts/db_shell.py
```

**What it does**:
- Opens an interactive Python shell
- Provides async database session
- Pre-loads all models, repositories, and enums
- Enables direct database queries and exploration

**Example usage in shell**:
```python
# Get all schools
school_repo = SchoolRepository(db)
schools = await school_repo.get_all()
for s in schools:
    print(s.name, s.total_students)

# Get student with account status
student_repo = StudentRepository(db)
student = await student_repo.get_by_id(1)
status = await student_repo.get_account_status(1)
print(f"Total pending: ${status['total_pending']}")

# Create new invoice
invoice_repo = InvoiceRepository(db)
invoice = await invoice_repo.create(
    student_id=1,
    amount=Decimal("5000.00"),
    issue_date=date.today(),
    due_date=date.today() + timedelta(days=30),
    description="Monthly tuition"
)
```

**Requirements**:
- Database must be running
- Install IPython for better experience: `pip install ipython`

## Development Notes

- All scripts use async/await patterns
- Import paths are relative to project root
- Scripts should be run from project root directory
- Database connection uses `AsyncSessionLocal` from `app.core.database`
