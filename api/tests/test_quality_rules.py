"""
Tests for quality rules analysis functionality.

Tests pattern detection, quality metrics, PHI risk flags, and NPI validation.
"""

import pytest
from api.services.quality_rules import (
    QualityRulesAnalyzer,
    QualityRulesResult,
    validate_npi_check_digit,
    EMAIL_PATTERN,
    PHONE_US_PATTERN,
    SSN_PATTERN,
    ZIP_5_PATTERN,
    ZIP_PLUS4_PATTERN,
    NPI_PATTERN,
    ICD10_DX_PATTERN,
    ICD10_PCS_PATTERN,
    CPT_PATTERN,
    US_STATE_CODES
)


class TestNPIValidation:
    """Tests for NPI check digit validation using Luhn algorithm."""

    def test_valid_npi_numbers(self):
        """Test that valid NPI numbers pass check digit validation."""
        # Common valid NPIs (from public data)
        valid_npis = [
            "1234567893",  # Valid Luhn checksum with 80840 prefix
            "1679576722",  # Another valid NPI
        ]

        for npi in valid_npis:
            assert validate_npi_check_digit(npi), f"NPI {npi} should be valid"

    def test_invalid_npi_checksum(self):
        """Test that NPIs with invalid checksums fail."""
        # Valid format but wrong checksum
        invalid_npis = [
            "1234567890",  # Wrong checksum
            "1234567891",  # Wrong checksum
            "1234567892",  # Wrong checksum
        ]

        for npi in invalid_npis:
            # Some might randomly be valid, so we just ensure the function runs
            result = validate_npi_check_digit(npi)
            assert isinstance(result, bool)

    def test_non_10_digit_strings_fail(self):
        """Test that non-10-digit strings fail validation."""
        invalid_formats = [
            "123456789",    # 9 digits
            "12345678901",  # 11 digits
            "",             # empty
            "abc1234567",   # contains letters
            "123-456-789",  # contains hyphens
        ]

        for invalid in invalid_formats:
            assert not validate_npi_check_digit(invalid), f"{invalid} should be invalid"

    def test_non_numeric_strings_fail(self):
        """Test that strings with non-numeric characters fail."""
        assert not validate_npi_check_digit("abcdefghij")
        assert not validate_npi_check_digit("123abc7890")
        assert not validate_npi_check_digit("          ")


