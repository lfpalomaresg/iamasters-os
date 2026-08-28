"""``capa2_decisions check`` — read-only integrity sweep (FR-053 design, section 9).

For every decision currently on record this re-verifies:

1. the record itself reads back cleanly through the trusted engine (hash
   binding to its source still matches, JSON is canonical, closure — if any
   — is consistent);
2. the store's own filesystem shape is sane: no symlinked entries, no
   stray non-``.json`` files, no orphaned or malformed closures (see
   ``store.scan_store_integrity``);
3. its source note's Capa 2 context header still parses and validates;
4. its source note still contains no Soho references or personal data, and
   neither do the decision's own recorded title/hypothesis/expected_outcome
   **nor its closure's actual_outcome, when the decision is closed**
   (defense in depth: the base engine already blocks personal data in all
   four fields — including actual_outcome — at write time via its own
   ``_safe_text``, this re-checks it at read time too. Soho is different:
   the base engine has no notion of it at all, in any field, at any time —
   ``check`` re-scanning actual_outcome for Soho references is the only
   place that ever happens).

Never writes anything. A clean run means the whole store is safe to trust for
producing ``status``, or for handing to the content loop.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .personal_data import PersonalDataDetected, reject_personal_data
from .soho_filter import SohoDataDetected, reject_soho_references
from .store import StoreSnapshot, read_all_decisions
from .validate import SourceValidationError, validate_source_text


@dataclass(frozen=True)
class CheckFinding:
    decision_id: str
    problem: str


@dataclass(frozen=True)
class CheckReport:
    decisions_checked: int
    findings: tuple[CheckFinding, ...]

    @property
    def ok(self) -> bool:
        return not self.findings

    def render(self) -> str:
        lines = [f"capa2_decisions check — {self.decisions_checked} decisiones revisadas"]
        if self.ok:
            lines.append("OK: sin errores de integridad ni contenido inseguro.")
        else:
            lines.append(f"FALLO: {len(self.findings)} problema(s) encontrado(s).")
            for finding in self.findings:
                lines.append(f"  - {finding.decision_id}: {finding.problem}")
        return "\n".join(lines) + "\n"


def collect_findings(project_root: Path, store_path: Path) -> tuple[StoreSnapshot, tuple[CheckFinding, ...]]:
    """Run the full integrity sweep and return both the raw snapshot and the
    findings derived from it.

    Split out from ``run_check`` so other read-only views (``views.build_status``)
    can reuse exactly the same sweep instead of re-implementing a weaker
    version of it (careo round 1, finding #4: ``status`` used to publish
    without running these filters at all).
    """
    snapshot = read_all_decisions(project_root, store_path)
    findings: list[CheckFinding] = [
        CheckFinding(decision_id=item.decision_id, problem=item.error) for item in snapshot.integrity_errors
    ]

    for decision in snapshot.decisions:
        source_path = project_root / decision.source_document
        try:
            source_text = source_path.read_text(encoding="utf-8")
        except OSError as error:
            findings.append(CheckFinding(decision.decision_id, f"no se pudo leer la fuente: {error}"))
            continue

        try:
            validate_source_text(source_text, label=decision.source_document)
        except SourceValidationError as error:
            findings.append(CheckFinding(decision.decision_id, str(error)))

        fields_to_scan = [
            ("title", decision.title),
            ("hypothesis", decision.hypothesis),
            ("expected_outcome", decision.expected_outcome),
        ]
        # actual_outcome only exists once the decision is CLOSED. The base
        # engine's close() already blocks personal data in it (same
        # _safe_text as the other three fields); it has no notion of Soho
        # at all, so this is the only place actual_outcome ever gets
        # scanned for that.
        if decision.actual_outcome is not None:
            fields_to_scan.append(("actual_outcome", decision.actual_outcome))

        for field_name, field_value in fields_to_scan:
            try:
                reject_soho_references(field_value, field=field_name)
                reject_personal_data(field_value, field=field_name)
            except (SohoDataDetected, PersonalDataDetected) as error:
                findings.append(CheckFinding(decision.decision_id, str(error)))

    return snapshot, tuple(findings)


def run_check(project_root: Path, store_path: Path) -> CheckReport:
    snapshot, findings = collect_findings(project_root, store_path)
    return CheckReport(
        decisions_checked=len(snapshot.decisions) + len(snapshot.integrity_errors),
        findings=findings,
    )
