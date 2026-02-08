"""
Additional data quality rules for enhanced profiling.

Provides pattern detection, validation, and quality scoring beyond basic type inference.
"""

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from ..utils.security import safe_pattern_match


# ============================================================================
# Pattern Detection Rules
# ============================================================================

# Pre-compiled patterns for performance (ReDoS-safe)
EMAIL_PATTERN = re.compile(r'^[\w.+-]+@[\w.-]+\.[\w]{2,}$')
PHONE_US_PATTERN = re.compile(r'^\+?1?[\d\s\-().]{10,}$')
SSN_PATTERN = re.compile(r'^\d{3}-?\d{2}-?\d{4}$')
ZIP_5_PATTERN = re.compile(r'^\d{5}$')
ZIP_PLUS4_PATTERN = re.compile(r'^\d{5}-\d{4}$')
US_STATE_CODES = {
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
    'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
    'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
    'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
    'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY',
    'DC', 'PR', 'VI', 'GU', 'AS', 'MP'
}
NPI_PATTERN = re.compile(r'^\d{10}$')
ICD10_DX_PATTERN = re.compile(r'^[A-Z]\d{2}(\.\d{1,4})?$')
ICD10_PCS_PATTERN = re.compile(r'^[0-9A-HJ-NP-Z]{7}$')
CPT_PATTERN = re.compile(r'^\d{5}$')


def validate_npi_check_digit(npi: str) -> bool:
    """Validate NPI using Luhn algorithm (with healthcare prefix 80840)."""
    if len(npi) != 10 or not npi.isdigit():
        return False
    # Prepend 80840 prefix for Luhn check
    full = "80840" + npi
    total = 0
    for i, digit in enumerate(reversed(full)):
        d = int(digit)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


@dataclass
class QualityRulesResult:
    """Results from quality rules analysis for a single column."""
    # Pattern detection
    detected_patterns: Dict[str, int] = field(default_factory=dict)  # pattern_name -> match_count

    # Completeness
    completeness_pct: float = 0.0  # (non-null / total) * 100

    # Uniqueness
    uniqueness_pct: float = 0.0  # (distinct / non-null) * 100

    # Whitespace issues
    leading_whitespace_count: int = 0
    trailing_whitespace_count: int = 0

    # Empty string vs null
    empty_string_count: int = 0
    null_count: int = 0

    # Entropy (Shannon)
    entropy: Optional[float] = None

    # Outliers (for numeric columns)
    outlier_count: int = 0
    outlier_pct: float = 0.0

    # PHI flags
    phi_risk_flags: List[str] = field(default_factory=list)