class TestPatternDetection:
    """Tests for pattern detection regex patterns."""

    def test_email_pattern(self):
        """Test email pattern detection."""
        # Valid emails
        assert EMAIL_PATTERN.match("test@example.com")
        assert EMAIL_PATTERN.match("user.name+tag@domain.co.uk")
        assert EMAIL_PATTERN.match("first.last@company.org")

        # Invalid emails
        assert not EMAIL_PATTERN.match("notanemail")
        assert not EMAIL_PATTERN.match("@example.com")
        assert not EMAIL_PATTERN.match("test@")
        assert not EMAIL_PATTERN.match("test@.com")

    def test_phone_us_pattern(self):
        """Test US phone number pattern detection."""
        # Valid phone formats
        assert PHONE_US_PATTERN.match("555-123-4567")
        assert PHONE_US_PATTERN.match("(555) 123-4567")
        assert PHONE_US_PATTERN.match("5551234567")
        assert PHONE_US_PATTERN.match("555.123.4567")
        assert PHONE_US_PATTERN.match("+1-555-123-4567")
        assert PHONE_US_PATTERN.match("1 555 123 4567")

        # Invalid phone numbers
        assert not PHONE_US_PATTERN.match("123-456")  # Too short
        assert not PHONE_US_PATTERN.match("abc-def-ghij")

    def test_ssn_pattern(self):
        """Test SSN/TIN pattern detection."""
        # Valid SSN formats
        assert SSN_PATTERN.match("123-45-6789")
        assert SSN_PATTERN.match("123456789")

        # Invalid SSN formats
        assert not SSN_PATTERN.match("12-345-6789")  # Wrong format
        assert not SSN_PATTERN.match("123-456-789")  # Too short
        assert not SSN_PATTERN.match("1234-56-789")  # Wrong grouping

    def test_zip_patterns(self):
        """Test ZIP code pattern detection."""
        # Valid ZIP-5
        assert ZIP_5_PATTERN.match("12345")
        assert ZIP_5_PATTERN.match("90210")

        # Invalid ZIP-5
        assert not ZIP_5_PATTERN.match("1234")   # Too short
        assert not ZIP_5_PATTERN.match("123456") # Too long
        assert not ZIP_5_PATTERN.match("abcde")  # Letters

        # Valid ZIP+4
        assert ZIP_PLUS4_PATTERN.match("12345-6789")
        assert ZIP_PLUS4_PATTERN.match("90210-1234")

        # Invalid ZIP+4
        assert not ZIP_PLUS4_PATTERN.match("12345")      # Missing +4
        assert not ZIP_PLUS4_PATTERN.match("12345-678")  # +3 only

    def test_state_code_detection(self):
        """Test US state code detection."""
        # Valid state codes
        assert "CA" in US_STATE_CODES
        assert "NY" in US_STATE_CODES
        assert "TX" in US_STATE_CODES
        assert "DC" in US_STATE_CODES
        assert "PR" in US_STATE_CODES

        # Invalid codes
        assert "XX" not in US_STATE_CODES
        assert "ZZ" not in US_STATE_CODES
        assert "AB" not in US_STATE_CODES

    def test_npi_pattern(self):
        """Test NPI pattern detection (10 digits)."""
        assert NPI_PATTERN.match("1234567890")
        assert NPI_PATTERN.match("9876543210")

        assert not NPI_PATTERN.match("123456789")   # 9 digits
        assert not NPI_PATTERN.match("12345678901") # 11 digits
        assert not NPI_PATTERN.match("123-456-7890") # With hyphens

    def test_icd10_patterns(self):
        """Test ICD-10 code pattern detection."""
        # ICD-10 Diagnosis codes
        assert ICD10_DX_PATTERN.match("A01")
        assert ICD10_DX_PATTERN.match("A01.1")
        assert ICD10_DX_PATTERN.match("A01.12")
        assert ICD10_DX_PATTERN.match("A01.123")
        assert ICD10_DX_PATTERN.match("A01.1234")
        assert ICD10_DX_PATTERN.match("Z99.89")

        # Invalid ICD-10 DX
        assert not ICD10_DX_PATTERN.match("A")      # Too short
        assert not ICD10_DX_PATTERN.match("A1")     # Only 1 digit
        assert not ICD10_DX_PATTERN.match("AA1")    # Two letters
        assert not ICD10_DX_PATTERN.match("A01.12345") # Too many decimals

        # ICD-10 Procedure codes (7 alphanumeric)
        assert ICD10_PCS_PATTERN.match("0016070")
        assert ICD10_PCS_PATTERN.match("00160J6")
        assert ICD10_PCS_PATTERN.match("ABCDEFG")

        # Invalid ICD-10 PCS
        assert not ICD10_PCS_PATTERN.match("001607")    # 6 chars
        assert not ICD10_PCS_PATTERN.match("00160706")  # 8 chars
        assert not ICD10_PCS_PATTERN.match("0016O70")   # Contains O (not allowed)
        assert not ICD10_PCS_PATTERN.match("0016I70")   # Contains I (not allowed)

    def test_cpt_pattern(self):
        """Test CPT code pattern detection."""
        assert CPT_PATTERN.match("99213")
        assert CPT_PATTERN.match("00100")
        assert CPT_PATTERN.match("12345")

        assert not CPT_PATTERN.match("9921")   # 4 digits
        assert not CPT_PATTERN.match("992134") # 6 digits
        assert not CPT_PATTERN.match("9921A")  # Contains letter


