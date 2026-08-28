"""Tests for the capa2_decisions adapter (FR-053).

These do NOT re-prove the base engine's own invariants (atomic create-once,
symlink/path-traversal rejection, hash binding) — that suite lives in
knowledge-ingest's own ``tests/test_decision_journal.py`` and already passes
independently. These tests cover only what this adapter actually adds:
context-header validation, the Soho filter, the derived view, and the
read-only integrity sweep — including their behaviour against the base
engine when used together.
"""

from __future__ import annotations

import contextlib
import io
import os
import re
import subprocess
import sys
import tempfile
import types
import unittest
from hashlib import sha256
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]  # .capa2/decision-journal/
sys.path.insert(0, str(APP_ROOT))

from capa2_decisions import add as add_module  # noqa: E402
from capa2_decisions import checks, engine_path, store, views  # noqa: E402
from capa2_decisions.__main__ import main as cli_main  # noqa: E402
from capa2_decisions.add import InvalidSupersedes  # noqa: E402
from capa2_decisions.context import InvalidContextHeader, parse_context_header  # noqa: E402
from capa2_decisions.personal_data import PersonalDataDetected, reject_personal_data  # noqa: E402
from capa2_decisions.soho_filter import SohoDataDetected, reject_soho_references  # noqa: E402
from capa2_decisions.validate import SourceValidationError, validate_source_text  # noqa: E402

engine_path.ensure_engine_importable()
from knowledge_ingest.decision_journal import DecisionJournal  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"
STORE_PATH = Path(".capa2/decision-journal")


def _read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class ContextHeaderTests(unittest.TestCase):
    def test_parses_valid_header(self):
        header = parse_context_header(_read_fixture("valid_source.md"))
        self.assertEqual(header.scope, "content")
        self.assertEqual(header.content_ids, ("S9",))
        self.assertEqual(header.metric_code, "engagement_rate")
        self.assertEqual(header.owner, "luisfran")
        self.assertIsNone(header.supersedes)

    def test_rejects_invalid_scope(self):
        with self.assertRaises(InvalidContextHeader):
            parse_context_header(_read_fixture("invalid_header_source.md"))

    def test_rejects_missing_required_field(self):
        text = "---\nscope: content\nowner: luisfran\n---\nbody\n"
        with self.assertRaises(InvalidContextHeader):
            parse_context_header(text)

    def test_rejects_unknown_field(self):
        text = (
            "---\nscope: content\ncontent_ids: []\nmetric_code: x_y\n"
            'baseline: "b"\ntarget: "t"\nowner: luisfran\nrogue: 1\n---\nbody\n'
        )
        with self.assertRaises(InvalidContextHeader):
            parse_context_header(text)

    def test_accepts_optional_supersedes(self):
        text = (
            "---\nscope: content\ncontent_ids: []\nmetric_code: x_y\n"
            'baseline: "b"\ntarget: "t"\nowner: luisfran\nsupersedes: D-001\n---\nbody\n'
        )
        header = parse_context_header(text)
        self.assertEqual(header.supersedes, "D-001")

    def test_owner_must_be_luisfran(self):
        text = (
            "---\nscope: content\ncontent_ids: []\nmetric_code: x_y\n"
            'baseline: "b"\ntarget: "t"\nowner: someone_else\n---\nbody\n'
        )
        with self.assertRaises(InvalidContextHeader):
            parse_context_header(text)


class SohoFilterTests(unittest.TestCase):
    def test_rejects_soho_mention(self):
        with self.assertRaises(SohoDataDetected):
            reject_soho_references(_read_fixture("sensitive_soho_source.md"), field="source")

    def test_allows_blindbeds_mention(self):
        # Blindbeds is Luisfran's own public product, not internal Soho data.
        reject_soho_references("Se nombra Blindbeds Supply en el post.", field="source")

    def test_allows_clean_text(self):
        reject_soho_references(_read_fixture("valid_source.md"), field="source")


class PersonalDataFilterTests(unittest.TestCase):
    def test_rejects_email(self):
        with self.assertRaises(PersonalDataDetected):
            reject_personal_data(_read_fixture("sensitive_pii_source.md"), field="source")

    def test_allows_clean_text(self):
        reject_personal_data(_read_fixture("valid_source.md"), field="source")


class ValidateSourceTests(unittest.TestCase):
    def test_valid_source_passes(self):
        header = validate_source_text(_read_fixture("valid_source.md"), label="valid_source.md")
        self.assertEqual(header.scope, "content")

    def test_soho_source_fails_closed(self):
        with self.assertRaises(SourceValidationError):
            validate_source_text(_read_fixture("sensitive_soho_source.md"), label="soho")

    def test_pii_source_fails_closed(self):
        with self.assertRaises(SourceValidationError):
            validate_source_text(_read_fixture("sensitive_pii_source.md"), label="pii")

    def test_invalid_header_fails_closed(self):
        with self.assertRaises(SourceValidationError):
            validate_source_text(_read_fixture("invalid_header_source.md"), label="bad-header")


class _ProjectFixture:
    """A throwaway project tree shaped like the real capa2-ia-hoteles brief."""

    def __init__(self, tmp_path: Path):
        self.root = tmp_path
        (self.root / "knowledge" / "decisions").mkdir(parents=True)

    def write_source(self, name: str, text: str) -> tuple[str, str]:
        relative = f"knowledge/decisions/{name}"
        (self.root / relative).write_text(text, encoding="utf-8")
        digest = sha256(text.encode("utf-8")).hexdigest()
        return relative, digest

    def journal(self) -> DecisionJournal:
        return store.open_journal(self.root, STORE_PATH)


class StoreAndChecksTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = _ProjectFixture(Path(self.tmp.name).resolve())

    def tearDown(self):
        self.tmp.cleanup()

    def _add(self, decision_id: str, source_name: str, source_text: str, **overrides):
        relative, digest = self.project.write_source(source_name, source_text)
        journal = self.project.journal()
        params = dict(
            decision_id=decision_id,
            title="Título de prueba",
            source_document=relative,
            source_hash=digest,
            friction_id="FR-053",
            hypothesis="Hipótesis de prueba suficientemente larga.",
            expected_outcome="Resultado esperado de prueba.",
            review_on="2026-09-30",
        )
        params.update(overrides)
        return journal.add(**params)

    def test_duplicate_add_does_not_create_a_second_record(self):
        text = _read_fixture("valid_source.md")
        self._add("D-001", "d1.md", text)
        journal = self.project.journal()
        source_relative = "knowledge/decisions/d1.md"
        digest = sha256(text.encode("utf-8")).hexdigest()
        with self.assertRaises(Exception):
            journal.add(
                decision_id="D-001",
                title="Título de prueba",
                source_document=source_relative,
                source_hash=digest,
                friction_id="FR-053",
                hypothesis="Hipótesis de prueba suficientemente larga.",
                expected_outcome="Resultado esperado de prueba.",
                review_on="2026-09-30",
            )
        ids = store.list_decision_ids(self.project.root, STORE_PATH)
        self.assertEqual(ids, ("D-001",))

    def test_same_id_different_content_fails_without_altering_original(self):
        text = _read_fixture("valid_source.md")
        self._add("D-001", "d1.md", text)
        original = self.project.journal().get("D-001")
        with self.assertRaises(Exception):
            self._add("D-001", "d1.md", text, title="Un título distinto")
        unchanged = self.project.journal().get("D-001")
        self.assertEqual(unchanged, original)

    def test_tampered_source_is_reported_without_crashing_the_whole_sweep(self):
        text = _read_fixture("valid_source.md")
        self._add("D-001", "d1.md", text)
        self._add("D-002", "d2.md", text.replace("S9", "S10"))
        # Tamper D-001's source after the fact.
        (self.project.root / "knowledge/decisions/d1.md").write_text(text + "\nextra\n", encoding="utf-8")

        snapshot = store.read_all_decisions(self.project.root, STORE_PATH)
        self.assertEqual({d.decision_id for d in snapshot.decisions}, {"D-002"})
        self.assertEqual(len(snapshot.integrity_errors), 1)
        self.assertEqual(snapshot.integrity_errors[0].decision_id, "D-001")

        report = checks.run_check(self.project.root, STORE_PATH)
        self.assertFalse(report.ok)
        self.assertTrue(any(f.decision_id == "D-001" for f in report.findings))

    def test_check_flags_soho_reference_left_in_a_stored_source(self):
        # The recommended workflow is validate-source THEN add; this proves
        # check() still catches it even if someone skipped that step.
        text = _read_fixture("sensitive_soho_source.md")
        self._add("D-001", "d1.md", text)
        report = checks.run_check(self.project.root, STORE_PATH)
        self.assertFalse(report.ok)
        self.assertTrue(any(f.decision_id == "D-001" for f in report.findings))

    def test_check_clean_store_passes(self):
        self._add("D-001", "d1.md", _read_fixture("valid_source.md"))
        report = checks.run_check(self.project.root, STORE_PATH)
        self.assertTrue(report.ok)
        self.assertEqual(report.decisions_checked, 1)


class BuildStatusTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = _ProjectFixture(Path(self.tmp.name).resolve())

    def tearDown(self):
        self.tmp.cleanup()

    def _add(self, decision_id, review_on, source_name="src.md"):
        text = _read_fixture("valid_source.md").replace("2026-09-30", review_on)
        # Keep source_hash consistent with the mutated text.
        name = f"{decision_id}-{source_name}"
        relative, digest = self.project.write_source(name, text)
        journal = self.project.journal()
        return journal.add(
            decision_id=decision_id,
            title=f"Decisión {decision_id}",
            source_document=relative,
            source_hash=digest,
            friction_id="FR-053",
            hypothesis="Hipótesis suficientemente larga para pasar validación.",
            expected_outcome="Resultado esperado de prueba suficientemente largo.",
            review_on=review_on,
        )

    def test_overdue_due_soon_and_open_buckets(self):
        self._add("D-001", "2026-08-01")  # overdue relative to as_of below
        self._add("D-002", "2026-08-31")  # due soon (within 7 days)
        self._add("D-003", "2027-01-01")  # far in the future
        view = views.build_status(self.project.root, STORE_PATH, as_of="2026-08-28")
        buckets = {row["decision_id"]: row["bucket"] for row in view.open_decisions}
        self.assertEqual(buckets["D-001"], "vencida")
        self.assertEqual(buckets["D-002"], "próxima")
        self.assertEqual(buckets["D-003"], "abierta")
        self.assertEqual(view.counts["overdue"], 1)
        self.assertEqual(view.counts["due_soon"], 1)
        self.assertEqual(view.counts["open_total"], 3)

    def test_status_is_deterministic_and_idempotent(self):
        self._add("D-001", "2026-08-01")
        self._add("D-002", "2027-01-01")
        first = views.build_status(self.project.root, STORE_PATH, as_of="2026-08-28")
        second = views.build_status(self.project.root, STORE_PATH, as_of="2026-08-28")
        self.assertEqual(first.to_json(), second.to_json())
        self.assertEqual(first.to_markdown(), second.to_markdown())

    def test_closed_decisions_and_timeliness(self):
        # review_on close to "today" so closing it today lands within the
        # review_on + 7 days grace window used for the timeliness metric.
        self._add("D-001", "2026-08-25")
        journal = self.project.journal()
        journal.close("D-001", actual_outcome="Resultado observado de prueba.", review_decision="ADOPT")
        view = views.build_status(self.project.root, STORE_PATH, as_of="2026-08-28")
        self.assertEqual(view.counts["closed_total"], 1)
        self.assertEqual(view.counts["adopt"], 1)
        self.assertEqual(view.review_timeliness["evaluated_total"], 1)
        # closed the same day it's generated -> well within review_on+7d.
        self.assertEqual(view.review_timeliness["evaluated_on_time"], 1)
        self.assertIsNotNone(view.median_days_to_close)

    def test_successor_detection_from_supersedes_header(self):
        original_text = _read_fixture("valid_source.md")
        relative, digest = self.project.write_source("d-orig.md", original_text)
        journal = self.project.journal()
        journal.add(
            decision_id="D-001",
            title="Original",
            source_document=relative,
            source_hash=digest,
            friction_id="FR-053",
            hypothesis="Hipótesis suficientemente larga para pasar validación.",
            expected_outcome="Resultado esperado de prueba suficientemente largo.",
            review_on="2026-09-30",
        )
        journal.close("D-001", actual_outcome="No funcionó como se esperaba.", review_decision="ADJUST")

        successor_text = original_text.replace(
            "owner: luisfran\n---", "owner: luisfran\nsupersedes: D-001\n---"
        )
        relative2, digest2 = self.project.write_source("d-successor.md", successor_text)
        journal.add(
            decision_id="D-002",
            title="Ajustada",
            source_document=relative2,
            source_hash=digest2,
            friction_id="FR-053",
            hypothesis="Hipótesis ajustada tras el cierre de D-001.",
            expected_outcome="Resultado esperado ajustado de prueba.",
            review_on="2026-10-15",
        )

        view = views.build_status(self.project.root, STORE_PATH, as_of="2026-08-28")
        self.assertEqual(view.successors, ({"decision_id": "D-002", "supersedes": "D-001"},))


