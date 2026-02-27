"""Account status schemas (Pydantic models)"""
from pydantic import BaseModel, ConfigDict
from typing import List
from datetime import date
from decimal import Decimal
from app.db.models import InvoiceStatus


class InvoiceDetail(BaseModel):
    """Invoice detail for account status"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    invoice_number: str
    amount: Decimal
    paid_amount: Decimal
    balance: Decimal
    due_date: date
    status: InvoiceStatus


class StudentAccountStatus(BaseModel):
    """Student account status summary"""
    student_id: int
    student_name: str
    total_invoiced: Decimal
    total_paid: Decimal
    total_pending: Decimal
    invoices: List[InvoiceDetail]


class SchoolAccountStatus(BaseModel):
    """School account status summary"""
    school_id: int
    school_name: str
    total_students: int
    active_students: int
    total_invoiced: Decimal
    total_paid: Decimal
    total_pending: Decimal
    invoices: List[InvoiceDetail]


class SchoolStudentAccountStatus(BaseModel):
    """Account status for a specific student in a specific school"""
    school_id: int
    school_name: str
    student_id: int
    student_name: str
    total_invoiced: Decimal
    total_paid: Decimal
    total_pending: Decimal
    invoices: List[InvoiceDetail]
