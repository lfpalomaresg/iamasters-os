"""``capa2_decisions add`` — the only supported way to register a decision.

Careo round 1, finding #1: before this module existed, ``validate-source``
was only an optional pre-flight step — nothing stopped anyone (a human, a
script, a future loop) from skipping straight to
``python -m knowledge_ingest.decision_journal ... add``, so a source note
with a Soho/PII reference could enter the journal and only get caught later
by ``check``.

``add_decision`` closes that window by making validation an unconditional
first step of the *only* add path this adapter exposes: it reads the source
note, runs it through the exact same Capa 2 validation ``validate-source``
uses (context header + Soho filter + personal-data filter), computes its
hash, and only if all of that passes does it call through to the base
engine's own create-once ``DecisionJournal.add`` — which independently
re-applies its own personal-data checks on title/hypothesis/expected_outcome
and binds the hash. There is no gap between "validated" and "persisted":
if validation raises, nothing is written to the store at all.

Careo round 3, finding #1: ``validate_source_text`` only inspects
``source_document``'s own content — it never looked at ``title``,
``hypothesis``, or ``expected_outcome``, the three free-text fields passed
directly to this function by the caller. The base engine's own
``DecisionJournal.add`` re-checks those three for generic personal data
(email/phone/DNI/IBAN/address) via its ``_safe_text``, but it has no notion
of Soho at all — so a Soho reference placed only in ``title`` (never in the
source note) would sail straight through untouched. This function now runs
the same ``reject_soho_references`` check against all three before calling
the base engine, with the same fail-closed guarantee as the rest of it.

Careo round 3, finding #4a: a source note's optional ``supersedes: D-XXX``
header field used to be accepted at face value at add time — only
``views.build_status`` ever checked whether the referenced decision really
existed, was ``CLOSED``, and carried an ``ADJUST`` verdict, and only *after*
the bad record was already persisted. This function now runs that same
check before writing anything, so an invalid ``supersedes`` is rejected at
the door instead of merely being flagged later.

``validate-source`` remains available as a diagnostic-only command (dry run
against a note before you've decided on title/hypothesis/etc.), but it is no
longer part of the real add flow — this is.
"""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from . import engine_path
from .soho_filter import reject_soho_references
from .store import open_journal
from .validate import validate_source_text

engine_path.ensure_engine_importable()

from knowledge_ingest.decision_journal import (  # noqa: E402
    CorruptDecisionStore,
    Decision,
    DecisionJournal,
    InvalidDecision,
    InvalidDecisionTransition,
)


class InvalidSupersedes(ValueError):
    """Raised when a source note's ``supersedes`` header does not point to
    an existing decision that is ``CLOSED`` with ``review_decision ==
    "ADJUST"`` — or points at the decision being added itself. Mirrors the
    validity rule ``views.build_status`` enforces when rendering, but
    checked here, before anything is written, instead of only being
    surfaced afterwards as an integrity error.
    """


def add_decision(
    project_root: Path,
    store_path: Path,
    *,
    decision_id: str,
    title: str,
    source_document: str,
    friction_id: str,
    hypothesis: str,
    expected_outcome: str,
    review_on: str,
) -> Decision:
    """Validate ``source_document`` and, only if that passes, persist it.

    ``source_document`` is a path relative to ``project_root`` (e.g.
    ``knowledge/decisions/D-004-titulo.md``), matching what the base engine
    itself expects for ``Decision.source_document``.

    Raises ``SourceValidationError`` (from ``validate_source_text``) if the
    note fails the context-header/Soho/PII checks, ``SohoDataDetected`` if
    ``title``/``hypothesis``/``expected_outcome`` mention Soho, or
    ``InvalidSupersedes`` if the header's ``supersedes`` field doesn't point
    to a valid ADJUST-closed decision — all before anything touches the
    store. Raises whatever the base engine raises (``DuplicateDecision``,
    ``InvalidDecision``, ...) if the write itself is rejected.
    """
    source_path = project_root / source_document
    source_text = source_path.read_text(encoding="utf-8")

    # Fails closed: any validation error propagates and nothing is written.
    header = validate_source_text(source_text, label=source_document)

    # Careo round 3, finding #1: these three fields never go through
    # validate_source_text (which only looks at source_document's content),
    # so without this they would be persisted without ever being screened
    # for Soho references.
    reject_soho_references(title, field="title")
    reject_soho_references(hypothesis, field="hypothesis")
    reject_soho_references(expected_outcome, field="expected_outcome")

    source_hash = sha256(source_text.encode("utf-8")).hexdigest()

    journal = open_journal(project_root, store_path)

    # Careo round 3, finding #4a: validate `supersedes` against the real
    # state of the store before writing anything — not just at render time.
    if header.supersedes is not None:
        _validate_supersedes_target(journal, decision_id, header.supersedes)

    return journal.add(
        decision_id=decision_id,
        title=title,
        source_document=source_document,
        source_hash=source_hash,
        friction_id=friction_id,
        hypothesis=hypothesis,
        expected_outcome=expected_outcome,
        review_on=review_on,
    )


def _validate_supersedes_target(journal: DecisionJournal, decision_id: str, supersedes_id: str) -> None:
    """Fails closed: raises ``InvalidSupersedes`` unless ``supersedes_id``
    names a different, already-persisted decision that is ``CLOSED`` with
    ``review_decision == "ADJUST"``.
    """
    if supersedes_id == decision_id:
        raise InvalidSupersedes(f"supersedes se autorreferencia: {supersedes_id!r}")
    try:
        target = journal.get(supersedes_id)
    except (InvalidDecisionTransition, CorruptDecisionStore, InvalidDecision) as error:
        raise InvalidSupersedes(
            f"supersedes inválido: {supersedes_id!r} no se pudo leer del almacén ({error})"
        ) from error
    if target.status != "CLOSED" or target.review_decision != "ADJUST":
        raise InvalidSupersedes(
            f"supersedes inválido: {supersedes_id!r} existe pero no está CLOSED con veredicto ADJUST "
            f"(status={target.status!r}, review_decision={target.review_decision!r})"
        )