class LoopIsolationGuardTests(unittest.TestCase):
    """Static guard: no CODE in this package ever touches content-log.md.

    Documentation is allowed to name the file when explaining that it is
    off-limits (this module's own docstrings do); what must never appear is
    the filename inside an executable line.
    """

    _DOCSTRING_PATTERN = re.compile(r'""".*?"""|\'\'\'.*?\'\'\'', re.DOTALL)
    _COMMENT_PATTERN = re.compile(r"#.*")

    def test_no_code_line_mentions_content_log(self):
        package_dir = APP_ROOT / "capa2_decisions"
        offenders = []
        for path in package_dir.glob("*.py"):
            text = path.read_text(encoding="utf-8")
            code_only = self._DOCSTRING_PATTERN.sub("", text)
            code_only = self._COMMENT_PATTERN.sub("", code_only)
            if "content-log" in code_only.lower():
                offenders.append(path.name)
        self.assertEqual(offenders, [])


class AddCommandTests(unittest.TestCase):
    """Careo round 1, finding #1: `add` is the only supported entrypoint and
    the source is validated before anything is persisted — no window to
    skip straight to the base engine.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = _ProjectFixture(Path(self.tmp.name).resolve())

    def tearDown(self):
        self.tmp.cleanup()

    def _add_kwargs(self, relative: str, **overrides) -> dict:
        params = dict(
            decision_id="D-001",
            title="Título de prueba",
            source_document=relative,
            friction_id="FR-053",
            hypothesis="Hipótesis de prueba suficientemente larga.",
            expected_outcome="Resultado esperado de prueba.",
            review_on="2026-09-30",
        )
        params.update(overrides)
        return params

    def test_add_decision_rejects_soho_source_and_persists_nothing(self):
        relative, _ = self.project.write_source("d1.md", _read_fixture("sensitive_soho_source.md"))
        with self.assertRaises(SourceValidationError):
            add_module.add_decision(self.project.root, STORE_PATH, **self._add_kwargs(relative))
        # Nothing was written to the store at all — no gap between "would
        # have been rejected" and "already on disk".
        self.assertEqual(store.list_decision_ids(self.project.root, STORE_PATH), ())
        decisions_dir = self.project.root / STORE_PATH / "decisions"
        self.assertFalse(decisions_dir.exists() and any(decisions_dir.iterdir()))

    def test_add_decision_rejects_pii_source_and_persists_nothing(self):
        relative, _ = self.project.write_source("d1.md", _read_fixture("sensitive_pii_source.md"))
        with self.assertRaises(SourceValidationError):
            add_module.add_decision(self.project.root, STORE_PATH, **self._add_kwargs(relative))
        self.assertEqual(store.list_decision_ids(self.project.root, STORE_PATH), ())

    def test_add_decision_valid_source_persists_via_base_engine(self):
        relative, _ = self.project.write_source("d1.md", _read_fixture("valid_source.md"))
        decision = add_module.add_decision(self.project.root, STORE_PATH, **self._add_kwargs(relative))
        self.assertEqual(decision.decision_id, "D-001")
        self.assertEqual(decision.status, "OPEN")
        self.assertEqual(store.list_decision_ids(self.project.root, STORE_PATH), ("D-001",))

    def test_cli_add_command_rejects_soho_source_and_writes_nothing(self):
        relative, _ = self.project.write_source("d1.md", _read_fixture("sensitive_soho_source.md"))
        argv = [
            "--project-root", str(self.project.root),
            "--store", str(STORE_PATH),
            "add",
            "--id", "D-001",
            "--title", "Título de prueba",
            "--source-document", relative,
            "--friction", "FR-053",
            "--hypothesis", "Hipótesis de prueba suficientemente larga.",
            "--expected-outcome", "Resultado esperado de prueba.",
            "--review-on", "2026-09-30",
        ]
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            exit_code = cli_main(argv)
        self.assertEqual(exit_code, 1)
        self.assertEqual(store.list_decision_ids(self.project.root, STORE_PATH), ())

    def test_cli_add_command_valid_source_persists(self):
        relative, _ = self.project.write_source("d1.md", _read_fixture("valid_source.md"))
        argv = [
            "--project-root", str(self.project.root),
            "--store", str(STORE_PATH),
            "add",
            "--id", "D-001",
            "--title", "Título de prueba",
            "--source-document", relative,
            "--friction", "FR-053",
            "--hypothesis", "Hipótesis de prueba suficientemente larga.",
            "--expected-outcome", "Resultado esperado de prueba.",
            "--review-on", "2026-09-30",
        ]
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            exit_code = cli_main(argv)
        self.assertEqual(exit_code, 0)
        self.assertEqual(store.list_decision_ids(self.project.root, STORE_PATH), ("D-001",))


class FilesystemIntegritySweepTests(unittest.TestCase):
    """Careo round 1, finding #2: `check` must not silently skip symlinks,
    non-``.json`` files, or unrecognized names in ``decisions/`` — and must
    enumerate ``closures/`` at all.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = _ProjectFixture(Path(self.tmp.name).resolve())

    def tearDown(self):
        self.tmp.cleanup()

    def _store_subdir(self, name: str) -> Path:
        path = self.project.root / STORE_PATH / name
        path.mkdir(parents=True, exist_ok=True)
        return path

    def test_symlink_in_decisions_dir_is_flagged_not_skipped(self):
        decisions_dir = self._store_subdir("decisions")
        target = self.project.root / "outside.json"
        target.write_text("{}", encoding="utf-8")
        (decisions_dir / "D-001.json").symlink_to(target)

        errors = store.scan_store_integrity(self.project.root, STORE_PATH)
        self.assertTrue(any("symlink" in e.error and "D-001.json" in e.error for e in errors))

        report = checks.run_check(self.project.root, STORE_PATH)
        self.assertFalse(report.ok)
        self.assertTrue(any("symlink" in f.problem for f in report.findings))

    def test_non_json_file_in_decisions_dir_is_flagged_not_skipped(self):
        decisions_dir = self._store_subdir("decisions")
        (decisions_dir / "notes.txt").write_text("hi", encoding="utf-8")

        errors = store.scan_store_integrity(self.project.root, STORE_PATH)
        self.assertTrue(any("notes.txt" in e.error for e in errors))
        report = checks.run_check(self.project.root, STORE_PATH)
        self.assertFalse(report.ok)

    def test_unrecognized_name_in_decisions_dir_is_flagged_not_skipped(self):
        decisions_dir = self._store_subdir("decisions")
        (decisions_dir / "not-a-decision-id.json").write_text("{}", encoding="utf-8")

        errors = store.scan_store_integrity(self.project.root, STORE_PATH)
        self.assertTrue(any("not-a-decision-id.json" in e.error for e in errors))
        report = checks.run_check(self.project.root, STORE_PATH)
        self.assertFalse(report.ok)

    def test_symlinked_decisions_directory_itself_is_flagged(self):
        real_dir = self.project.root / "real-decisions"
        real_dir.mkdir()
        store_dir = self.project.root / STORE_PATH
        store_dir.mkdir(parents=True, exist_ok=True)
        (store_dir / "decisions").symlink_to(real_dir)

        errors = store.scan_store_integrity(self.project.root, STORE_PATH)
        self.assertTrue(any("decisions/ es un symlink" in e.error for e in errors))
        report = checks.run_check(self.project.root, STORE_PATH)
        self.assertFalse(report.ok)

    def test_symlinked_closures_directory_itself_is_flagged(self):
        real_dir = self.project.root / "real-closures"
        real_dir.mkdir()
        store_dir = self.project.root / STORE_PATH
        store_dir.mkdir(parents=True, exist_ok=True)
        (store_dir / "closures").symlink_to(real_dir)

        errors = store.scan_store_integrity(self.project.root, STORE_PATH)
        self.assertTrue(any("closures/ es un symlink" in e.error for e in errors))

    def test_orphan_closure_is_flagged_not_skipped(self):
        closures_dir = self._store_subdir("closures")
        (closures_dir / "D-999.json").write_text("{}", encoding="utf-8")
        # decisions/ deliberately left empty: D-999 has no matching decision.

        errors = store.scan_store_integrity(self.project.root, STORE_PATH)
        self.assertTrue(any("huérfano" in e.error and e.decision_id == "D-999" for e in errors))

        report = checks.run_check(self.project.root, STORE_PATH)
        self.assertFalse(report.ok)
        self.assertTrue(any("huérfano" in f.problem for f in report.findings))

    def test_malformed_closure_name_is_flagged_not_skipped(self):
        closures_dir = self._store_subdir("closures")
        (closures_dir / "D-1.json").write_text("{}", encoding="utf-8")  # too few digits

        errors = store.scan_store_integrity(self.project.root, STORE_PATH)
        self.assertTrue(any("D-1.json" in e.error for e in errors))