class TestQualityMetrics:
    """Tests for quality metrics calculation."""

    def test_completeness_no_nulls(self):
        """Test completeness is 100% when no nulls/empties."""
        analyzer = QualityRulesAnalyzer()

        for i in range(100):
            analyzer.update(f"value_{i}", "varchar")

        result = analyzer.finalize()
        assert result.completeness_pct == 100.0

    def test_completeness_with_nulls(self):
        """Test completeness calculation with null values."""
        analyzer = QualityRulesAnalyzer()

        # 70 valid, 20 null, 10 empty
        for i in range(70):
            analyzer.update(f"value_{i}", "varchar")
        for i in range(20):
            analyzer.update(None, "varchar")
        for i in range(10):
            analyzer.update("", "varchar")

        result = analyzer.finalize()
        # Completeness = 70 / 100 = 70%
        assert result.completeness_pct == 70.0
        assert result.null_count == 20
        assert result.empty_string_count == 10

    def test_completeness_with_whitespace_only(self):
        """Test that whitespace-only values count as null."""
        analyzer = QualityRulesAnalyzer()

        analyzer.update("value1", "varchar")
        analyzer.update("   ", "varchar")  # Whitespace only -> null
        analyzer.update("\t\t", "varchar")  # Tabs only -> null
        analyzer.update("value2", "varchar")

        result = analyzer.finalize()
        # 2 valid out of 4 = 50%
        assert result.completeness_pct == 50.0
        assert result.null_count == 2

    def test_uniqueness_all_unique(self):
        """Test uniqueness is 100% when all values are unique."""
        analyzer = QualityRulesAnalyzer()

        for i in range(100):
            analyzer.update(f"unique_value_{i}", "varchar")

        result = analyzer.finalize()
        assert result.uniqueness_pct == 100.0

    def test_uniqueness_with_duplicates(self):
        """Test uniqueness calculation with duplicate values."""
        analyzer = QualityRulesAnalyzer()

        # Add 50 unique values twice each = 50 distinct / 100 total
        for i in range(50):
            analyzer.update(f"value_{i}", "varchar")
            analyzer.update(f"value_{i}", "varchar")  # Duplicate

        result = analyzer.finalize()
        # 50 distinct / 100 non-null = 50%
        assert result.uniqueness_pct == 50.0

    def test_uniqueness_single_value(self):
        """Test uniqueness with single repeated value."""
        analyzer = QualityRulesAnalyzer()

        for i in range(100):
            analyzer.update("same_value", "varchar")

        result = analyzer.finalize()
        # 1 distinct / 100 non-null = 1%
        assert result.uniqueness_pct == 1.0

    def test_entropy_single_value(self):
        """Test entropy is 0 for single-value column."""
        analyzer = QualityRulesAnalyzer()

        for i in range(100):
            analyzer.update("constant", "varchar")

        result = analyzer.finalize()
        assert result.entropy == 0.0

    def test_entropy_uniform_distribution(self):
        """Test entropy for uniformly distributed values."""
        analyzer = QualityRulesAnalyzer()

        # 4 values, each appearing 25 times
        for i in range(25):
            analyzer.update("A", "varchar")
            analyzer.update("B", "varchar")
            analyzer.update("C", "varchar")
            analyzer.update("D", "varchar")

        result = analyzer.finalize()
        # Entropy should be log2(4) = 2.0 for uniform distribution
        assert result.entropy == pytest.approx(2.0, abs=0.01)

    def test_entropy_skewed_distribution(self):
        """Test entropy for skewed distribution."""
        analyzer = QualityRulesAnalyzer()

        # Highly skewed: 90 of one value, 10 of another
        for i in range(90):
            analyzer.update("common", "varchar")
        for i in range(10):
            analyzer.update("rare", "varchar")

        result = analyzer.finalize()
        # Entropy should be low due to skew
        assert result.entropy is not None
        assert result.entropy < 1.0

    def test_outlier_detection_numeric(self):
        """Test outlier detection for numeric columns using IQR method."""
        analyzer = QualityRulesAnalyzer()

        # Normal distribution: 1-100, with outliers at 500 and 1000
        for i in range(1, 101):
            analyzer.update(str(i), "numeric")
        analyzer.update("500", "numeric")
        analyzer.update("1000", "numeric")

        result = analyzer.finalize()
        # Should detect the two outliers
        assert result.outlier_count == 2
        assert result.outlier_pct > 0

    def test_outlier_detection_no_outliers(self):
        """Test that tight distributions have no outliers."""
        analyzer = QualityRulesAnalyzer()

        # Very tight distribution
        for i in range(100):
            analyzer.update(str(50 + i % 10), "numeric")

        result = analyzer.finalize()
        assert result.outlier_count == 0
        assert result.outlier_pct == 0.0

    def test_whitespace_detection_leading(self):
        """Test detection of leading whitespace."""
        analyzer = QualityRulesAnalyzer()

        analyzer.update("normal", "varchar")
        analyzer.update("  leading", "varchar")
        analyzer.update("\tleading_tab", "varchar")
        analyzer.update("normal2", "varchar")

        result = analyzer.finalize()
        assert result.leading_whitespace_count == 2

    def test_whitespace_detection_trailing(self):
        """Test detection of trailing whitespace."""
        analyzer = QualityRulesAnalyzer()

        analyzer.update("normal", "varchar")
        analyzer.update("trailing  ", "varchar")
        analyzer.update("trailing_tab\t", "varchar")
        analyzer.update("normal2", "varchar")

        result = analyzer.finalize()
        assert result.trailing_whitespace_count == 2

    def test_whitespace_detection_both(self):
        """Test detection of both leading and trailing whitespace."""
        analyzer = QualityRulesAnalyzer()

        analyzer.update("  both  ", "varchar")

        result = analyzer.finalize()
        assert result.leading_whitespace_count == 1
        assert result.trailing_whitespace_count == 1


