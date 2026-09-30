"""
Security helpers, PHI outbound checks, and a tamper-evident HMAC-SHA256 audit trail.
"""
import hashlib
import hmac
import json
import os
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

PHI_PATTERNS = [
    re.compile(r"\b(?:MRN|mrn)[:#\s-]*\d{4,10}\b", re.IGNORECASE),
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"\b(?:DOB|Date of Birth)[:\s]*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", re.IGNORECASE),
    re.compile(r"\b(?:Patient\s+Name|Patient)[:\s]+[A-Z][a-z]+\s+[A-Z][a-z]+\b", re.IGNORECASE),
    re.compile(r"\b(?:John\s+Doe|Jane\s+Smith|Alice\s+Johnson|Bob\s+Wilson|Mary\s+Brown)\b", re.IGNORECASE),
    re.compile(r"\bHICN[:#\s-]*\w{8,15}\b", re.IGNORECASE),
    re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"),
    re.compile(r"\b(?:ip\s+address|ipaddr)[:#\s]*\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", re.IGNORECASE),
]


class SecurityException(Exception):
    """Raised when outbound text contains a configured sensitive-identifier pattern."""


class ResourceLimitExceededException(Exception):
    """Raised when computational parameters exceed safety bounds."""


MAX_PHI_CHECK_LENGTH = 10_000
PHI_SCAN_OVERLAP = 256


def _iter_phi_scan_chunks(text: str):
    """Yield bounded, overlapping chunks so long inputs cannot bypass detection."""
    if len(text) <= MAX_PHI_CHECK_LENGTH:
        yield text
        return

    step = MAX_PHI_CHECK_LENGTH - PHI_SCAN_OVERLAP
    for start in range(0, len(text), step):
        yield text[start : start + MAX_PHI_CHECK_LENGTH]


def assert_no_phi(text: str) -> None:
    """Raise SecurityException when a configured sensitive-identifier pattern is detected.

    Long inputs are scanned in bounded overlapping chunks. This limits regex work per
    search while still examining the entire input, including identifiers located after
    the first 10,000 characters or spanning a chunk boundary.
    """
    if not text:
        return

    for chunk in _iter_phi_scan_chunks(str(text)):
        for pattern in PHI_PATTERNS:
            if pattern.search(chunk):
                raise SecurityException("Sensitive identifier detected by outbound data guard")


class PHIGuard:
    @staticmethod
    def assert_no_phi(text: str) -> None:
        assert_no_phi(text)

    @staticmethod
    def redact_phi(text: str) -> str:
        result = str(text)
        for pattern in PHI_PATTERNS:
            result = pattern.sub("[REDACTED_IDENTIFIER]", result)
        return result


class AuditTrail:
    """In-memory HMAC-SHA256 hash chain with per-entry signature verification."""

    GENESIS_HASH = "GENESIS_BLOCK_0000000000000000"

    def __init__(self, secret_key: Optional[str] = None):
        resolved_key = secret_key or os.getenv("AUDIT_SECRET_KEY")
        if not resolved_key:
            import secrets
            import warnings

            resolved_key = secrets.token_hex(32)
            warnings.warn(
                "AUDIT_SECRET_KEY not set. Generated ephemeral key - audit trail will not persist across restarts. "
                "Set AUDIT_SECRET_KEY for deployments that require verification across process restarts.",
                RuntimeWarning,
                stacklevel=2,
            )
        self.secret_key = resolved_key.encode("utf-8") if isinstance(resolved_key, str) else resolved_key
        self.logs: List[Dict[str, Any]] = []

    def _signature(
        self,
        audit_id: str,
        timestamp: str,
        actor: str,
        actor_tier: str,
        event_type: str,
        payload_hash: str,
        prev_hash: str,
    ) -> str:
        sign_string = (
            f"{audit_id}|{timestamp}|{actor}|{actor_tier}|{event_type}|{payload_hash}|{prev_hash}"
        )
        return hmac.new(self.secret_key, sign_string.encode("utf-8"), hashlib.sha256).hexdigest()

    def log(self, actor: str, actor_tier: str, event_type: str, details: Dict[str, Any]) -> Dict[str, Any]:
        payload_str = json.dumps(details, sort_keys=True, separators=(",", ":"), default=str)
        assert_no_phi(payload_str)
        payload_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()
        audit_id = f"AUDIT-{int(time.time() * 1000)}-{len(self.logs) + 1}"
        timestamp = datetime.now(timezone.utc).isoformat()
        prev_hash = self.logs[-1]["current_hash"] if self.logs else self.GENESIS_HASH
        signature = self._signature(
            audit_id,
            timestamp,
            actor,
            actor_tier,
            event_type,
            payload_hash,
            prev_hash,
        )
        entry = {
            "audit_id": audit_id,
            "timestamp": timestamp,
            "actor": actor,
            "actor_tier": actor_tier,
            "event_type": event_type,
            "payload_hash": payload_hash,
            "prev_hash": prev_hash,
            "current_hash": signature,
        }
        self.logs.append(entry)
        return dict(entry)

    def verify_integrity(self) -> bool:
        """Recompute every HMAC and validate the complete hash chain."""
        required = {
            "audit_id",
            "timestamp",
            "actor",
            "actor_tier",
            "event_type",
            "payload_hash",
            "prev_hash",
            "current_hash",
        }
        try:
            for index, entry in enumerate(self.logs):
                if not required.issubset(entry):
                    return False

                expected_prev = (
                    self.logs[index - 1]["current_hash"] if index > 0 else self.GENESIS_HASH
                )
                if not hmac.compare_digest(str(entry["prev_hash"]), str(expected_prev)):
                    return False

                expected_signature = self._signature(
                    str(entry["audit_id"]),
                    str(entry["timestamp"]),
                    str(entry["actor"]),
                    str(entry["actor_tier"]),
                    str(entry["event_type"]),
                    str(entry["payload_hash"]),
                    str(entry["prev_hash"]),
                )
                if not hmac.compare_digest(
                    str(entry["current_hash"]),
                    expected_signature,
                ):
                    return False
        except (KeyError, TypeError, ValueError):
            return False

        return True

    def get_trail(self) -> List[Dict[str, Any]]:
        """Return defensive copies so callers cannot mutate the internal ledger."""
        return [dict(entry) for entry in self.logs]


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
        result = fn(*args, **kwargs)
        AuditLogger.log(actor, actor_tier, action_type, {"status": "SUCCESS"})
        return result
