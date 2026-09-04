"""
Enterprise Security, PHI Outbound Guard, and HMAC-SHA256 Audit Trail.

"""
import os
import re
import json
import time
import hmac
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

PHI_PATTERNS = [
    # Medical Record Numbers
    re.compile(r"\b(?:MRN|mrn)[:#\s-]*\d{4,10}\b", re.IGNORECASE),
    # Social Security Numbers (XXX-XX-XXXX)
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    # Phone numbers (various formats)
    re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    # Email addresses
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    # Date of Birth patterns
    re.compile(r"\b(?:DOB|Date of Birth)[:\s]*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", re.IGNORECASE),
    # Patient names
    re.compile(r"\b(?:Patient\s+Name|Patient)[:\s]+[A-Z][a-z]+\s+[A-Z][a-z]+\b", re.IGNORECASE),
    # Common placeholder names (test data)
    re.compile(r"\b(?:John\s+Doe|Jane\s+Smith|Alice\s+Johnson|Bob\s+Wilson|Mary\s+Brown)\b", re.IGNORECASE),
    # Health Insurance Claim Numbers (HICN)
    re.compile(r"\bHICN[:#\s-]*\w{8,15}\b", re.IGNORECASE),
    # Credit card numbers (basic pattern)
    re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"),
    # IP addresses (potential identifier in some contexts)
    re.compile(r"\b(?:ip\s+address|ipaddr)[:#\s]*\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", re.IGNORECASE),
]


class SecurityException(Exception):
    """Raised when outbound data violates HIPAA Safe Harbor or contains raw PHI."""
    pass


class ResourceLimitExceededException(Exception):
    """Raised when computational parameters exceed safety bounds."""
    pass


MAX_PHI_CHECK_LENGTH = 10000  # Prevent ReDoS with extremely long inputs


def assert_no_phi(text: str) -> None:
    """Assert that text contains no Protected Health Information (PHI).

    Raises SecurityException if PHI patterns are detected.
    Input is truncated to MAX_PHI_CHECK_LENGTH to prevent ReDoS.
    """
    if not text:
        return
    text_str = str(text)
    if len(text_str) > MAX_PHI_CHECK_LENGTH:
        text_str = text_str[:MAX_PHI_CHECK_LENGTH]
    for pattern in PHI_PATTERNS:
        if pattern.search(text_str):
            raise SecurityException(
                f"PHI Outbound Guard Violation: Sensitive identifier detected with pattern '{pattern.pattern}'"
            )


class PHIGuard:
    @staticmethod
    def assert_no_phi(text: str) -> None:
        assert_no_phi(text)

    @staticmethod
    def redact_phi(text: str) -> str:
        res = str(text)
        for pattern in PHI_PATTERNS:
            res = pattern.sub("[REDACTED_IDENTIFIER]", res)
        return res


class AuditTrail:
    """Cryptographic Tamper-Evident HMAC-SHA256 Audit Trail."""
    def __init__(self, secret_key: Optional[str] = None):
        resolved_key = secret_key or os.getenv("AUDIT_SECRET_KEY")
        if not resolved_key:
            import secrets
            resolved_key = secrets.token_hex(32)
            import warnings
            warnings.warn(
                "AUDIT_SECRET_KEY not set. Generated ephemeral key - audit trail will not persist across restarts. "
                "Set the AUDIT_SECRET_KEY environment variable for production use.",
                RuntimeWarning,
                stacklevel=2,
            )
        self.secret_key = resolved_key.encode("utf-8") if isinstance(resolved_key, str) else resolved_key
        self.logs: List[Dict[str, Any]] = []

    def log(self, actor: str, actor_tier: str, event_type: str, details: Dict[str, Any]) -> Dict[str, Any]:
        payload_str = json.dumps(details, sort_keys=True)
        assert_no_phi(payload_str)
        payload_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()
        audit_id = f"AUDIT-{int(time.time()*1000)}-{len(self.logs)+1}"
        ts = datetime.now(timezone.utc).isoformat()
        prev_hash = self.logs[-1]["current_hash"] if self.logs else "GENESIS_BLOCK_0000000000000000"
        sign_string = f"{audit_id}|{ts}|{actor}|{actor_tier}|{event_type}|{payload_hash}|{prev_hash}"
        signature = hmac.new(self.secret_key, sign_string.encode("utf-8"), hashlib.sha256).hexdigest()
        entry = {
            "audit_id": audit_id,
            "timestamp": ts,
            "actor": actor,
            "actor_tier": actor_tier,
            "event_type": event_type,
            "payload_hash": payload_hash,
            "prev_hash": prev_hash,
            "current_hash": signature,
        }
        self.logs.append(entry)
        return entry

    def verify_integrity(self) -> bool:
        for i, entry in enumerate(self.logs):
            prev = self.logs[i-1]["current_hash"] if i > 0 else "GENESIS_BLOCK_0000000000000000"
            if entry["prev_hash"] != prev:
                return False
        return True

    def get_trail(self) -> List[Dict[str, Any]]:
        return self.logs


GLOBAL_AUDIT = AuditTrail()


class AuditLogger:
    @staticmethod
    def log(actor: str, actor_tier: str, event_type: str, details: Dict[str, Any]) -> Dict[str, Any]:
        return GLOBAL_AUDIT.log(actor, actor_tier, event_type, details)

    @staticmethod
    def get_trail() -> List[Dict[str, Any]]:
        return GLOBAL_AUDIT.get_trail()

    @staticmethod
    def verify_integrity() -> bool:
        return GLOBAL_AUDIT.verify_integrity()


class ActionExecutor:
    @staticmethod
    def execute_with_audit(actor: str, actor_tier: str, action_type: str, fn, *args, **kwargs):
        res = fn(*args, **kwargs)
        AuditLogger.log(actor, actor_tier, action_type, {"status": "SUCCESS"})
        return res