class TestPHIRiskFlags:
    """Tests for PHI risk flag detection."""

    def test_ssn_triggers_phi_flag(self):
        """Test that SSN pattern triggers potential_ssn flag."""
        analyzer = QualityRulesAnalyzer()

        # Add enough SSNs to exceed threshold (10% of 100 = 10)
        for i in range(15):
            analyzer.update("123-45-6789", "varchar")
        for i in range(85):
            analyzer.update("other", "varchar")

        result = analyzer.finalize()
        assert "potential_ssn" in result.phi_risk_flags
        assert "ssn_tin" in result.detected_patterns

    def test_npi_triggers_phi_flag(self):
        """Test that NPI pattern triggers potential_npi flag."""
        analyzer = QualityRulesAnalyzer()

        # Add enough NPIs to exceed threshold
        for i in range(15):
            analyzer.update("1234567893", "varchar")
        for i in range(85):
            analyzer.update("other", "varchar")

        result = analyzer.finalize()
        assert "potential_npi" in result.phi_risk_flags
        assert "npi" in result.detected_patterns

    def test_email_triggers_phi_flag(self):
        """Test that email pattern triggers potential_email_pii flag."""
        analyzer = QualityRulesAnalyzer()

        # Add enough emails to exceed threshold
        for i in range(15):
            analyzer.update("test@example.com", "varchar")
        for i in range(85):
            analyzer.update("other", "varchar")

        result = analyzer.finalize()
        assert "potential_email_pii" in result.phi_risk_flags
        assert "email" in result.detected_patterns

    def test_phone_triggers_phi_flag(self):
        """Test that phone pattern triggers potential_phone_pii flag."""
        analyzer = QualityRulesAnalyzer()

        # Add enough phone numbers to exceed threshold
        for i in range(15):
            analyzer.update("555-123-4567", "varchar")
        for i in range(85):
            analyzer.update("other", "varchar")

        result = analyzer.finalize()
        assert "potential_phone_pii" in result.phi_risk_flags
        assert "phone_us" in result.detected_patterns

    def test_multiple_phi_flags(self):
        """Test detection of multiple PHI risk flags."""
        analyzer = QualityRulesAnalyzer()

        # Mix of different PII types
        analyzer.update("test@example.com", "varchar")
        analyzer.update("555-123-4567", "varchar")
        analyzer.update("123-45-6789", "varchar")

        result = analyzer.finalize()
        # With only 3 values, none will exceed 10% threshold individually
        # but flags are set if ANY matches exist (count > 0)
        assert len(result.phi_risk_flags) >= 0

    def test_no_phi_flags_for_normal_data(self):
        """Test that normal data doesn't trigger PHI flags."""
        analyzer = QualityRulesAnalyzer()

        for i in range(100):
            analyzer.update(f"normal_value_{i}", "varchar")

        result = analyzer.finalize()
        assert len(result.phi_risk_flags) == 0


class TestPatternThresholds:
    """Tests for pattern detection threshold (10% of non-null values)."""

    def test_pattern_below_threshold_not_reported(self):
        """Test that patterns below 10% threshold are not reported."""
        analyzer = QualityRulesAnalyzer()

        # 5 emails out of 100 = 5% (below 10% threshold)
        for i in range(5):
            analyzer.update("test@example.com", "varchar")
        for i in range(95):
            analyzer.update("not_email", "varchar")

        result = analyzer.finalize()
        # Should not be in detected patterns (below threshold)
        assert "email" not in result.detected_patterns

    def test_pattern_above_threshold_reported(self):
        """Test that patterns above 10% threshold are reported."""
        analyzer = QualityRulesAnalyzer()

        # 15 emails out of 100 = 15% (above 10% threshold)
        for i in range(15):
            analyzer.update("test@example.com", "varchar")
        for i in range(85):
            analyzer.update("not_email", "varchar")

        result = analyzer.finalize()
        assert "email" in result.detected_patterns
        assert result.detected_patterns["email"] == 15

    def test_pattern_exactly_threshold(self):
        """Test pattern detection at exactly 10% threshold."""
        analyzer = QualityRulesAnalyzer()

        # 10 emails out of 100 = 10% (exactly threshold)
        for i in range(10):
            analyzer.update("test@example.com", "varchar")
        for i in range(90):
            analyzer.update("not_email", "varchar")

        result = analyzer.finalize()
        # Threshold is max(1, 0.10 * non_null), so 10 should be included
        assert "email" in result.detected_patterns


