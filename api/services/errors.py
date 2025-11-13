"""
Error aggregation and management for data profiling.

This module provides error code definitions and the ErrorAggregator class
for collecting and rolling up errors during data profiling operations.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


class ErrorCode:
    """Standard error codes for data profiling operations."""

    # Catastrophic errors (stop processing immediately)
    E_UTF8_INVALID = "E_UTF8_INVALID"
    E_HEADER_MISSING = "E_HEADER_MISSING"
    E_JAGGED_ROW = "E_JAGGED_ROW"

    # Non-catastrophic errors (continue processing)
    E_QUOTE_RULE = "E_QUOTE_RULE"
    E_UNQUOTED_DELIM = "E_UNQUOTED_DELIM"
    E_NUMERIC_FORMAT = "E_NUMERIC_FORMAT"
    E_MONEY_FORMAT = "E_MONEY_FORMAT"
    E_DATE_MIXED_FORMAT = "E_DATE_MIXED_FORMAT"

    # Warnings (informational only)
    W_DATE_RANGE = "W_DATE_RANGE"
    W_LINE_ENDING = "W_LINE_ENDING"


# Error message templates
ERROR_MESSAGES: Dict[str, str] = {
    # Catastrophic errors
    ErrorCode.E_UTF8_INVALID: "Invalid UTF-8 byte sequence detected",
    ErrorCode.E_HEADER_MISSING: "Header row not found or file is empty",
    ErrorCode.E_JAGGED_ROW: "Inconsistent column count detected",

    # Non-catastrophic errors
    ErrorCode.E_QUOTE_RULE: "Quote escaping violation detected",
    ErrorCode.E_UNQUOTED_DELIM: "Unquoted embedded delimiter detected",
    ErrorCode.E_NUMERIC_FORMAT: "Invalid numeric format detected",
    ErrorCode.E_MONEY_FORMAT: "Invalid money format detected",
    ErrorCode.E_DATE_MIXED_FORMAT: "Inconsistent date formats in column",

    # Warnings
    ErrorCode.W_DATE_RANGE: "Date outside expected range",
    ErrorCode.W_LINE_ENDING: "Mixed line endings detected",
}

# Catastrophic error codes (processing stops)
CATASTROPHIC_ERRORS = {
    ErrorCode.E_UTF8_INVALID,
    ErrorCode.E_HEADER_MISSING,
    ErrorCode.E_JAGGED_ROW,
}


@dataclass
class ErrorRecord:
    """Single error occurrence with context."""

    code: str
    message: str
    is_catastrophic: bool
    line_number: Optional[int] = None
    column_name: Optional[str] = None
    byte_offset: Optional[int] = None
    details: Optional[Dict] = None


@dataclass
class ErrorSummary:
    """Aggregated error summary for a specific error code."""

    code: str
    message: str
    count: int
    is_catastrophic: bool
    percentage: float = 0.0
    first_occurrence: Optional[ErrorRecord] = None


class ErrorAggregator:
    """
    Aggregates errors during data profiling operations.

    Errors are grouped by code and counted. Catastrophic errors cause
    immediate processing termination, while non-catastrophic errors
    are accumulated and reported.
    """

    def __init__(self):
        """Initialize error aggregator."""
        self._error_counts: Dict[str, int] = {}
        self._first_occurrences: Dict[str, ErrorRecord] = {}
        self._all_errors: List[ErrorRecord] = []
        self._total_rows: int = 0

    def record(
        self,
        code: str,
        message: Optional[str] = None,
        line_number: Optional[int] = None,
        column_name: Optional[str] = None,
        byte_offset: Optional[int] = None,
        details: Optional[Dict] = None,
    ) -> None:
        """
        Record an error occurrence.

        Args:
            code: Error code (e.g., ErrorCode.E_NUMERIC_FORMAT)
            message: Optional custom message (uses default if not provided)
            line_number: Optional line number where error occurred
            column_name: Optional column name where error occurred
            byte_offset: Optional byte offset for encoding errors
            details: Optional additional context
        """
        # Use default message if not provided
        if message is None:
            message = ERROR_MESSAGES.get(code, "Unknown error")

        # Determine if catastrophic
        is_catastrophic = code in CATASTROPHIC_ERRORS

        # Create error record
        error = ErrorRecord(
            code=code,
            message=message,
            is_catastrophic=is_catastrophic,
            line_number=line_number,
            column_name=column_name,
            byte_offset=byte_offset,
            details=details,
        )

        # Update counts
        self._error_counts[code] = self._error_counts.get(code, 0) + 1

        # Store first occurrence for each error code
        if code not in self._first_occurrences:
            self._first_occurrences[code] = error

        # Store all errors (for debugging/logging)
        self._all_errors.append(error)

    def set_total_rows(self, count: int) -> None:
        """
        Set total row count for percentage calculations.

        Args:
            count: Total number of rows processed
        """
        self._total_rows = count

    def get_error_count(self, code: str) -> int:
        """
        Get count of errors for a specific error code.

        Args:
            code: Error code to query

        Returns:
            Number of occurrences of this error code
        """
        return self._error_counts.get(code, 0)

    def get_error_rollup(self) -> Dict[str, int]:
        """
        Get error counts grouped by code.

        Returns:
            Dictionary mapping error code to count
        """
        return self._error_counts.copy()

    def get_errors(self) -> List[ErrorRecord]:
        """
        Get all error records.

        Returns:
            List of all recorded errors
        """
        return self._all_errors.copy()

    def get_summaries(self) -> List[ErrorSummary]:
        """
        Get aggregated error summaries.

        Returns:
            List of ErrorSummary objects, one per error code
        """
        summaries = []
        for code, count in self._error_counts.items():
            first_occurrence = self._first_occurrences.get(code)
            message = ERROR_MESSAGES.get(code, "Unknown error")
            is_catastrophic = code in CATASTROPHIC_ERRORS

            # Calculate percentage
            percentage = 0.0
            if self._total_rows > 0:
                percentage = count / self._total_rows

            summaries.append(
                ErrorSummary(
                    code=code,
                    message=message,
                    count=count,
                    is_catastrophic=is_catastrophic,
                    percentage=percentage,
                    first_occurrence=first_occurrence,
                )
            )

        # Sort by count descending
        summaries.sort(key=lambda s: s.count, reverse=True)
        return summaries

    def has_catastrophic_errors(self) -> bool:
        """
        Check if any catastrophic errors have been recorded.

        Returns:
            True if catastrophic errors exist
        """
        return any(code in CATASTROPHIC_ERRORS for code in self._error_counts.keys())

    def has_errors(self) -> bool:
        """
        Check if any errors (catastrophic or not) have been recorded.

        Returns:
            True if any errors exist
        """
        return len(self._error_counts) > 0

    def get_error_count_total(self) -> int:
        """
        Get total count of all errors.

        Returns:
            Sum of all error counts
        """
        return sum(self._error_counts.values())

    def to_dict(self) -> Dict:
        """
        Convert error aggregation to dictionary format.

        Returns:
            Dictionary with error summaries and metadata
        """
        summaries = self.get_summaries()
        return {
            "total_errors": self.get_error_count_total(),
            "has_catastrophic": self.has_catastrophic_errors(),
            "summaries": [
                {
                    "code": s.code,
                    "message": s.message,
                    "count": s.count,
                    "percentage": s.percentage,
                    "is_catastrophic": s.is_catastrophic,
                }
                for s in summaries
            ],
        }

    def clear(self) -> None:
        """Clear all recorded errors."""
        self._error_counts.clear()
        self._first_occurrences.clear()
        self._all_errors.clear()
        self._total_rows = 0
