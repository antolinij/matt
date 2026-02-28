"""
Custom exceptions for domain and repository layers.

This module defines custom exceptions that provide:
- Better error handling and debugging
- Separation of technical vs domain errors
- Clearer error messages for API consumers
"""


class RepositoryException(Exception):
    """Base exception for all repository-level errors."""

    def __init__(
        self, message: str = "A repository error occurred", details: str = None
    ):
        self.message = message
        self.details = details
        super().__init__(self.message)


class DuplicateRecordException(RepositoryException):
    """Raised when attempting to create a record that violates uniqueness constraints."""

    def __init__(self, resource: str, field: str, value: str):
        message = f"{resource} with {field} '{value}' already exists"
        super().__init__(message)
        self.resource = resource
        self.field = field
        self.value = value


class RecordNotFoundException(RepositoryException):
    """Raised when a requested record is not found in the database."""

    def __init__(self, resource: str, identifier: any):
        message = f"{resource} with id '{identifier}' not found"
        super().__init__(message)
        self.resource = resource
        self.identifier = identifier


class DatabaseConnectionException(RepositoryException):
    """Raised when database connection or operational errors occur."""

    def __init__(self, details: str = None):
        message = "Database connection error occurred"
        super().__init__(message, details)


class ForeignKeyViolationException(RepositoryException):
    """Raised when attempting to create/update a record with invalid foreign key references."""

    def __init__(self, resource: str, foreign_key: str, value: any):
        message = f"{resource} references non-existent {foreign_key} with id '{value}'"
        super().__init__(message)
        self.resource = resource
        self.foreign_key = foreign_key
        self.value = value


class InvalidDataException(RepositoryException):
    """Raised when data validation fails at the repository level."""

    def __init__(self, resource: str, details: str):
        message = f"Invalid data for {resource}: {details}"
        super().__init__(message, details)
        self.resource = resource


class DatabaseOperationException(RepositoryException):
    """Raised when a database operation fails for reasons other than constraints."""

    def __init__(self, operation: str, resource: str, details: str = None):
        message = f"Failed to {operation} {resource}"
        super().__init__(message, details)
        self.operation = operation
        self.resource = resource