class ClosureActualOutcomeCheckTests(unittest.TestCase):
    """Careo round 1, finding #3: `check` must scan a closed decision's
    ``actual_outcome`` for Soho/PII too — the base engine never validates
    that field's content at write time, and `check` used to skip it too.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = _ProjectFixture(Path(self.tmp.name).resolve())

    def tearDown(self):
        self.tmp.cleanup()

    def _add_and_close(self, actual_outcome: str, review_decision: str = "ADOPT"):
        text = _read_fixture("valid_source.md")
        relative, digest = self.project.write_source("d1.md", text)
        journal = self.project.journal()
        journal.add(
            decision_id="D-001",
            title="Título de prueba",
            source_document=relative,
            source_hash=digest,
            friction_id="FR-053",
            hypothesis="Hipótesis de prueba suficientemente larga.",
            expected_outcome="Resultado esperado de prueba.",
            review_on="2026-09-30",
        )
        journal.close("D-001", actual_outcome=actual_outcome, review_decision=review_decision)

    def test_soho_in_actual_outcome_is_caught_by_check(self):
        # Passes the base engine's own close() cleanly — it applies no
        # content filter at all to actual_outcome — and used to pass this
        # adapter's check() too, silently, before this fix.
        self._add_and_close("Se confirmó que Soho ya usaba una métrica parecida internamente.")
        report = checks.run_check(self.project.root, STORE_PATH)
        self.assertFalse(report.ok)
        self.assertTrue(
            any(f.decision_id == "D-001" and "actual_outcome" in f.problem for f in report.findings)
        )

    def test_base_engine_already_blocks_pii_in_actual_outcome_at_write_time(self):
        # Documents a boundary, doesn't test this adapter: unlike Soho (which
        # the base engine has no notion of), personal data in actual_outcome
        # IS already rejected by DecisionJournal.close() itself (it reuses
        # _safe_text, the same helper used for title/hypothesis/expected_
        # outcome) — so this scenario can never reach the store for `check`
        # to catch. Verified here so the gap this fix closes isn't
        # overstated as covering PII too; it specifically closes the Soho
        # gap, which the base engine has no way to block.
        with self.assertRaises(Exception):
            self._add_and_close("Contacto de seguimiento: prueba.fixture@example.com")

    def test_clean_actual_outcome_still_passes(self):
        self._add_and_close("Resultado observado limpio de prueba, sin datos sensibles.")
        report = checks.run_check(self.project.root, STORE_PATH)
        self.assertTrue(report.ok)

    def test_open_decision_without_closure_still_passes(self):
        # actual_outcome is None while OPEN — must not crash or false-positive.
        text = _read_fixture("valid_source.md")
        relative, digest = self.project.write_source("d1.md", text)
        journal = self.project.journal()
        journal.add(
            decision_id="D-001",
            title="Título de prueba",
            source_document=relative,
            source_hash=digest,
            friction_id="FR-053",
            hypothesis="Hipótesis de prueba suficientemente larga.",
            expected_outcome="Resultado esperado de prueba.",
            review_on="2026-09-30",
        )
        report = checks.run_check(self.project.root, STORE_PATH)
        self.assertTrue(report.ok)


class BuildStatusIntegrityTrustTests(unittest.TestCase):
    """Careo round 1, finding #4: `status` must not publish unverified data
    and must escape free text before inserting it into a Markdown table.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = _ProjectFixture(Path(self.tmp.name).resolve())

    def tearDown(self):
        self.tmp.cleanup()

    def _add(self, decision_id: str, source_text: str, **overrides) -> None:
        relative, digest = self.project.write_source(f"{decision_id}.md", source_text)
        journal = self.project.journal()
        params = dict(
            decision_id=decision_id,
            title="Título de prueba",
            source_document=relative,
            source_hash=digest,
            friction_id="FR-053",
            hypothesis="Hipótesis de prueba suficientemente larga.",
            expected_outcome="Resultado esperado de prueba.",
            review_on="2026-09-30",
        )
        params.update(overrides)
        journal.add(**params)

    def test_decision_with_soho_source_is_excluded_from_normal_tables(self):
        self._add("D-001", _read_fixture("sensitive_soho_source.md"))
        view = views.build_status(self.project.root, STORE_PATH, as_of="2026-08-28")
        self.assertEqual(view.open_decisions, ())
        self.assertEqual(view.counts["open_total"], 0)
        self.assertTrue(any(item["decision_id"] == "D-001" for item in view.integrity_errors))
        markdown = view.to_markdown()
        self.assertIn("Errores de integridad", markdown)

    def test_title_with_pipe_and_newline_is_escaped_in_markdown_table(self):
        malicious_title = "Título | inyectado\ny una fila extra"
        self._add("D-001", _read_fixture("valid_source.md"), title=malicious_title)
        view = views.build_status(self.project.root, STORE_PATH, as_of="2026-08-28")
        markdown = view.to_markdown()

        self.assertNotIn(malicious_title, markdown)
        self.assertIn("Título \\| inyectado y una fila extra", markdown)

        open_section = markdown.split("## Abiertas", 1)[1].split("## Cerradas", 1)[0]
        data_rows = [line for line in open_section.splitlines() if line.startswith("| D-001")]
        self.assertEqual(len(data_rows), 1)


