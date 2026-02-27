"""
Tests for Custom Exception Classes

Tests that custom exceptions are created correctly with proper attributes.
"""
import pytest

from app.core.exceptions import (
    RepositoryException,
    DuplicateRecordException,
    RecordNotFoundException,
    DatabaseConnectionException,
    ForeignKeyViolationException,
    InvalidDataException,
    DatabaseOperationException,
)


class TestRepositoryException:
    """Tests for base RepositoryException"""

    def test_repository_exception_creation(self):
        """Test creating a basic repository exception"""
        exc = RepositoryException("Test error message")
        assert exc.message == "Test error message"
        assert exc.details is None
        assert str(exc) == "Test error message"

    def test_repository_exception_with_details(self):
        """Test creating repository exception with details"""
        exc = RepositoryException("Test error", "Additional details")
        assert exc.message == "Test error"
        assert exc.details == "Additional details"


class TestDuplicateRecordException:
    """Tests for DuplicateRecordException"""

    def test_duplicate_record_exception_creation(self):
        """Test creating duplicate record exception"""
        exc = DuplicateRecordException("User", "email", "test@example.com")
        assert exc.message == "User with email 'test@example.com' already exists"
        assert exc.resource == "User"
        assert exc.field == "email"
        assert exc.value == "test@example.com"

    def test_duplicate_username_exception(self):
        """Test duplicate username exception"""
        exc = DuplicateRecordException("User", "username", "johndoe")
        assert exc.message == "User with username 'johndoe' already exists"
        assert exc.resource == "User"
        assert exc.field == "username"

    def test_duplicate_school_email_exception(self):
        """Test duplicate school email exception"""
        exc = DuplicateRecordException("School", "email", "school@example.com")
        assert exc.message == "School with email 'school@example.com' already exists"


class TestRecordNotFoundException:
    """Tests for RecordNotFoundException"""

    def test_record_not_found_exception_creation(self):
        """Test creating record not found exception"""
        exc = RecordNotFoundException("User", 123)
        assert exc.message == "User with id '123' not found"
        assert exc.resource == "User"
        assert exc.identifier == 123

    def test_record_not_found_with_string_id(self):
        """Test record not found with string identifier"""
        exc = RecordNotFoundException("School", "abc-123")
        assert exc.message == "School with id 'abc-123' not found"
        assert exc.identifier == "abc-123"


class TestForeignKeyViolationException:
    """Tests for ForeignKeyViolationException"""

    def test_foreign_key_violation_exception_creation(self):
        """Test creating foreign key violation exception"""
        exc = ForeignKeyViolationException("Student", "school_id", 999)
        assert exc.message == "Student references non-existent school_id with id '999'"
        assert exc.resource == "Student"
        assert exc.foreign_key == "school_id"
        assert exc.value == 999

    def test_invoice_foreign_key_violation(self):
        """Test invoice foreign key violation"""
        exc = ForeignKeyViolationException("Invoice", "student_id", 456)
        assert exc.message == "Invoice references non-existent student_id with id '456'"

    def test_payment_foreign_key_violation(self):
        """Test payment foreign key violation"""
        exc = ForeignKeyViolationException("Payment", "invoice_id", 789)
        assert exc.message == "Payment references non-existent invoice_id with id '789'"


class TestInvalidDataException:
    """Tests for InvalidDataException"""

    def test_invalid_data_exception_creation(self):
        """Test creating invalid data exception"""
        exc = InvalidDataException("User", "Email format is invalid")
        assert exc.message == "Invalid data for User: Email format is invalid"
        assert exc.resource == "User"
        assert exc.details == "Email format is invalid"

    def test_payment_exceeds_balance_exception(self):
        """Test payment exceeds balance exception"""
        exc = InvalidDataException(
            "Payment",
            "Payment amount (150.00) exceeds remaining balance (100.00)"
        )
        assert "Payment amount" in exc.message
        assert "exceeds remaining balance" in exc.message


class TestDatabaseConnectionException:
    """Tests for DatabaseConnectionException"""

    def test_database_connection_exception_creation(self):
        """Test creating database connection exception"""
        exc = DatabaseConnectionException("Connection timeout after 30s")
        assert exc.message == "Database connection error occurred"
        assert exc.details == "Connection timeout after 30s"

    def test_database_connection_exception_no_details(self):
        """Test database connection exception without details"""
        exc = DatabaseConnectionException()
        assert exc.message == "Database connection error occurred"
        assert exc.details is None


class TestDatabaseOperationException:
    """Tests for DatabaseOperationException"""

    def test_database_operation_exception_creation(self):
        """Test creating database operation exception"""
        exc = DatabaseOperationException("create", "User", "Unique constraint violation")
        assert exc.message == "Failed to create User"
        assert exc.operation == "create"
        assert exc.resource == "User"
        assert exc.details == "Unique constraint violation"

    def test_database_operation_exception_no_details(self):
        """Test database operation exception without details"""
        exc = DatabaseOperationException("update", "School")
        assert exc.message == "Failed to update School"
        assert exc.details is None

    def test_various_operations(self):
        """Test different operation types"""
        operations = ["create", "update", "delete", "get", "get_all"]
        resources = ["User", "School", "Student", "Invoice", "Payment"]

        for operation in operations:
            for resource in resources:
                exc = DatabaseOperationException(operation, resource)
                assert exc.message == f"Failed to {operation} {resource}"
                assert exc.operation == operation
                assert exc.resource == resource


class TestExceptionInheritance:
    """Tests for exception inheritance hierarchy"""

    def test_all_exceptions_inherit_from_repository_exception(self):
        """Test that all custom exceptions inherit from RepositoryException"""
        assert issubclass(DuplicateRecordException, RepositoryException)
        assert issubclass(RecordNotFoundException, RepositoryException)
        assert issubclass(DatabaseConnectionException, RepositoryException)
        assert issubclass(ForeignKeyViolationException, RepositoryException)
        assert issubclass(InvalidDataException, RepositoryException)
        assert issubclass(DatabaseOperationException, RepositoryException)

    def test_all_exceptions_inherit_from_base_exception(self):
        """Test that all exceptions inherit from base Exception"""
        assert issubclass(RepositoryException, Exception)
        assert issubclass(DuplicateRecordException, Exception)
        assert issubclass(RecordNotFoundException, Exception)


class TestExceptionCatching:
    """Tests for exception catching behavior"""

    def test_catch_specific_exception(self):
        """Test catching specific exception type"""
        with pytest.raises(DuplicateRecordException) as exc_info:
            raise DuplicateRecordException("User", "email", "test@example.com")

        assert exc_info.value.resource == "User"
        assert exc_info.value.field == "email"

    def test_catch_as_repository_exception(self):
        """Test catching as base RepositoryException"""
        with pytest.raises(RepositoryException):
            raise DuplicateRecordException("User", "email", "test@example.com")

    def test_catch_multiple_exception_types(self):
        """Test catching multiple exception types"""
        exceptions = [
            DuplicateRecordException("User", "email", "test@example.com"),
            RecordNotFoundException("User", 123),
            ForeignKeyViolationException("Student", "school_id", 999),
            InvalidDataException("Payment", "Invalid amount"),
            DatabaseConnectionException("Connection lost"),
            DatabaseOperationException("create", "User", "Error details"),
        ]

        for exc in exceptions:
            with pytest.raises(RepositoryException):
                raise exc
