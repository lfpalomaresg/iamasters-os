"""Parses and validates the Capa 2 context header (FR-053 design, section 5).

Each decision's source note under ``knowledge/decisions/*.md`` starts with a
small YAML-like header:

    ---
    scope: content|cadence|format|brand|loop
    content_ids: [S9]
    metric_code: engagement_rate
    baseline: "mediana S6-S7"
    target: ">= baseline"
    owner: luisfran
    ---

``supersedes: D-001`` is an optional extension (not part of the base engine's
schema) used to trace ``ADJUST`` successors back to the decision they replace,
per section 7's "decisiones sucesoras creadas por un ADJUST".

This is a small hand-rolled parser (no PyYAML dependency) scoped exactly to
this fixed field set. Anything outside that shape fails closed, matching the
base engine's own "unexpected schema" philosophy.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

HEADER_DELIMITER = "---"
VALID_SCOPES = {"content", "cadence", "format", "brand", "loop"}
REQUIRED_FIELDS = ("scope", "content_ids", "metric_code", "baseline", "target", "owner")
OPTIONAL_FIELDS = ("supersedes",)
ALL_FIELDS = set(REQUIRED_FIELDS) | set(OPTIONAL_FIELDS)

CONTENT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,19}$")
METRIC_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9_]{2,49}$")
DECISION_ID_PATTERN = re.compile(r"^D-[0-9]{3,6}$")
OWNER_VALUE = "luisfran"
MAX_TEXT_LENGTH = 500


class InvalidContextHeader(ValueError):
    """Raised when the Capa 2 context header is missing, malformed, or unsafe."""


@dataclass(frozen=True)
class ContextHeader:
    scope: str
    content_ids: tuple[str, ...]
    metric_code: str
    baseline: str
    target: str
    owner: str
    supersedes: str | None = None


def parse_context_header(source_text: str) -> ContextHeader:
    """Extract and validate the header from a source note's full text."""
    header_text = _extract_header_block(source_text)
    fields = _parse_fields(header_text)

    missing = [name for name in REQUIRED_FIELDS if name not in fields]
    if missing:
        raise InvalidContextHeader(f"faltan campos obligatorios: {', '.join(missing)}")
    unknown = [name for name in fields if name not in ALL_FIELDS]
    if unknown:
        raise InvalidContextHeader(f"campos no reconocidos en el encabezado: {', '.join(unknown)}")

    scope = fields["scope"]
    if scope not in VALID_SCOPES:
        raise InvalidContextHeader(f"scope inválido: {scope!r}")

    content_ids = _parse_list(fields["content_ids"])
    for content_id in content_ids:
        if not CONTENT_ID_PATTERN.fullmatch(content_id):
            raise InvalidContextHeader(f"content_id inválido: {content_id!r}")

    metric_code = fields["metric_code"]
    if not METRIC_CODE_PATTERN.fullmatch(metric_code):
        raise InvalidContextHeader(f"metric_code inválido: {metric_code!r}")

    baseline = _validated_text(fields["baseline"], "baseline")
    target = _validated_text(fields["target"], "target")

    owner = fields["owner"]
    if owner != OWNER_VALUE:
        raise InvalidContextHeader(f"owner debe ser {OWNER_VALUE!r}, no {owner!r}")

    supersedes = fields.get("supersedes")
    if supersedes is not None and not DECISION_ID_PATTERN.fullmatch(supersedes):
        raise InvalidContextHeader(f"supersedes inválido: {supersedes!r}")

    return ContextHeader(
        scope=scope,
        content_ids=content_ids,
        metric_code=metric_code,
        baseline=baseline,
        target=target,
        owner=owner,
        supersedes=supersedes,
    )


def _extract_header_block(source_text: str) -> str:
    lines = source_text.splitlines()
    if not lines or lines[0].strip() != HEADER_DELIMITER:
        raise InvalidContextHeader("la nota debe empezar con un encabezado --- ... ---")
    try:
        closing_index = next(
            index for index, line in enumerate(lines[1:], start=1) if line.strip() == HEADER_DELIMITER
        )
    except StopIteration as error:
        raise InvalidContextHeader("el encabezado no tiene línea de cierre ---") from error
    return "\n".join(lines[1:closing_index])


_LINE_PATTERN = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$")


def _parse_fields(header_text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for raw_line in header_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = _LINE_PATTERN.fullmatch(line)
        if not match:
            raise InvalidContextHeader(f"línea de encabezado ilegible: {raw_line!r}")
        key, value = match.group(1), match.group(2).strip()
        if key in fields:
            raise InvalidContextHeader(f"campo duplicado en el encabezado: {key!r}")
        fields[key] = _unquote(value)
    return fields


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def _parse_list(raw_value: str) -> tuple[str, ...]:
    value = raw_value.strip()
    if not (value.startswith("[") and value.endswith("]")):
        raise InvalidContextHeader(f"content_ids debe ser una lista entre corchetes: {raw_value!r}")
    inner = value[1:-1].strip()
    if not inner:
        return ()
    items = [item.strip() for item in inner.split(",")]
    if any(not item for item in items):
        raise InvalidContextHeader("content_ids tiene un elemento vacío")
    return tuple(_unquote(item) for item in items)


def _validated_text(value: str, field: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise InvalidContextHeader(f"{field} no puede estar vacío")
    if len(cleaned) > MAX_TEXT_LENGTH:
        raise InvalidContextHeader(f"{field} supera los {MAX_TEXT_LENGTH} caracteres")
    return cleaned
