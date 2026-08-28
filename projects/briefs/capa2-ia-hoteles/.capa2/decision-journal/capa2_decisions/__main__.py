"""CLI entry point: ``python -m capa2_decisions <command>``.

Commands
--------
``add``              The ONLY supported way to register a new decision.
                     Validates the source note's context header + Soho
                     filter + personal-data filter, computes its hash, and
                     only then calls the base engine's create-once
                     ``DecisionJournal.add`` — no window to skip validation
                     (careo round 1, finding #1). Superseded design note:
                     an earlier revision of this CLI left ``add`` out on
                     purpose and told operators to call
                     ``python -m knowledge_ingest.decision_journal ... add``
                     directly; that flow is no longer the documented one
                     (see README.md) precisely because it had no such gate.
``status``          Regenerate ``derived/status.json`` + ``derived/STATUS.md``
                     and print one of them to stdout.
``check``            Read-only integrity sweep over the whole store; exit
                     code 0 when clean, 1 otherwise.
``validate-source``  Diagnostic-only dry run of one source note's context
                     header and content filters, without touching the
                     store and without registering anything. Useful to
                     iterate on a note before you have the rest of the
                     ``add`` fields ready — the real gate is ``add`` itself,
                     not this command.

``due``/``close`` are intentionally NOT here — per the FR-053 design
(section 9) those stay exactly what they already are:
``python -m knowledge_ingest.decision_journal ...``. This CLI only adds what
the base engine does not have: the Capa 2 context header, the Soho filter,
the mandatory validate-then-persist gate on add, and the derived view.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from .add import add_decision
from .checks import run_check
from .validate import SourceValidationError, validate_source_file
from .views import build_status

DEFAULT_STORE = Path(".capa2/decision-journal")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="capa2_decisions")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--store", type=Path, default=DEFAULT_STORE)
    commands = parser.add_subparsers(dest="command", required=True)

    add_cmd = commands.add_parser("add")
    add_cmd.add_argument("--id", dest="decision_id", required=True)
    add_cmd.add_argument("--title", required=True)
    add_cmd.add_argument("--source-document", required=True, type=str)
    add_cmd.add_argument("--friction", dest="friction_id", required=True)
    add_cmd.add_argument("--hypothesis", required=True)
    add_cmd.add_argument("--expected-outcome", dest="expected_outcome", required=True)
    add_cmd.add_argument("--review-on", dest="review_on", required=True)

    status_cmd = commands.add_parser("status")
    status_cmd.add_argument("--format", choices=("markdown", "json"), default="markdown")
    status_cmd.add_argument("--as-of", default=date.today().isoformat())
    status_cmd.add_argument("--no-write", action="store_true", help="don't regenerate derived/, just print")

    commands.add_parser("check")

    validate_cmd = commands.add_parser("validate-source")
    validate_cmd.add_argument("path", type=Path)

    args = parser.parse_args(argv)

    if args.command == "add":
        return _run_add(args)
    if args.command == "status":
        return _run_status(args)
    if args.command == "check":
        return _run_check(args)
    if args.command == "validate-source":
        return _run_validate_source(args)
    parser.error(f"unknown command {args.command!r}")
    return 2


def _run_add(args: argparse.Namespace) -> int:
    try:
        decision = add_decision(
            args.project_root,
            args.store,
            decision_id=args.decision_id,
            title=args.title,
            source_document=args.source_document,
            friction_id=args.friction_id,
            hypothesis=args.hypothesis,
            expected_outcome=args.expected_outcome,
            review_on=args.review_on,
        )
    except (SourceValidationError, OSError, ValueError) as error:
        print(f"add failed: {error}", file=sys.stderr)
        return 1
    print(f"decision={decision.decision_id} status={decision.status}")
    return 0


def _run_status(args: argparse.Namespace) -> int:
    view = build_status(args.project_root, args.store, as_of=args.as_of)
    if not args.no_write:
        derived_dir = args.project_root / args.store / "derived"
        derived_dir.mkdir(parents=True, exist_ok=True)
        (derived_dir / "status.json").write_text(view.to_json(), encoding="utf-8")
        (derived_dir / "STATUS.md").write_text(view.to_markdown(), encoding="utf-8")
    output = view.to_markdown() if args.format == "markdown" else view.to_json()
    sys.stdout.write(output)
    return 0


def _run_check(args: argparse.Namespace) -> int:
    report = run_check(args.project_root, args.store)
    sys.stdout.write(report.render())
    return 0 if report.ok else 1


def _run_validate_source(args: argparse.Namespace) -> int:
    try:
        header = validate_source_file(args.path)
    except SourceValidationError as error:
        print(f"validate-source failed: {error}", file=sys.stderr)
        return 1
    print(f"OK: {args.path} — scope={header.scope} metric_code={header.metric_code}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
