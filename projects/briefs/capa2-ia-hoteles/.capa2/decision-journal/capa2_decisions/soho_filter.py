"""Rejects text that identifies internal Soho matters (FR-053 design, section 8).

This is additional to, not a replacement for, the base journal's own
personal-data filter (see ``personal_data.py``). The base engine has no
notion of "Soho" — this rule is specific to the Capa 2 adapter.

Deliberately conservative: any mention of the employer's name or its
internal systems is rejected outright, even in a plausible-looking context.
Public brand names (e.g. "Blindbeds") are NOT blocked here — Blindbeds is
Luisfran's own product and is already mentioned by design in some published
posts; only the employer's internal name and internal systems are unsafe for
a piece of persistent, git-tracked text like this journal.
"""

from __future__ import annotations

import re

_SOHO_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bsoho\b", re.IGNORECASE),
    re.compile(r"\bsihot\b", re.IGNORECASE),
    re.compile(r"\bsbh\b", re.IGNORECASE),
)


class SohoDataDetected(ValueError):
    """Raised when text appears to reference internal Soho matters."""


def reject_soho_references(text: str, *, field: str) -> None:
    for pattern in _SOHO_PATTERNS:
        match = pattern.search(text)
        if match:
            raise SohoDataDetected(
                f"posible referencia interna de Soho en {field} (coincide {match.group(0)!r})"
            )
