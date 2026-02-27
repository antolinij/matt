"""
Script to seed the database with sample data
Run with:
  - Docker: docker-compose exec web python scripts/seed_data.py
  - Local: python scripts/seed_data.py
  - Makefile: make seed
"""

import asyncio
from datetime import date, timedelta
from decimal import Decimal
from app.core.database import AsyncSessionLocal
from app.db.models import StudentStatus, InvoiceStatus, PaymentMethod
from app.repositories import SchoolRepository, StudentRepository, InvoiceRepository, PaymentRepository
from app.schemas import SchoolCreate, StudentCreate, InvoiceCreate, PaymentCreate

async def seed_database():
    async with AsyncSessionLocal() as db:
        try:
            print("🌱 Starting database seeding...")

            # Create Schools
            print("\n📚 Creating schools...")
            school_repo = SchoolRepository(db)

            school1 = await school_repo.create(
                name="Colegio San José",
                address="Av. Insurgentes Sur 123, CDMX",
                phone="+52 55 1234 5678",
                email="info@sanjose.edu.mx"
            )
            print(f"   ✓ Created: {school1.name}")

            school2 = await school_repo.create(
                name="Instituto Juárez",
                address="Calle Reforma 456, Guadalajara",
                phone="+52 33 8765 4321",
                email="contacto@juarez.edu.mx"
            )
            print(f"   ✓ Created: {school2.name}")

            # Create Students for School 1
            print("\n👨‍🎓 Creating students...")
            student_repo = StudentRepository(db)

            student1 = await student_repo.create(
                school_id=school1.id,
                first_name="Juan",
                last_name="Pérez García",
                email="juan.perez@example.com",
                enrollment_date=date(2024, 1, 15),
                status=StudentStatus.ACTIVE
            )
            print(f"   ✓ Created: {student1.first_name} {student1.last_name}")

            student2 = await student_repo.create(
                school_id=school1.id,
                first_name="María",
                last_name="González López",
                email="maria.gonzalez@example.com",
                enrollment_date=date(2024, 1, 15),
                status=StudentStatus.ACTIVE
            )
            print(f"   ✓ Created: {student2.first_name} {student2.last_name}")

            # Create Students for School 2
            student3 = await student_repo.create(
                school_id=school2.id,
                first_name="Carlos",
                last_name="Rodríguez Martínez",
                email="carlos.rodriguez@example.com",
                enrollment_date=date(2024, 2, 1),
                status=StudentStatus.ACTIVE
            )
            print(f"   ✓ Created: {student3.first_name} {student3.last_name}")

            # Create Invoices
            print("\n🧾 Creating invoices...")
            invoice_repo = InvoiceRepository(db)
            today = date.today()

            # Student 1 - Multiple invoices
            invoice1 = await invoice_repo.create(
                student_id=student1.id,
                amount=Decimal("5000.00"),
                issue_date=today - timedelta(days=30),
                due_date=today - timedelta(days=15),
                description="Colegiatura Enero 2024",
                status=InvoiceStatus.PENDING
            )
            print(f"   ✓ Created: {invoice1.invoice_number} - ${invoice1.amount}")

            invoice2 = await invoice_repo.create(
                student_id=student1.id,
                amount=Decimal("5000.00"),
                issue_date=today - timedelta(days=15),
                due_date=today + timedelta(days=15),
                description="Colegiatura Febrero 2024",
                status=InvoiceStatus.PENDING
            )
            print(f"   ✓ Created: {invoice2.invoice_number} - ${invoice2.amount}")

            # Student 2 - One invoice
            invoice3 = await invoice_repo.create(
                student_id=student2.id,
                amount=Decimal("6000.00"),
                issue_date=today - timedelta(days=20),
                due_date=today + timedelta(days=10),
                description="Colegiatura + Materiales Febrero 2024",
                status=InvoiceStatus.PENDING
            )
            print(f"   ✓ Created: {invoice3.invoice_number} - ${invoice3.amount}")

            # Student 3 - One invoice
            invoice4 = await invoice_repo.create(
                student_id=student3.id,
                amount=Decimal("4500.00"),
                issue_date=today - timedelta(days=10),
                due_date=today + timedelta(days=20),
                description="Colegiatura Febrero 2024",
                status=InvoiceStatus.PENDING
            )
            print(f"   ✓ Created: {invoice4.invoice_number} - ${invoice4.amount}")

            # Create Payments
            print("\n💰 Creating payments...")
            payment_repo = PaymentRepository(db)

            # Full payment for invoice 1
            payment1 = await payment_repo.create(
                invoice_id=invoice1.id,
                amount=Decimal("5000.00"),
                payment_date=today - timedelta(days=10),
                payment_method=PaymentMethod.TRANSFER,
                reference="TRF-20240215-001"
            )
            print(f"   ✓ Created: Payment ${payment1.amount} for {invoice1.invoice_number}")

            # Partial payment for invoice 2
            payment2 = await payment_repo.create(
                invoice_id=invoice2.id,
                amount=Decimal("2500.00"),
                payment_date=today - timedelta(days=5),
                payment_method=PaymentMethod.CARD,
                reference="CARD-20240220-002"
            )
            print(f"   ✓ Created: Payment ${payment2.amount} for {invoice2.invoice_number}")

            # Partial payment for invoice 3
            payment3 = await payment_repo.create(
                invoice_id=invoice3.id,
                amount=Decimal("3000.00"),
                payment_date=today - timedelta(days=3),
                payment_method=PaymentMethod.CASH,
                reference=None
            )
            print(f"   ✓ Created: Payment ${payment3.amount} for {invoice3.invoice_number}")

            print("\n✅ Database seeding completed successfully!")

            # Print summary
            print("\n" + "="*50)
            print("📊 SUMMARY")
            print("="*50)
            print(f"Schools created: 2")
            print(f"Students created: 3")
            print(f"Invoices created: 4")
            print(f"Payments created: 3")
            print("\n🚀 You can now test the API at http://localhost:8000/docs")

        except Exception as e:
            print(f"\n❌ Error seeding database: {e}")
            await db.rollback()


if __name__ == "__main__":
    asyncio.run(seed_database())
