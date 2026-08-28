"""Makes ``knowledge_ingest`` importable without vendoring or copying it.

The decision journal engine (``knowledge_ingest.decision_journal``) lives in a
separate, private repository (``~/MAIN_PROYECTOS/knowledge-ingest``). FR-053's
design explicitly forbids copying or reimplementing its logic, so this module
resolves the engine's ``src`` directory at runtime and inserts it into
``sys.path`` on first use — the same effect as an editable/path dependency,
without requiring network access or a Python packaging setup that neither
this project's brief folder nor the ``iamasters-os`` repo has.

Resolution order:

1. ``$CAPA2_KNOWLEDGE_INGEST_SRC`` if set (an absolute path to
   ``knowledge-ingest/src``) — use this on any machine where the repo lives
   somewhere other than the default below (e.g. a future HP clone).
2. The default Mac location, ``~/MAIN_PROYECTOS/knowledge-ingest/src``.

Never guesses beyond that: failing loudly beats silently importing the wrong
copy of a security-sensitive module. Two extra provenance checks close a gap
found in careo round 1 (finding #5):

- the marker file (``knowledge_ingest/decision_journal.py``) itself must not
  be a symlink — a candidate whose marker is a symlink is treated the same
  as a candidate that doesn't have it at all;
- after ``sys.path`` insertion, the module actually imported is verified to
  resolve under the candidate directory we picked. This also catches the
  case where ``knowledge_ingest`` was already present in ``sys.modules``
  from a *different* path (e.g. some other tool imported it first) — Python
  would otherwise silently hand back that stale module instead of the one
  this adapter just resolved.
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

ENV_VAR = "CAPA2_KNOWLEDGE_INGEST_SRC"
_DEFAULT_CANDIDATES = (Path("~/MAIN_PROYECTOS/knowledge-ingest/src").expanduser(),)
_MARKER = Path("knowledge_ingest") / "decision_journal.py"
_TARGET_MODULE = "knowledge_ingest.decision_journal"


class EngineNotFound(RuntimeError):
    """Raised when the knowledge_ingest engine cannot be located."""


class EngineProvenanceError(RuntimeError):
    """Raised when the imported ``knowledge_ingest`` module does not
    actually come from the resolved candidate directory."""


def _has_valid_marker(candidate: Path) -> bool:
    """True only if the marker exists as a real file, not a symlink.

    Uses ``is_symlink()`` (an ``lstat``, never follows the link) before
    ``is_file()`` so a symlinked marker — pointing anywhere, even to a
    legitimate-looking file — is rejected outright rather than silently
    trusted.
    """
    marker_path = candidate / _MARKER
    return not marker_path.is_symlink() and marker_path.is_file()


def ensure_engine_importable() -> Path:
    """Insert the engine's ``src`` dir into ``sys.path``, import the target
    module, and verify its provenance.

    Returns the resolved directory that was used. Safe to call repeatedly
    (idempotent) — every call re-verifies provenance instead of trusting a
    previous call's result blindly, so a later stale ``sys.modules`` entry
    from elsewhere is still caught.
    """
    override = os.environ.get(ENV_VAR)
    candidates = [Path(override).expanduser()] if override else list(_DEFAULT_CANDIDATES)

    chosen: Path | None = None
    for candidate in candidates:
        if _has_valid_marker(candidate):
            chosen = candidate
            break

    if chosen is None:
        tried = ", ".join(str(candidate) for candidate in candidates)
        raise EngineNotFound(
            "no se encuentra knowledge_ingest.decision_journal (probado: "
            f"{tried}; se rechaza si el marcador es un symlink). Define "
            f"{ENV_VAR}=/ruta/a/knowledge-ingest/src o clona knowledge-ingest "
            "en la ruta por defecto."
        )

    resolved_candidate = chosen.resolve()
    candidate_str = str(chosen)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

    module = importlib.import_module(_TARGET_MODULE)
    module_file = getattr(module, "__file__", None)
    if not module_file:
        raise EngineProvenanceError(
            f"{_TARGET_MODULE} se importó sin __file__ (¿paquete espejo o namespace package?); "
            "no se puede verificar su procedencia."
        )
    module_path = Path(module_file).resolve()
    if not module_path.is_relative_to(resolved_candidate):
        raise EngineProvenanceError(
            f"{_TARGET_MODULE} importado no coincide con el candidato esperado: "
            f"importado de {module_path}, candidato resuelto {resolved_candidate}. "
            "Puede que ya estuviera cargado en sys.modules desde otra ruta, o que el "
            "marcador fuera un enlace simbólico que apuntaba a otro sitio."
        )

    return resolved_candidate
