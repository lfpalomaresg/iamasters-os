"""Builds the read-only derived view (FR-053 design, section 7).

``build_status`` is a pure function of the store's current content plus an
explicit ``as_of`` date — no wall-clock timestamp is embedded in the output,
so running it twice against the same store and the same ``as_of`` produces
byte-identical ``status.json``/``STATUS.md`` (acceptance criterion 7:
"status es determinista e idempotente a igualdad de entradas").

This module only reads. It never calls ``DecisionJournal.add``/``close`` and
never touches ``content-log.md``.

Trust boundary (careo round 1, finding #4): this view is meant to be safe to
publish and to feed to an unattended loop. It therefore runs the exact same
integrity sweep as ``capa2_decisions check`` (via ``checks.collect_findings``)
before building anything — any decision with a finding (filesystem
corruption, an invalid context header, a Soho/PII hit in the source or in
any of its own recorded fields, including a closed decision's
``actual_outcome``) is excluded from the normal Abiertas/Cerradas tables and
surfaces only in "Errores de integridad" instead. Free text inserted into a
Markdown table cell (``title``, and — careo round 3, finding #3 — the
``decision_id``/``error`` of every integrity error, which can carry a raw,
attacker-controlled filesystem entry name) is escaped so it cannot break a
row/line or smuggle extra Markdown into ``STATUS.md``.

Careo round 3, finding #4b: a decision whose ``supersedes`` header turns out
to be invalid must appear ONLY in "Errores de integridad", never also in the
normal Abiertas/Cerradas tables — this module used to append it to the
normal table first and only add the integrity error afterwards, so it ended
up listed twice, once as if nothing were wrong. ``build_status`` now
resolves ``supersedes`` validity before deciding which section a decision
belongs to.
"""

from __future__ import annotations

import json
import re
import statistics
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from . import checks
from .context import InvalidContextHeader, parse_context_header
from .store import IntegrityError

DUE_SOON_WINDOW_DAYS = 7
LATE_REVIEW_GRACE_DAYS = 7