class EnginePathProvenanceTests(unittest.TestCase):
    """Careo round 1, finding #5: `engine_path` must reject a symlinked
    marker file and must catch a stale ``sys.modules`` entry pointing
    elsewhere instead of silently trusting whatever is already imported.
    """

    def test_symlinked_marker_is_rejected(self):
        real_candidate = engine_path.ensure_engine_importable()
        real_marker = real_candidate / "knowledge_ingest" / "decision_journal.py"

        with tempfile.TemporaryDirectory() as tmp:
            candidate = Path(tmp).resolve()
            marker_dir = candidate / "knowledge_ingest"
            marker_dir.mkdir()
            (marker_dir / "decision_journal.py").symlink_to(real_marker)

            old_env = os.environ.get(engine_path.ENV_VAR)
            os.environ[engine_path.ENV_VAR] = str(candidate)
            try:
                with self.assertRaises(engine_path.EngineNotFound):
                    engine_path.ensure_engine_importable()
            finally:
                if old_env is None:
                    del os.environ[engine_path.ENV_VAR]
                else:
                    os.environ[engine_path.ENV_VAR] = old_env

    def test_stale_sys_modules_entry_from_another_path_is_rejected(self):
        module_name = "knowledge_ingest.decision_journal"
        real_module = sys.modules.get(module_name)
        fake = types.ModuleType(module_name)
        fake.__file__ = str(
            Path(tempfile.gettempdir()) / "somewhere-else" / "knowledge_ingest" / "decision_journal.py"
        )
        sys.modules[module_name] = fake
        try:
            with self.assertRaises(engine_path.EngineProvenanceError):
                engine_path.ensure_engine_importable()
        finally:
            if real_module is not None:
                sys.modules[module_name] = real_module
            else:
                del sys.modules[module_name]


class GitignoreExtensionGuardTests(unittest.TestCase):
    """Careo round 1, finding #6: the ``.gitignore`` exceptions for
    ``knowledge/decisions/``, ``decisions/``, ``closures/``,
    ``capa2_decisions/`` and ``tests/`` must only unignore the extension
    each folder actually needs — never "anything goes".
    """

    repo_root: Path

    @classmethod
    def setUpClass(cls):
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=str(APP_ROOT),
                capture_output=True,
                text=True,
                check=True,
            )
        except (OSError, subprocess.CalledProcessError) as error:
            raise unittest.SkipTest(f"git not usable in this environment: {error}")
        cls.repo_root = Path(result.stdout.strip())

    def _is_ignored(self, relative_path: str) -> bool:
        result = subprocess.run(
            ["git", "check-ignore", "-q", relative_path],
            cwd=str(self.repo_root),
        )
        return result.returncode == 0

    def test_allowed_extensions_stay_trackable(self):
        base = "projects/briefs/capa2-ia-hoteles"
        trackable = [
            f"{base}/knowledge/decisions/zzz-test-marker.md",
            f"{base}/.capa2/decision-journal/decisions/zzz-test-marker.json",
            f"{base}/.capa2/decision-journal/closures/zzz-test-marker.json",
            f"{base}/.capa2/decision-journal/capa2_decisions/zzz_test_marker.py",
            f"{base}/.capa2/decision-journal/tests/zzz_test_marker.py",
            f"{base}/.capa2/decision-journal/tests/fixtures/zzz-test-marker.md",
            f"{base}/.capa2/decision-journal/README.md",
        ]
        for path in trackable:
            self.assertFalse(self._is_ignored(path), f"{path} should NOT be ignored, but git says it is")

    def test_disallowed_extensions_stay_ignored(self):
        base = "projects/briefs/capa2-ia-hoteles"
        blocked = [
            f"{base}/knowledge/decisions/zzz-test-marker.bin",
            f"{base}/knowledge/decisions/zzz-test-marker.png",
            f"{base}/.capa2/decision-journal/decisions/zzz-test-marker.bin",
            f"{base}/.capa2/decision-journal/decisions/zzz-test-marker.png",
            f"{base}/.capa2/decision-journal/closures/zzz-test-marker.bin",
            f"{base}/.capa2/decision-journal/capa2_decisions/zzz-test-marker.bin",
            f"{base}/.capa2/decision-journal/capa2_decisions/zzz-test-marker.png",
            f"{base}/.capa2/decision-journal/tests/zzz-test-marker.bin",
            f"{base}/.capa2/decision-journal/tests/fixtures/zzz-test-marker.png",
        ]
        for path in blocked:
            self.assertTrue(self._is_ignored(path), f"{path} should still be ignored, but git says it is not")


