"""Validates a decision's source note before (or after) it enters the journal.

Combines the Capa 2 context header contract with the two content filters
(Soho, personal data). Used both as a pre-flight step (recommended before
running ``knowledge_ingest.decision_journal add``) and by ``check`` to
re-verify every source already on record.
"""

from __future__ import annotations

from pathlib import Path

from .context import ContextHeader, InvalidContextHeader, parse_context_header
from .personal_data import PersonalDataDetected, reject_personal_data
from .soho_filter import SohoDataDetected, reject_soho_references


class SourceValidationError(ValueError):
    """Raised when a source note fails any Capa 2 validation rule."""


def validate_source_text(text: str, *, label: str) -> ContextHeader:
    """Validate the full text of a source note. Returns its parsed header.

    Raises ``SourceValidationError`` (chaining the specific cause) on the
    first failure. Fails closed: any of the three checks failing rejects the
    whole note.
    """
    try:
        header = parse_context_header(text)
    except InvalidContextHeader as error:
        raise SourceValidationError(f"{label}: encabezado de contexto inválido: {error}") from error
    try:
        reject_soho_references(text, field=label)
    except SohoDataDetected as error:
        raise SourceValidationError(f"{label}: {error}") from error
    try:
        reject_personal_data(text, field=label)
    except PersonalDataDetected as error:
        raise SourceValidationError(f"{label}: {error}") from error
    return header


def validate_source_file(path: Path) -> ContextHeader:
    text = path.read_text(encoding="utf-8")
    return validate_source_text(text, label=str(path))