class QualityRulesAnalyzer:
    """
    Analyzes column values for additional quality rules.

    Run after type-specific profiling to add quality metadata.
    """

    def __init__(self):
        """Initialize analyzer."""
        self.total_count = 0
        self.null_count = 0
        self.empty_string_count = 0
        self.leading_ws_count = 0
        self.trailing_ws_count = 0
        self.value_counts: Counter = Counter()
        self.numeric_values: List[float] = []

        # Pattern match counts
        self.email_count = 0
        self.phone_count = 0
        self.ssn_count = 0
        self.zip5_count = 0
        self.zip_plus4_count = 0
        self.state_code_count = 0
        self.npi_count = 0
        self.npi_valid_count = 0
        self.icd10_dx_count = 0
        self.icd10_pcs_count = 0
        self.cpt_count = 0

    def update(self, value: str, col_type: str = "unknown") -> None:
        """
        Process a single value.

        Args:
            value: Raw value from CSV
            col_type: Inferred column type
        """
        self.total_count += 1

        # Null check (None or empty after strip)
        if value is None:
            self.null_count += 1
            return

        if value == '':  # Empty string (before stripping)
            self.empty_string_count += 1
            return

        # Whitespace checks (before stripping)
        if value != value.lstrip():
            self.leading_ws_count += 1
        if value != value.rstrip():
            self.trailing_ws_count += 1

        stripped = value.strip()
        if stripped == '':
            self.null_count += 1
            return

        # Track value frequency for entropy
        self.value_counts[stripped] += 1

        # Try to parse as numeric for outlier detection
        if col_type in ("numeric", "money"):
            try:
                self.numeric_values.append(float(stripped))
            except (ValueError, TypeError):
                pass

        # Pattern detection with ReDoS protection
        if safe_pattern_match(EMAIL_PATTERN, stripped):
            self.email_count += 1
        if safe_pattern_match(PHONE_US_PATTERN, stripped):
            self.phone_count += 1
        if safe_pattern_match(SSN_PATTERN, stripped):
            self.ssn_count += 1
        if safe_pattern_match(ZIP_5_PATTERN, stripped):
            self.zip5_count += 1
        if safe_pattern_match(ZIP_PLUS4_PATTERN, stripped):
            self.zip_plus4_count += 1
        if stripped.upper() in US_STATE_CODES and len(stripped) == 2:
            self.state_code_count += 1
        if safe_pattern_match(NPI_PATTERN, stripped):
            self.npi_count += 1
            if validate_npi_check_digit(stripped):
                self.npi_valid_count += 1
        if safe_pattern_match(ICD10_DX_PATTERN, stripped.upper()):
            self.icd10_dx_count += 1
        if safe_pattern_match(ICD10_PCS_PATTERN, stripped.upper()):
            self.icd10_pcs_count += 1
        if safe_pattern_match(CPT_PATTERN, stripped):
            self.cpt_count += 1

    def finalize(self) -> QualityRulesResult:
        """Compute final quality rules results."""
        result = QualityRulesResult()

        non_null = self.total_count - self.null_count - self.empty_string_count

        # Completeness
        result.completeness_pct = (non_null / self.total_count * 100.0) if self.total_count > 0 else 0.0

        # Uniqueness
        distinct_count = len(self.value_counts)
        result.uniqueness_pct = (distinct_count / non_null * 100.0) if non_null > 0 else 0.0

        # Whitespace
        result.leading_whitespace_count = self.leading_ws_count
        result.trailing_whitespace_count = self.trailing_ws_count
        result.empty_string_count = self.empty_string_count
        result.null_count = self.null_count

        # Pattern detection - only report if significant (>10% of non-null values)
        threshold = max(1, non_null * 0.10)

        patterns = {}
        if self.email_count >= threshold:
            patterns["email"] = self.email_count
        if self.phone_count >= threshold:
            patterns["phone_us"] = self.phone_count
        if self.ssn_count >= threshold:
            patterns["ssn_tin"] = self.ssn_count
        if self.zip5_count >= threshold:
            patterns["zip_code_5"] = self.zip5_count
        if self.zip_plus4_count >= threshold:
            patterns["zip_plus_4"] = self.zip_plus4_count
        if self.state_code_count >= threshold:
            patterns["us_state_code"] = self.state_code_count
        if self.npi_count >= threshold:
            patterns["npi"] = self.npi_count
            patterns["npi_valid_checksum"] = self.npi_valid_count
        if self.icd10_dx_count >= threshold:
            patterns["icd10_diagnosis"] = self.icd10_dx_count
        if self.icd10_pcs_count >= threshold:
            patterns["icd10_procedure"] = self.icd10_pcs_count
        if self.cpt_count >= threshold:
            patterns["cpt_code"] = self.cpt_count

        result.detected_patterns = patterns

        # Entropy (Shannon)
        if non_null > 0:
            entropy = 0.0
            for count in self.value_counts.values():
                p = count / non_null
                if p > 0:
                    entropy -= p * math.log2(p)
            result.entropy = round(entropy, 4)

        # Outlier detection (IQR method for numeric)
        if len(self.numeric_values) >= 4:
            sorted_vals = sorted(self.numeric_values)
            n = len(sorted_vals)
            q1_idx = n // 4
            q3_idx = (3 * n) // 4
            q1 = sorted_vals[q1_idx]
            q3 = sorted_vals[q3_idx]
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            outliers = sum(1 for v in self.numeric_values if v < lower_bound or v > upper_bound)
            result.outlier_count = outliers
            result.outlier_pct = (outliers / len(self.numeric_values) * 100.0) if self.numeric_values else 0.0

        # PHI risk flags
        phi_flags = []
        if self.ssn_count > 0:
            phi_flags.append("potential_ssn")
        if self.npi_count > 0:
            phi_flags.append("potential_npi")
        if self.email_count > 0:
            phi_flags.append("potential_email_pii")
        if self.phone_count > 0:
            phi_flags.append("potential_phone_pii")
        result.phi_risk_flags = phi_flags

        return result