@dataclass(frozen=True)
class StatusView:
    as_of: str
    counts: dict
    review_timeliness: dict
    median_days_to_close: float | None
    open_decisions: tuple[dict, ...]
    closed_decisions: tuple[dict, ...]
    successors: tuple[dict, ...]
    integrity_errors: tuple[dict, ...]

    def to_json(self) -> str:
        payload = {
            "as_of": self.as_of,
            "counts": self.counts,
            "review_timeliness": self.review_timeliness,
            "median_days_to_close": self.median_days_to_close,
            "open": list(self.open_decisions),
            "closed": list(self.closed_decisions),
            "successors": list(self.successors),
            "integrity_errors": list(self.integrity_errors),
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"

    def to_markdown(self) -> str:
        lines = [
            "# Diario de decisiones — Capa 2 (FR-053)",
            "",
            f"_Generado a fecha de {self.as_of}. Vista de solo lectura — no es la fuente de verdad._",
            "",
            "## Resumen",
            "",
            f"- Abiertas: {self.counts['open_total']} "
            f"(vencidas: {self.counts['overdue']}, próximas 7 días: {self.counts['due_soon']})",
            f"- Cerradas: {self.counts['closed_total']} "
            f"(ADOPT: {self.counts['adopt']}, ADJUST: {self.counts['adjust']}, DISCARD: {self.counts['discard']})",
            f"- Revisadas a tiempo (antes de review_on + {LATE_REVIEW_GRACE_DAYS}d): "
            + _format_ratio(self.review_timeliness),
            f"- Días medianos hasta el cierre: {self._median_display()}",
            f"- Sucesoras (ADJUST): {len(self.successors)}",
            f"- Errores de integridad: {len(self.integrity_errors)}",
            "",
        ]

        if self.integrity_errors:
            lines.append(
                "> ⚠️ Hay errores de integridad — las decisiones afectadas se han excluido de las "
                "tablas de abajo y solo aparecen en la sección de errores. No se han verificado."
            )
            lines.append("")

        lines.append("## Abiertas")
        lines.append("")
        if self.open_decisions:
            lines.append("| ID | Estado | Revisión | Ámbito | Título |")
            lines.append("|---|---|---|---|---|")
            for item in self.open_decisions:
                lines.append(
                    f"| {item['decision_id']} | {item['bucket']} | {item['review_on']} "
                    f"| {item['scope'] or '—'} | {_escape_markdown_cell(item['title'])} |"
                )
        else:
            lines.append("_Ninguna._")
        lines.append("")

        lines.append("## Cerradas")
        lines.append("")
        if self.closed_decisions:
            lines.append("| ID | Veredicto | Cerrada | A tiempo | Título |")
            lines.append("|---|---|---|---|---|")
            for item in self.closed_decisions:
                on_time = "sí" if item["evaluated_on_time"] else "no"
                lines.append(
                    f"| {item['decision_id']} | {item['review_decision']} | {item['closed_at']} "
                    f"| {on_time} | {_escape_markdown_cell(item['title'])} |"
                )
        else:
            lines.append("_Ninguna._")
        lines.append("")

        lines.append("## Sucesoras (ADJUST)")
        lines.append("")
        if self.successors:
            for item in self.successors:
                lines.append(f"- {item['decision_id']} sustituye a {item['supersedes']}")
        else:
            lines.append("_Ninguna._")
        lines.append("")

        lines.append("## Errores de integridad")
        lines.append("")
        if self.integrity_errors:
            for item in self.integrity_errors:
                safe_id = _escape_markdown_cell(item["decision_id"])
                safe_error = _escape_markdown_cell(item["error"])
                lines.append(f"- **{safe_id}**: {safe_error}")
        else:
            lines.append("_Ninguno._")
        lines.append("")

        return "\n".join(lines)

    def _median_display(self) -> str:
        return "—" if self.median_days_to_close is None else f"{self.median_days_to_close:g}"


def build_status(project_root: Path, store_path: Path, *, as_of: str) -> StatusView:
    as_of_date = _parse_iso_date(as_of, "as_of")

    # Same sweep `check` runs — a decision with any finding here (filesystem
    # corruption, invalid header, Soho/PII in the source or in any of its
    # own recorded fields) is not trustworthy enough to publish normally.
    snapshot, findings = checks.collect_findings(project_root, store_path)
    finding_ids = {finding.decision_id for finding in findings}
    integrity_errors: list[IntegrityError] = [
        IntegrityError(decision_id=finding.decision_id, error=finding.problem) for finding in findings
    ]

    decisions_by_id = {decision.decision_id: decision for decision in snapshot.decisions}

    open_rows: list[dict] = []
    closed_rows: list[dict] = []
    successors: list[dict] = []
    close_durations_days: list[int] = []
    on_time_count = 0

    for decision in snapshot.decisions:
        if decision.decision_id in finding_ids:
            # Excluded from the normal tables — already represented in
            # integrity_errors above. Not verified, so not shown as normal.
            continue

        header, header_error = _read_header_safely(project_root, decision.source_document)
        if header_error is not None:
            # Defensive fallback: collect_findings() already validates the
            # header via the same source text, so this should not trigger
            # in practice — but if it ever does, fail closed here too
            # instead of silently falling back to scope=None.
            integrity_errors.append(IntegrityError(decision_id=decision.decision_id, error=header_error))
            continue
        scope = header.scope if header is not None else None

        # Careo round 3, finding #4b: resolve `supersedes` validity BEFORE
        # deciding which section this decision belongs to. Previously the
        # decision was appended to open_rows/closed_rows first and only
        # afterwards checked for a bad `supersedes` — so an invalid one
        # landed the decision in the normal table AND in integrity_errors
        # at the same time. Now an invalid `supersedes` routes it to
        # integrity_errors only, via `continue`, before either table (or
        # the timeliness/median bookkeeping below) ever sees it.
        supersedes_id: str | None = None
        supersedes_error: str | None = None
        if header is not None and header.supersedes is not None:
            supersedes_id = header.supersedes
            if supersedes_id == decision.decision_id:
                supersedes_error = f"supersedes se autorreferencia: {supersedes_id}"
            else:
                target = decisions_by_id.get(supersedes_id)
                valid_target = (
                    target is not None
                    and target.status == "CLOSED"
                    and target.review_decision == "ADJUST"
                    and supersedes_id not in finding_ids
                )
                if not valid_target:
                    supersedes_error = (
                        f"supersedes inválido: {supersedes_id!r} no existe en el almacén, "
                        "no está CLOSED con veredicto ADJUST, o tiene su propio error de integridad"
                    )

        if supersedes_error is not None:
            integrity_errors.append(IntegrityError(decision_id=decision.decision_id, error=supersedes_error))
            continue

        if decision.status == "OPEN":
            review_on_date = _parse_iso_date(decision.review_on, "review_on")
            bucket = _bucket_for(review_on_date, as_of_date)
            open_rows.append(
                {
                    "decision_id": decision.decision_id,
                    "title": decision.title,
                    "review_on": decision.review_on,
                    "bucket": bucket,
                    "scope": scope,
                    "friction_id": decision.friction_id,
                }
            )
        else:
            review_on_date = _parse_iso_date(decision.review_on, "review_on")
            closed_at_date = _parse_iso_date((decision.closed_at or "")[:10], "closed_at")
            created_at_date = _parse_iso_date(decision.created_at[:10], "created_at")
            deadline = _add_days(review_on_date, LATE_REVIEW_GRACE_DAYS)
            evaluated_on_time = closed_at_date <= deadline
            if evaluated_on_time:
                on_time_count += 1
            close_durations_days.append((closed_at_date - created_at_date).days)
            closed_rows.append(
                {
                    "decision_id": decision.decision_id,
                    "title": decision.title,
                    "review_decision": decision.review_decision,
                    "closed_at": decision.closed_at,
                    "evaluated_on_time": evaluated_on_time,
                    "scope": scope,
                    "friction_id": decision.friction_id,
                }
            )

        if supersedes_id is not None:
            # supersedes_error is None here (handled via `continue` above),
            # so this is a validated ADJUST successor.
            successors.append({"decision_id": decision.decision_id, "supersedes": supersedes_id})

    open_rows.sort(key=lambda item: (item["review_on"], item["decision_id"]))
    closed_rows.sort(key=lambda item: (item["closed_at"] or "", item["decision_id"]))
    successors.sort(key=lambda item: item["decision_id"])
    integrity_rows = tuple(
        sorted(
            (
                {"decision_id": item.decision_id, "error": item.error}
                for item in _dedupe_integrity_errors(integrity_errors)
            ),
            key=lambda item: (item["decision_id"], item["error"]),
        )
    )

    overdue = sum(1 for item in open_rows if item["bucket"] == "vencida")
    due_soon = sum(1 for item in open_rows if item["bucket"] == "próxima")
    adopt = sum(1 for item in closed_rows if item["review_decision"] == "ADOPT")
    adjust = sum(1 for item in closed_rows if item["review_decision"] == "ADJUST")
    discard = sum(1 for item in closed_rows if item["review_decision"] == "DISCARD")

    review_timeliness = {
        "evaluated_total": len(closed_rows),
        "evaluated_on_time": on_time_count,
        "evaluated_on_time_pct": (
            round(100 * on_time_count / len(closed_rows), 1) if closed_rows else None
        ),
    }
    median_days = statistics.median(close_durations_days) if close_durations_days else None

    counts = {
        "open_total": len(open_rows),
        "overdue": overdue,
        "due_soon": due_soon,
        "closed_total": len(closed_rows),
        "adopt": adopt,
        "adjust": adjust,
        "discard": discard,
    }

    return StatusView(
        as_of=as_of,
        counts=counts,
        review_timeliness=review_timeliness,
        median_days_to_close=median_days,
        open_decisions=tuple(open_rows),
        closed_decisions=tuple(closed_rows),
        successors=tuple(successors),
        integrity_errors=integrity_rows,
    )


def _dedupe_integrity_errors(items: list[IntegrityError]) -> list[IntegrityError]:
    seen: set[tuple[str, str]] = set()
    deduped: list[IntegrityError] = []
    for item in items:
        key = (item.decision_id, item.error)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _bucket_for(review_on: date, as_of: date) -> str:
    if review_on <= as_of:
        return "vencida"
    if review_on <= _add_days(as_of, DUE_SOON_WINDOW_DAYS):
        return "próxima"
    return "abierta"


def _add_days(value: date, days: int) -> date:
    return value + timedelta(days=days)


def _parse_iso_date(value: str, field: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{field} inválido: {value!r}") from error


def _read_header_safely(project_root: Path, source_document: str) -> tuple[object | None, str | None]:
    try:
        text = (project_root / source_document).read_text(encoding="utf-8")
    except OSError as error:
        return None, f"no se pudo leer source_document: {error}"
    try:
        return parse_context_header(text), None
    except InvalidContextHeader as error:
        return None, f"encabezado de contexto inválido: {error}"


def _format_ratio(review_timeliness: dict) -> str:
    total = review_timeliness["evaluated_total"]
    if total == 0:
        return "—"
    return f"{review_timeliness['evaluated_on_time']}/{total} ({review_timeliness['evaluated_on_time_pct']}%)"


_MARKDOWN_TABLE_UNSAFE = re.compile(r"[|\r\n\t\\`*_\[\]()<>]")
_MARKDOWN_TABLE_REPLACEMENTS = {
    "|": "\\|",
    "\r": " ",
    "\n": " ",
    "\t": " ",
    # Careo round 3 (final verification pass): the round-3 fix only escaped
    # table-structure characters (|, CR/LF/tab). A filesystem entry name is
    # untrusted and doesn't need real newlines to inject Markdown/HTML — e.g.
    # ``x**: [enlace](https://example.invalid)`` closes a bold span the
    # template opened and smuggles a link, entirely inline, no newline
    # required. Backslash is escaped first (via single-pass regex
    # substitution — the output is never re-scanned, so this can't cause
    # double-escaping) so an attacker can't pre-empt one of these escapes.
    "\\": "\\\\",
    "`": "\\`",
    "*": "\\*",
    "_": "\\_",
    "[": "\\[",
    "]": "\\]",
    "(": "\\(",
    ")": "\\)",
    "<": "\\<",
    ">": "\\>",
}


def _escape_markdown_cell(value: str) -> str:
    """Neutralize characters that would break a Markdown table row/line,
    smuggle extra rows/content into it, or open inline Markdown/HTML markup
    (careo round 1, finding #4b; extended in careo round 3, finding #3 to the
    ``decision_id``/``error`` of every integrity error too, then broadened
    again in the round-3 final verification pass after Codex showed the
    first extension still let ``*``/``[]``/``()``/``<>``/backtick through): a
    stray ``|`` would split into extra columns, a raw newline/tab would break
    out of the row/bullet entirely, and unescaped Markdown markup characters
    can open bold/link/HTML spans mid-cell without needing either of those.
    Used on any free text of untrusted origin, never just ``title``.
    """
    return _MARKDOWN_TABLE_UNSAFE.sub(lambda match: _MARKDOWN_TABLE_REPLACEMENTS[match.group(0)], value)
