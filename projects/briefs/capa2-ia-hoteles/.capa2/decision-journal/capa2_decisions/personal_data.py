"""Reuses the base journal's own personal-data patterns against source files.

``knowledge_ingest.decision_journal`` already rejects personal data in the
fields passed directly to ``add()`` (title, hypothesis, expected_outcome —
see its ``_safe_text``). It does **not** content-scan the source document
itself (it only hashes it for binding). This module closes that gap for the
Capa 2 adapter by re-running the exact same compiled patterns — imported,
never copied — against the full source note text.
"""

from __future__ import annotations

from . import engine_path

engine_path.ensure_engine_importable()

from knowledge_ingest.registry import (  # noqa: E402  (import after sys.path bootstrap)
    ADDRESS_PATTERN,
    DNI_PATTERN,
    EMAIL_PATTERN,
    IBAN_PATTERN,
    PHONE_PATTERN,
)

_PATTERNS = (
    ("email", EMAIL_PATTERN),
    ("teléfono", PHONE_PATTERN),
    ("DNI", DNI_PATTERN),
    ("IBAN", IBAN_PATTERN),
    ("dirección postal", ADDRESS_PATTERN),
)


class PersonalDataDetected(ValueError):
    """Raised when text appears to contain personal data."""


def reject_personal_data(text: str, *, field: str) -> None:
    for label, pattern in _PATTERNS:
        match = pattern.search(text)
        if match:
            raise PersonalDataDetected(f"posible {label} en {field}")
