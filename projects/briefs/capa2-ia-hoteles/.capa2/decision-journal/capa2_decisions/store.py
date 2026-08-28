"""Read-only helpers around a ``DecisionJournal`` store.

The base engine exposes no "list all decisions" API (only ``due()``, which
filters to OPEN + overdue). Enumerating every decision_id that exists is a
filesystem read done here, in the adapter — it does not touch the engine's
write path, does not bypass any of its validation, and every record found is
still read back through ``DecisionJournal.get()``, which re-verifies the
source binding (hash + safe path) before trusting it.

This module also runs a *loud* filesystem-level integrity sweep
(``scan_store_integrity``) over ``decisions/`` and ``closures/``: careo
round 1, finding #2 established that the previous enumeration silently
skipped symlinks, non-``.json`` files, and unrecognized names — and never
looked at ``closures/`` at all. Anything that sweep finds is surfaced as an
``IntegrityError`` through ``read_all_decisions``/``StoreSnapshot`` instead
of being dropped on the floor.

Careo round 3, finding #2: that sweep checked whether ``decisions/`` and
``closures/`` *themselves* were symlinks, but never checked the store root
itself — ``project_root / store_path`` (e.g. ``.capa2/decision-journal``).
``Path.is_symlink()`` only inspects the final path component, so a symlinked
store root whose target directory happens to contain real ``decisions/``
and ``closures/`` subdirectories sailed straight through: every check below
it (``decisions_dir.is_symlink()`` included) would pass cleanly, because
none of *those* path components are themselves symlinks — only their parent
is. An attacker (or a botched deploy) swapping the whole store for an empty
external directory this way used to make ``check`` report OK with zero
decisions instead of flagging that the store had been substituted.
``scan_store_integrity`` now checks the store root first, before descending
into either subdirectory, and treats a symlinked root as maximally
suspicious: it short-circuits and reports only that single, unmissable
error instead of mixing it in as one finding among many.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from . import engine_path

engine_path.ensure_engine_importable()

from knowledge_ingest.decision_journal import (  # noqa: E402
    CorruptDecisionStore,
    Decision,
    DecisionJournal,
    InvalidDecisionTransition,
)

_DECISION_ID_PATTERN = re.compile(r"^D-[0-9]{3,6}$")


@dataclass(frozen=True)
class IntegrityError:
    decision_id: str
    error: str


@dataclass(frozen=True)
class StoreSnapshot:
    """All decisions the store currently holds, read back safely."""

    decisions: tuple[Decision, ...]
    integrity_errors: tuple[IntegrityError, ...]


def open_journal(project_root: Path, store_path: Path) -> DecisionJournal:
    return DecisionJournal(store_path, project_root=project_root)


def list_decision_ids(project_root: Path, store_path: Path) -> tuple[str, ...]:
    """Filesystem-level enumeration only — no trust placed in these names yet.

    Deliberately permissive/best-effort: this only decides which ids are
    worth attempting to read through the trusted engine. Anything it skips
    (symlinks, non-``.json`` files, unrecognized names) is still reported
    loudly by ``scan_store_integrity`` — it is not silently dropped from the
    system as a whole, only from this particular "what can I try to read"
    list.
    """
    decisions_dir = project_root / store_path / "decisions"
    if decisions_dir.is_symlink() or not decisions_dir.is_dir():
        return ()
    ids = []
    for entry in sorted(decisions_dir.iterdir()):
        if entry.is_symlink() or not entry.is_file():
            continue
        if entry.suffix != ".json":
            continue
        stem = entry.stem
        if _DECISION_ID_PATTERN.fullmatch(stem):
            ids.append(stem)
    return tuple(sorted(ids))


def _scan_entries(directory: Path, *, kind: str) -> tuple[list[str], list[IntegrityError]]:
    """Scan one flat directory of ``*.json`` records, failing closed.

    Returns ``(valid_ids, integrity_errors)``. Nothing is skipped silently:
    a symlinked directory, a symlinked entry, a non-``.json`` file, a
    subdirectory, or a name that doesn't match the decision-id pattern are
    all reported as errors instead of being quietly ignored.
    """
    valid_ids: list[str] = []
    errors: list[IntegrityError] = []

    if directory.is_symlink():
        errors.append(
            IntegrityError(decision_id=directory.name, error=f"{kind}/ es un symlink, no un directorio real")
        )
        return valid_ids, errors
    if not directory.exists():
        return valid_ids, errors
    if not directory.is_dir():
        errors.append(IntegrityError(decision_id=directory.name, error=f"{kind}/ no es un directorio"))
        return valid_ids, errors

    for entry in sorted(directory.iterdir()):
        if entry.is_symlink():
            errors.append(
                IntegrityError(
                    decision_id=entry.name,
                    error=f"entrada symlink no permitida en {kind}/: {entry.name}",
                )
            )
            continue
        if entry.is_dir():
            errors.append(
                IntegrityError(
                    decision_id=entry.name,
                    error=f"subdirectorio inesperado en {kind}/: {entry.name}",
                )
            )
            continue
        if entry.suffix != ".json":
            errors.append(
                IntegrityError(
                    decision_id=entry.name,
                    error=f"extensión no permitida en {kind}/: {entry.name}",
                )
            )
            continue
        stem = entry.stem
        if not _DECISION_ID_PATTERN.fullmatch(stem):
            errors.append(
                IntegrityError(
                    decision_id=entry.name,
                    error=f"nombre no reconocido como decision_id en {kind}/: {entry.name}",
                )
            )
            continue
        valid_ids.append(stem)

    return valid_ids, errors


def _check_store_root_not_symlink(store_root: Path, *, label: str) -> IntegrityError | None:
    """``lstat``-based check (never follows the link) — the store root's
    identity as "a real directory" is the foundation every other check in
    this module assumes. Returns an ``IntegrityError`` only if it is a
    symlink; ``None`` otherwise (including when it simply doesn't exist yet,
    which is not suspicious by itself).
    """
    if store_root.is_symlink():
        return IntegrityError(
            decision_id="<raíz del almacén>",
            error=(
                f"CRÍTICO: la raíz del almacén ({label}) es un symlink, no un directorio real — "
                "todo el almacén es sospechoso, no se ha comprobado nada más debajo de él."
            ),
        )
    return None


def scan_store_integrity(project_root: Path, store_path: Path) -> tuple[IntegrityError, ...]:
    """Filesystem-level integrity sweep over the store root, ``decisions/``,
    and ``closures/``.

    Covers what ``list_decision_ids`` deliberately does not police: this is
    meant to be loud, not silent (careo round 1, finding #2). In addition to
    per-entry problems in both directories, it flags closures that don't
    correspond to any known decision (orphans) — ``closures/`` was
    previously never enumerated at all.

    The store root itself (``project_root / store_path``) is checked first
    (careo round 3, finding #2): if it is a symlink, nothing beneath it can
    be trusted either, so this returns immediately with just that one
    critical finding instead of also scanning — and implicitly vouching for
    — whatever real ``decisions/``/``closures/`` happen to sit on the other
    side of it.
    """
    store_root = project_root / store_path
    root_error = _check_store_root_not_symlink(store_root, label=str(store_path))
    if root_error is not None:
        return (root_error,)

    decisions_dir = store_root / "decisions"
    closures_dir = store_root / "closures"

    decision_ids, decision_errors = _scan_entries(decisions_dir, kind="decisions")
    closure_ids, closure_errors = _scan_entries(closures_dir, kind="closures")

    known_decision_ids = set(decision_ids)
    orphan_errors = [
        IntegrityError(
            decision_id=closure_id,
            error=f"closure huérfano: no existe decisions/{closure_id}.json",
        )
        for closure_id in closure_ids
        if closure_id not in known_decision_ids
    ]

    return tuple(decision_errors + closure_errors + orphan_errors)


def read_all_decisions(project_root: Path, store_path: Path) -> StoreSnapshot:
    """Read every decision through the trusted engine, collecting failures.

    A single corrupt or tampered record does not stop the whole read: it is
    reported as an integrity error so ``status``/``check`` can surface it,
    instead of the entire view failing closed because of one bad file. The
    filesystem-level sweep (``scan_store_integrity``) runs first so its
    findings are always part of the result, even for entries the trusted
    engine never gets a chance to look at (symlinks, orphaned closures...).
    """
    journal = open_journal(project_root, store_path)
    decisions: list[Decision] = []
    errors: list[IntegrityError] = list(scan_store_integrity(project_root, store_path))
    for decision_id in list_decision_ids(project_root, store_path):
        try:
            decisions.append(journal.get(decision_id))
        except (CorruptDecisionStore, InvalidDecisionTransition, OSError, ValueError) as error:
            errors.append(IntegrityError(decision_id=decision_id, error=str(error)))
    return StoreSnapshot(decisions=tuple(decisions), integrity_errors=tuple(errors))