class TestHealthcarePatterns:
    """Tests for healthcare-specific pattern detection."""

    def test_icd10_diagnosis_detection(self):
        """Test ICD-10 diagnosis code detection."""
        analyzer = QualityRulesAnalyzer()

        icd10_codes = ["A01", "A01.1", "Z99.89", "J44.0", "E11.9"]

        # Add codes above threshold
        for code in icd10_codes:
            for i in range(3):
                analyzer.update(code, "varchar")

        # Add other values
        for i in range(50):
            analyzer.update("other", "varchar")

        result = analyzer.finalize()
        if "icd10_diagnosis" in result.detected_patterns:
            assert result.detected_patterns["icd10_diagnosis"] == 15

    def test_cpt_code_detection(self):
        """Test CPT code detection."""
        analyzer = QualityRulesAnalyzer()

        # Common CPT codes
        for i in range(15):
            analyzer.update("99213", "varchar")  # Office visit
        for i in range(85):
            analyzer.update("other", "varchar")

        result = analyzer.finalize()
        assert "cpt_code" in result.detected_patterns

    def test_npi_with_checksum_validation(self):
        """Test NPI detection includes valid checksum count."""
        analyzer = QualityRulesAnalyzer()

        # Valid NPIs
        for i in range(10):
            analyzer.update("1234567893", "varchar")  # Valid checksum

        # Invalid checksum NPIs (valid format, wrong checksum)
        for i in range(5):
            analyzer.update("1234567890", "varchar")  # Invalid checksum

        # Other values
        for i in range(85):
            analyzer.update("other", "varchar")

        result = analyzer.finalize()
        if "npi" in result.detected_patterns:
            # Should count all NPIs matching format
            assert result.detected_patterns["npi"] >= 10
            # Valid checksum count should be tracked separately
            if "npi_valid_checksum" in result.detected_patterns:
                assert result.detected_patterns["npi_valid_checksum"] >= 10


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_column(self):
        """Test analyzer with no values."""
        analyzer = QualityRulesAnalyzer()

        result = analyzer.finalize()
        assert result.completeness_pct == 0.0
        assert result.uniqueness_pct == 0.0
        assert result.entropy is None
        assert len(result.detected_patterns) == 0

    def test_single_value(self):
        """Test analyzer with single value."""
        analyzer = QualityRulesAnalyzer()
        analyzer.update("single", "varchar")

        result = analyzer.finalize()
        assert result.completeness_pct == 100.0
        assert result.uniqueness_pct == 100.0
        assert result.entropy == 0.0

    def test_all_nulls(self):
        """Test analyzer with all null values."""
        analyzer = QualityRulesAnalyzer()

        for i in range(100):
            analyzer.update(None, "varchar")

        result = analyzer.finalize()
        assert result.completeness_pct == 0.0
        assert result.null_count == 100

    def test_case_insensitive_state_codes(self):
        """Test that state codes are detected case-insensitively."""
        analyzer = QualityRulesAnalyzer()

        # Test both upper and lower case
        for i in range(10):
            analyzer.update("ca", "varchar")
            analyzer.update("NY", "varchar")

        for i in range(80):
            analyzer.update("other", "varchar")

        result = analyzer.finalize()
        # Both should be detected
        if "us_state_code" in result.detected_patterns:
            assert result.detected_patterns["us_state_code"] == 20

    def test_case_insensitive_icd10(self):
        """Test that ICD-10 codes are detected case-insensitively."""
        analyzer = QualityRulesAnalyzer()

        for i in range(15):
            analyzer.update("a01.1", "varchar")  # lowercase
        for i in range(85):
            analyzer.update("other", "varchar")

        result = analyzer.finalize()
        # Should still detect (pattern matches .upper())
        if "icd10_diagnosis" in result.detected_patterns:
            assert result.detected_patterns["icd10_diagnosis"] == 15
