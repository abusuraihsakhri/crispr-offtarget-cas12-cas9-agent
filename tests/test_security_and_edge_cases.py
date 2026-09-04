"""
Security and Edge Case Tests for crispr-offtarget-cas12-cas9-agent.
Tests PHI guard enforcement, path traversal protection, input validation,
and HMAC audit trail integrity.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from agents.base import PHIGuard, AuditLogger, SecurityException, assert_no_phi, MAX_PHI_CHECK_LENGTH
from agents.models import SystemTaskPayload
from agents.supervisor import SystemSupervisor
from cli import _validate_safe_path, main


class TestPHIGuardEnforcement:
    """Test PHI detection and redaction capabilities."""

    def test_mrn_detection(self):
        with pytest.raises(SecurityException):
            PHIGuard.assert_no_phi("Patient MRN-994827 blood culture positive")

    def test_ssn_detection(self):
        with pytest.raises(SecurityException):
            PHIGuard.assert_no_phi("SSN: 123-45-6789")

    def test_phone_number_detection(self):
        with pytest.raises(SecurityException):
            PHIGuard.assert_no_phi("Call patient at (555) 123-4567")

    def test_email_detection(self):
        with pytest.raises(SecurityException):
            PHIGuard.assert_no_phi("Email patient@example.com for results")

    def test_dob_detection(self):
        with pytest.raises(SecurityException):
            PHIGuard.assert_no_phi("DOB: 01/15/1985")

    def test_patient_name_detection(self):
        with pytest.raises(SecurityException):
            PHIGuard.assert_no_phi("Patient Name: John Smith")

    def test_placeholder_name_detection(self):
        with pytest.raises(SecurityException):
            PHIGuard.assert_no_phi("Test patient John Doe admitted")

    def test_clean_text_passes(self):
        PHIGuard.assert_no_phi("Analytical assay specimen KEY-001 optimal")
        PHIGuard.assert_no_phi("CRISPR guide sequence GACACCGTGGACAGCAACAT evaluated")

    def test_empty_text_passes(self):
        PHIGuard.assert_no_phi("")
        PHIGuard.assert_no_phi(None)

    def test_phi_redaction(self):
        redacted = PHIGuard.redact_phi("Contact patient at test@example.com")
        assert "[REDACTED_IDENTIFIER]" in redacted
        assert "test@example.com" not in redacted

    def test_long_input_truncation(self):
        """Test that very long inputs are truncated to prevent ReDoS."""
        long_input = "A" * (MAX_PHI_CHECK_LENGTH + 1000)
        # Should not raise, just truncate
        PHIGuard.assert_no_phi(long_input)

    def test_module_level_assert_no_phi(self):
        """Test the module-level assert_no_phi function."""
        with pytest.raises(SecurityException):
            assert_no_phi("MRN-12345678")
        assert_no_phi("Safe text without PHI")


class TestPathTraversalProtection:
    """Test file path validation."""

    def test_safe_path_accepted(self):
        assert _validate_safe_path("data.csv") == "data.csv"
        assert _validate_safe_path("subdir/data.csv") == "subdir\\data.csv" or _validate_safe_path("subdir/data.csv") == "subdir/data.csv"

    def test_path_traversal_rejected(self):
        with pytest.raises(Exception):
            _validate_safe_path("../etc/passwd")
        with pytest.raises(Exception):
            _validate_safe_path("..\\windows\\system32\\config\\sam")
        with pytest.raises(Exception):
            _validate_safe_path("data/../../../etc/shadow")

    def test_nested_path_traversal_rejected(self):
        with pytest.raises(Exception):
            _validate_safe_path("subdir/../../etc/passwd")


class TestAuditTrailIntegrity:
    """Test HMAC-SHA256 audit trail."""

    def test_audit_trail_chain_integrity(self):
        supervisor = SystemSupervisor(model_provider="mock")
        payload = SystemTaskPayload(
            task_id="AUDIT-TEST-01",
            target_identifier="KEY-AUDIT-01",
            primary_metric=10.0,
            secondary_metric=5.0,
            status_descriptor="NOMINAL"
        )
        supervisor.process_task(payload)
        assert AuditLogger.verify_integrity() is True

    def test_audit_trail_multiple_entries(self):
        supervisor = SystemSupervisor(model_provider="mock")
        for i in range(5):
            payload = SystemTaskPayload(
                task_id=f"AUDIT-MULTI-{i:03d}",
                target_identifier=f"KEY-MULTI-{i:03d}",
                primary_metric=10.0 + i,
                secondary_metric=5.0,
                status_descriptor="NOMINAL"
            )
            supervisor.process_task(payload)
        trail = AuditLogger.get_trail()
        assert len(trail) >= 5
        assert AuditLogger.verify_integrity() is True


class TestCLIEdgeCases:
    """Test CLI edge cases and error handling."""

    def test_batch_with_safe_path(self):
        """Test that batch command works with safe paths."""
        # Create a temp CSV file
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            f.write("task_id,target_identifier,primary_metric,secondary_metric,is_critical_flag,status_descriptor\n")
            f.write("T1,KEY-01,10.0,5.0,False,NOMINAL\n")
            temp_path = f.name

        try:
            output_path = temp_path.replace('.csv', '_out.csv')
            result = main(["batch", "-i", temp_path, "-o", output_path])
            assert result == 0
            os.unlink(output_path)
        finally:
            os.unlink(temp_path)

    def test_batch_rejects_traversal_path(self):
        """Test that batch command rejects path traversal attempts."""
        with pytest.raises(SystemExit):
            main(["batch", "-i", "../etc/passwd"])


class TestInputValidation:
    """Test input validation in core engine."""

    def test_empty_sequence_raises_error(self):
        from crispr_cas12_cas9 import CRISPRCas12Cas9Engine
        with pytest.raises(ValueError, match="cannot be empty"):
            CRISPRCas12Cas9Engine.calculate_spcas9_cleavage_prob("", "GACACCGTGGACAGCAACAT")

    def test_invalid_characters_raise_error(self):
        from crispr_cas12_cas9 import CRISPRCas12Cas9Engine
        with pytest.raises(ValueError, match="invalid characters"):
            CRISPRCas12Cas9Engine.calculate_spcas9_cleavage_prob("GACACCGTGGACAGCAACAX", "GACACCGTGGACAGCAACAT")

    def test_cas12a_empty_sequence_raises_error(self):
        from crispr_cas12_cas9 import CRISPRCas12Cas9Engine
        with pytest.raises(ValueError, match="cannot be empty"):
            CRISPRCas12Cas9Engine.calculate_cas12a_cleavage_prob("", "ATGCGATCGATCGATCGATCGAT")

    def test_cas12a_invalid_characters_raise_error(self):
        from crispr_cas12_cas9 import CRISPRCas12Cas9Engine
        with pytest.raises(ValueError, match="invalid characters"):
            CRISPRCas12Cas9Engine.calculate_cas12a_cleavage_prob("ATGCGATCGATCGATCGATCGAX", "ATGCGATCGATCGATCGATCGAT")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