class SupersedesValidationTests(unittest.TestCase):
    """Careo round 1, finding #7: ``supersedes`` must be validated against
    the real state of the referenced decision — existence, CLOSED status,
    ADJUST verdict, and no self-reference — not accepted at face value.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = _ProjectFixture(Path(self.tmp.name).resolve())

    def tearDown(self):
        self.tmp.cleanup()

    def _add(self, decision_id: str, review_on: str = "2026-09-30", supersedes: str | None = None) -> None:
        text = _read_fixture("valid_source.md")
        if supersedes is not None:
            text = text.replace("owner: luisfran\n---", f"owner: luisfran\nsupersedes: {supersedes}\n---")
        relative, digest = self.project.write_source(f"{decision_id}.md", text)
        journal = self.project.journal()
        journal.add(
            decision_id=decision_id,
            title=f"Decisión {decision_id}",
            source_document=relative,
            source_hash=digest,
            friction_id="FR-053",
            hypothesis="Hipótesis suficientemente larga para pasar validación.",
            expected_outcome="Resultado esperado de prueba suficientemente largo.",
            review_on=review_on,
        )

    def _close(self, decision_id: str, review_decision: str, actual_outcome: str = "Resultado observado."):
        self.project.journal().close(decision_id, actual_outcome=actual_outcome, review_decision=review_decision)

    def test_supersedes_pointing_to_nonexistent_decision_is_an_integrity_error(self):
        self._add("D-002", supersedes="D-999")
        view = views.build_status(self.project.root, STORE_PATH, as_of="2026-08-28")
        self.assertEqual(view.successors, ())
        self.assertTrue(
            any(item["decision_id"] == "D-002" and "supersedes" in item["error"] for item in view.integrity_errors)
        )

    def test_supersedes_pointing_to_open_decision_is_not_a_successor(self):
        self._add("D-001")  # stays OPEN — never closed
        self._add("D-002", supersedes="D-001")
        view = views.build_status(self.project.root, STORE_PATH, as_of="2026-08-28")
        self.assertEqual(view.successors, ())
        self.assertTrue(any(item["decision_id"] == "D-002" for item in view.integrity_errors))

    def test_supersedes_pointing_to_adopt_closed_decision_is_not_a_successor(self):
        self._add("D-001")
        self._close("D-001", "ADOPT")
        self._add("D-002", supersedes="D-001")
        view = views.build_status(self.project.root, STORE_PATH, as_of="2026-08-28")
        self.assertEqual(view.successors, ())
        self.assertTrue(any(item["decision_id"] == "D-002" for item in view.integrity_errors))

    def test_self_referencing_supersedes_is_an_integrity_error(self):
        self._add("D-001", supersedes="D-001")
        view = views.build_status(self.project.root, STORE_PATH, as_of="2026-08-28")
        self.assertEqual(view.successors, ())
        self.assertTrue(
            any(
                item["decision_id"] == "D-001" and "autorreferencia" in item["error"]
                for item in view.integrity_errors
            )
        )

    def test_valid_adjust_successor_is_still_accepted(self):
        self._add("D-001")
        self._close("D-001", "ADJUST", actual_outcome="No funcionó como se esperaba.")
        self._add("D-002", supersedes="D-001")
        view = views.build_status(self.project.root, STORE_PATH, as_of="2026-08-28")
        self.assertEqual(view.successors, ({"decision_id": "D-002", "supersedes": "D-001"},))


class AddDecisionFieldSohoFilterTests(unittest.TestCase):
    """Careo round 3, finding #1: ``title``/``hypothesis``/``expected_outcome``
    must be screened for Soho references before ``add_decision`` persists
    anything — ``validate_source_text`` only ever looked at
    ``source_document``'s own content, never at these three caller-supplied
    fields.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = _ProjectFixture(Path(self.tmp.name).resolve())

    def tearDown(self):
        self.tmp.cleanup()

    def _add_kwargs(self, relative: str, **overrides) -> dict:
        params = dict(
            decision_id="D-001",
            title="Título de prueba",
            source_document=relative,
            friction_id="FR-053",
            hypothesis="Hipótesis de prueba suficientemente larga.",
            expected_outcome="Resultado esperado de prueba.",
            review_on="2026-09-30",
        )
        params.update(overrides)
        return params

    def test_soho_in_title_is_rejected_and_persists_nothing(self):
        relative, _ = self.project.write_source("d1.md", _read_fixture("valid_source.md"))
        kwargs = self._add_kwargs(relative, title="Automatizar la exportación diaria de SIHOT")
        with self.assertRaises(SohoDataDetected):
            add_module.add_decision(self.project.root, STORE_PATH, **kwargs)
        self.assertEqual(store.list_decision_ids(self.project.root, STORE_PATH), ())

    def test_soho_in_hypothesis_is_rejected_and_persists_nothing(self):
        relative, _ = self.project.write_source("d1.md", _read_fixture("valid_source.md"))
        kwargs = self._add_kwargs(
            relative, hypothesis="Si automatizamos esto, Soho ahorrará tiempo cada semana."
        )
        with self.assertRaises(SohoDataDetected):
            add_module.add_decision(self.project.root, STORE_PATH, **kwargs)
        self.assertEqual(store.list_decision_ids(self.project.root, STORE_PATH), ())

    def test_soho_in_expected_outcome_is_rejected_and_persists_nothing(self):
        relative, _ = self.project.write_source("d1.md", _read_fixture("valid_source.md"))
        kwargs = self._add_kwargs(relative, expected_outcome="Reducir el tiempo de carga en SBH un 20%.")
        with self.assertRaises(SohoDataDetected):
            add_module.add_decision(self.project.root, STORE_PATH, **kwargs)
        self.assertEqual(store.list_decision_ids(self.project.root, STORE_PATH), ())

    def test_clean_fields_still_persist(self):
        relative, _ = self.project.write_source("d1.md", _read_fixture("valid_source.md"))
        decision = add_module.add_decision(self.project.root, STORE_PATH, **self._add_kwargs(relative))
        self.assertEqual(decision.decision_id, "D-001")
        self.assertEqual(store.list_decision_ids(self.project.root, STORE_PATH), ("D-001",))


