"""PII/PHI anonymization gateway.

Scrubs PII/PHI from content before it reaches an LLM provider, via Presidio
(ADR-0043). Every caller gets auto-redact-and-proceed on a detected match
except the `conversational-authoring` context, which gets flag-for-review
(ADR-0014 amendment). See GH #136.
"""

from pii_gateway.audit import AuditLogger, default_audit_path
from pii_gateway.config import default_config_path, load_config, save_config
from pii_gateway.models import (
    AuditEntry,
    DetectorCategoryConfiguration,
    Match,
    PendingConfirmation,
    Resolution,
    ScrubAction,
    ScrubResult,
)
from pii_gateway.router import create_settings_router
from pii_gateway.scrub import scrub

__all__ = [
    "AuditEntry",
    "AuditLogger",
    "DetectorCategoryConfiguration",
    "Match",
    "PendingConfirmation",
    "Resolution",
    "ScrubAction",
    "ScrubResult",
    "create_settings_router",
    "default_audit_path",
    "default_config_path",
    "load_config",
    "save_config",
    "scrub",
]
