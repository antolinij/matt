"""
Interactive database shell with async support
Run with:
  - Docker: docker-compose exec web python scripts/db_shell.py
  - Local: python scripts/db_shell.py
  - Makefile: make db-shell
"""

import asyncio
from app.core.database import AsyncSessionLocal
from app.db.models import School, Student, Invoice, Payment, StudentStatus, InvoiceStatus, PaymentMethod
from app.repositories import SchoolRepository, StudentRepository, InvoiceRepository, PaymentRepository

print("=" * 60)
print("Mattilda Database Shell (Async)")
print("=" * 60)
print("\nAvailable objects:")
print("  db                - Async database session")
print("  School            - School model")
print("  Student           - Student model")
print("  Invoice           - Invoice model")
print("  Payment           - Payment model")
print("  StudentStatus     - Student status enum")
print("  InvoiceStatus     - Invoice status enum")
print("  PaymentMethod     - Payment method enum")
print("  SchoolRepository  - School repository")
print("  StudentRepository - Student repository")
print("  InvoiceRepository - Invoice repository")
print("  PaymentRepository - Payment repository")
print("\nExample queries (use await for async operations):")
print("  school_repo = SchoolRepository(db)")
print("  schools = await school_repo.get_all()")
print("  school = await school_repo.get_by_id(1)")
print("  for s in schools: print(s.name)")
print("=" * 60)
print()

async def main():
    """Main async function to start the interactive shell"""
    async with AsyncSessionLocal() as db:
        # Import IPython for better interactive experience if available
        try:
            from IPython import embed
            # Create repository instances for convenience
            school_repo = SchoolRepository(db)
            student_repo = StudentRepository(db)
            invoice_repo = InvoiceRepository(db)
            payment_repo = PaymentRepository(db)

            # Make all these available in the shell
            await embed()
        except ImportError:
            print("\nNote: Install IPython for a better interactive experience:")
            print("  pip install ipython")
            print("\nStarting basic Python shell...")
            import code
            code.interact(local=locals())

if __name__ == "__main__":
    asyncio.run(main())