class StoreRootSymlinkTests(unittest.TestCase):
    """Careo round 3, finding #2: a symlinked store ROOT (not just a
    symlinked ``decisions/``/``closures/`` subdirectory) must be flagged.
    ``Path.is_symlink()`` only inspects the final path component, so
    ``decisions_dir.is_symlink()`` is False when only the store root's
    parent link is what was swapped — the previous sweep missed this
    entirely and would report OK with zero decisions.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = _ProjectFixture(Path(self.tmp.name).resolve())

    def tearDown(self):
        self.tmp.cleanup()

    def test_symlinked_store_root_is_flagged_as_critical_not_ok_with_zero_decisions(self):
        # An external, empty-but-real store: exactly the shape that used to
        # slip through, because decisions/ and closures/ underneath it are
        # real directories, not symlinks themselves.
        external = self.project.root / "external-store"
        (external / "decisions").mkdir(parents=True)
        (external / "closures").mkdir(parents=True)

        store_root = self.project.root / STORE_PATH
        store_root.parent.mkdir(parents=True, exist_ok=True)
        store_root.symlink_to(external)

        errors = store.scan_store_integrity(self.project.root, STORE_PATH)
        self.assertEqual(len(errors), 1)
        self.assertIn("symlink", errors[0].error)
        self.assertIn("CRÍTICO", errors[0].error)

        # Confirms the bug this closes: without the fix, decisions/ and
        # closures/ resolve (through the symlinked parent) to real, empty
        # directories, list_decision_ids() finds nothing, and check() used
        # to report OK with decisions_checked == 0 instead of flagging that
        # the whole store had been substituted.
        report = checks.run_check(self.project.root, STORE_PATH)
        self.assertFalse(report.ok)
        self.assertTrue(any("CRÍTICO" in f.problem for f in report.findings))

    def test_non_symlinked_store_root_is_unaffected(self):
        # Sanity check: a normal, real store root must not trip this check.
        (self.project.root / STORE_PATH / "decisions").mkdir(parents=True)
        errors = store.scan_store_integrity(self.project.root, STORE_PATH)
        self.assertEqual(errors, ())


class IntegrityErrorMarkdownEscapeTests(unittest.TestCase):
    """Careo round 3, finding #3 (regression from round 2): the escape added
    for ``title`` never covered ``decision_id``/``error`` of integrity
    errors, which can carry a raw, attacker-controlled filesystem entry
    name — e.g. a symlink or unrecognized file dropped into ``decisions/``.
    """

    def _make_view(self, decision_id: str, error: str) -> "views.StatusView":
        return views.StatusView(
            as_of="2026-08-28",
            counts={
                "open_total": 0,
                "overdue": 0,
                "due_soon": 0,
                "closed_total": 0,
                "adopt": 0,
                "adjust": 0,
                "discard": 0,
            },
            review_timeliness={"evaluated_total": 0, "evaluated_on_time": 0, "evaluated_on_time_pct": None},
            median_days_to_close=None,
            open_decisions=(),
            closed_decisions=(),
            successors=(),
            integrity_errors=({"decision_id": decision_id, "error": error},),
        )

    def test_newline_and_heading_in_error_field_does_not_inject_markdown_structure(self):
        malicious_error = "entrada symlink no permitida en decisions/: evil\n## Sección falsa\nmás | tuberías"
        view = self._make_view("D-001", malicious_error)
        markdown = view.to_markdown()

        # The raw injected text must not appear verbatim...
        self.assertNotIn(malicious_error, markdown)
        # ...and no bogus heading line was smuggled in.
        self.assertNotIn("\n## Sección falsa\n", markdown)
        for line in markdown.splitlines():
            self.assertFalse(
                line.strip().startswith("## Sección falsa"),
                f"a fake heading line leaked into STATUS.md: {line!r}",
            )
        # The content survives, just neutralized onto a single safe line.
        self.assertIn("## Sección falsa", markdown)  # present, but inline/escaped, not as its own line
        self.assertIn("\\|", markdown)  # the pipe was escaped

    def test_malicious_decision_id_field_is_also_escaped(self):
        malicious_id = "evil\n## Fake\nid"
        view = self._make_view(malicious_id, "error de prueba")
        markdown = view.to_markdown()
        self.assertNotIn(malicious_id, markdown)
        for line in markdown.splitlines():
            self.assertFalse(line.strip().startswith("## Fake"))

    def test_clean_integrity_error_renders_unchanged(self):
        view = self._make_view("D-001", "encabezado de contexto inválido: falta scope")
        markdown = view.to_markdown()
        self.assertIn("- **D-001**: encabezado de contexto inválido: falta scope", markdown)

    def test_markdown_markup_metacharacters_are_escaped_not_just_table_structure(self):
        # Round-3 final verification (Codex): the first extension of this
        # escape only covered table-structure characters (|, CR/LF/tab), not
        # inline Markdown/HTML markup — so a filesystem entry name could
        # still close a bold span the template opens and smuggle a link or
        # raw HTML, entirely inline, with no newline needed at all.
        malicious_error = "x**: [enlace](https://example.invalid) <script>alert(1)</script> `code`"
        view = self._make_view("D-001", malicious_error)
        markdown = view.to_markdown()

        # The raw, unescaped malicious string never appears verbatim.
        self.assertNotIn(malicious_error, markdown)
        # Every markup-opening character in the error text itself is
        # backslash-escaped (checked on the rendered error line only — the
        # template's own literal "**decision_id**" bullet markup is legitimate
        # and intentionally NOT escaped, so a whole-document check would give
        # a false positive there).
        error_line = next(line for line in markdown.splitlines() if line.startswith("- **D-001**:"))
        rendered_error = error_line.removeprefix("- **D-001**: ")
        self.assertIn("\\*\\*", rendered_error)  # the bold-closing ** is escaped
        self.assertIn("\\[enlace\\]\\(https://example.invalid\\)", rendered_error)  # link syntax neutralized
        self.assertIn("\\`code\\`", rendered_error)  # backticks neutralized
        self.assertIn("\\<script\\>alert\\(1\\)\\</script\\>", rendered_error)  # angle brackets + parens escaped

    def test_end_to_end_unrecognized_filename_is_escaped_in_rendered_markdown(self):
        # Same shape as FilesystemIntegritySweepTests, but driven all the
        # way through to the rendered STATUS.md instead of stopping at the
        # raw IntegrityError list.
        tmp = tempfile.TemporaryDirectory()
        try:
            project = _ProjectFixture(Path(tmp.name).resolve())
            decisions_dir = project.root / STORE_PATH / "decisions"
            decisions_dir.mkdir(parents=True)
            malicious_name = "evil\n## Sección falsa | inyectada.json"
            (decisions_dir / malicious_name).write_text("{}", encoding="utf-8")

            view = views.build_status(project.root, STORE_PATH, as_of="2026-08-28")
            markdown = view.to_markdown()
            for line in markdown.splitlines():
                self.assertFalse(line.strip().startswith("## Sección falsa"))
        finally:
            tmp.cleanup()


class AddDecisionSupersedesValidationTests(unittest.TestCase):
    """Careo round 3, finding #4a: ``add_decision`` must validate
    ``supersedes`` against the real state of the store at write time — not
    accept it at face value and leave the check to ``views.build_status``
    after the fact.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = _ProjectFixture(Path(self.tmp.name).resolve())

    def tearDown(self):
        self.tmp.cleanup()

    def _source_with_supersedes(self, supersedes: str | None) -> str:
        text = _read_fixture("valid_source.md")
        if supersedes is not None:
            text = text.replace("owner: luisfran\n---", f"owner: luisfran\nsupersedes: {supersedes}\n---")
        return text

    def _add_kwargs(self, decision_id: str, relative: str, **overrides) -> dict:
        params = dict(
            decision_id=decision_id,
            title=f"Decisión {decision_id}",
            source_document=relative,
            friction_id="FR-053",
            hypothesis="Hipótesis suficientemente larga para pasar validación.",
            expected_outcome="Resultado esperado de prueba suficientemente largo.",
            review_on="2026-10-15",
        )
        params.update(overrides)
        return params

    def test_supersedes_nonexistent_decision_is_rejected_and_persists_nothing(self):
        relative, _ = self.project.write_source(
            "D-002.md", self._source_with_supersedes("D-999")
        )
        with self.assertRaises(InvalidSupersedes):
            add_module.add_decision(self.project.root, STORE_PATH, **self._add_kwargs("D-002", relative))
        self.assertEqual(store.list_decision_ids(self.project.root, STORE_PATH), ())

    def test_self_referencing_supersedes_is_rejected_and_persists_nothing(self):
        relative, _ = self.project.write_source(
            "D-001.md", self._source_with_supersedes("D-001")
        )
        with self.assertRaises(InvalidSupersedes):
            add_module.add_decision(self.project.root, STORE_PATH, **self._add_kwargs("D-001", relative))
        self.assertEqual(store.list_decision_ids(self.project.root, STORE_PATH), ())

    def test_supersedes_pointing_to_open_decision_is_rejected_and_persists_nothing(self):
        original_relative, _ = self.project.write_source("D-001.md", self._source_with_supersedes(None))
        add_module.add_decision(
            self.project.root, STORE_PATH, **self._add_kwargs("D-001", original_relative, review_on="2026-09-30")
        )
        # D-001 stays OPEN — never closed.
        relative, _ = self.project.write_source("D-002.md", self._source_with_supersedes("D-001"))
        with self.assertRaises(InvalidSupersedes):
            add_module.add_decision(self.project.root, STORE_PATH, **self._add_kwargs("D-002", relative))
        self.assertEqual(store.list_decision_ids(self.project.root, STORE_PATH), ("D-001",))

    def test_supersedes_pointing_to_adopt_closed_decision_is_rejected_and_persists_nothing(self):
        original_relative, _ = self.project.write_source("D-001.md", self._source_with_supersedes(None))
        add_module.add_decision(
            self.project.root, STORE_PATH, **self._add_kwargs("D-001", original_relative, review_on="2026-09-30")
        )
        self.project.journal().close("D-001", actual_outcome="Funcionó como se esperaba.", review_decision="ADOPT")

        relative, _ = self.project.write_source("D-002.md", self._source_with_supersedes("D-001"))
        with self.assertRaises(InvalidSupersedes):
            add_module.add_decision(self.project.root, STORE_PATH, **self._add_kwargs("D-002", relative))
        self.assertEqual(store.list_decision_ids(self.project.root, STORE_PATH), ("D-001",))

    def test_supersedes_pointing_to_adjust_closed_decision_is_accepted(self):
        original_relative, _ = self.project.write_source("D-001.md", self._source_with_supersedes(None))
        add_module.add_decision(
            self.project.root, STORE_PATH, **self._add_kwargs("D-001", original_relative, review_on="2026-09-30")
        )
        self.project.journal().close(
            "D-001", actual_outcome="No funcionó como se esperaba.", review_decision="ADJUST"
        )

        relative, _ = self.project.write_source("D-002.md", self._source_with_supersedes("D-001"))
        decision = add_module.add_decision(self.project.root, STORE_PATH, **self._add_kwargs("D-002", relative))
        self.assertEqual(decision.decision_id, "D-002")
        self.assertEqual(
            set(store.list_decision_ids(self.project.root, STORE_PATH)), {"D-001", "D-002"}
        )


class SupersedesExclusiveFromNormalTablesTests(unittest.TestCase):
    """Careo round 3, finding #4b: a decision with an invalid ``supersedes``
    must appear ONLY in integrity_errors, never also in
    open_decisions/closed_decisions — the previous version appended it to
    the normal table first and only added the integrity error afterwards.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = _ProjectFixture(Path(self.tmp.name).resolve())

    def tearDown(self):
        self.tmp.cleanup()

    def _add_raw(self, decision_id: str, review_on: str = "2026-09-30", supersedes: str | None = None) -> None:
        # Bypasses add_decision on purpose (uses the base engine directly)
        # to simulate data that predates the finding #4a fix, or that
        # otherwise reached the store some other way — build_status must
        # still handle it correctly regardless of how it got there.
        text = _read_fixture("valid_source.md")
        if supersedes is not None:
            text = text.replace("owner: luisfran\n---", f"owner: luisfran\nsupersedes: {supersedes}\n---")
        relative, digest = self.project.write_source(f"{decision_id}.md", text)
        self.project.journal().add(
            decision_id=decision_id,
            title=f"Decisión {decision_id}",
            source_document=relative,
            source_hash=digest,
            friction_id="FR-053",
            hypothesis="Hipótesis suficientemente larga para pasar validación.",
            expected_outcome="Resultado esperado de prueba suficientemente largo.",
            review_on=review_on,
        )

    def test_invalid_supersedes_open_decision_is_not_also_in_open_decisions(self):
        self._add_raw("D-002", supersedes="D-999")
        view = views.build_status(self.project.root, STORE_PATH, as_of="2026-08-28")
        self.assertTrue(any(item["decision_id"] == "D-002" for item in view.integrity_errors))
        self.assertEqual(view.open_decisions, ())
        self.assertEqual(view.counts["open_total"], 0)

    def test_invalid_supersedes_closed_decision_is_not_also_in_closed_decisions(self):
        self._add_raw("D-002", supersedes="D-999")
        self.project.journal().close(
            "D-002", actual_outcome="Resultado observado de prueba.", review_decision="ADOPT"
        )
        view = views.build_status(self.project.root, STORE_PATH, as_of="2026-08-28")
        self.assertTrue(any(item["decision_id"] == "D-002" for item in view.integrity_errors))
        self.assertEqual(view.closed_decisions, ())
        self.assertEqual(view.counts["closed_total"], 0)
        # Also excluded from timeliness/median bookkeeping, not just the table.
        self.assertEqual(view.review_timeliness["evaluated_total"], 0)
        self.assertIsNone(view.median_days_to_close)

    def test_decision_never_appears_in_both_a_normal_table_and_integrity_errors(self):
        self._add_raw("D-001", supersedes="D-999")
        self._add_raw("D-002")  # clean, no supersedes
        view = views.build_status(self.project.root, STORE_PATH, as_of="2026-08-28")
        normal_ids = {item["decision_id"] for item in view.open_decisions} | {
            item["decision_id"] for item in view.closed_decisions
        }
        error_ids = {item["decision_id"] for item in view.integrity_errors}
        self.assertEqual(normal_ids & error_ids, set())
        self.assertIn("D-001", error_ids)
        self.assertIn("D-002", normal_ids)


if __name__ == "__main__":
    unittest.main()
