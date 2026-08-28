"""Capa 2 adapter around ``knowledge_ingest.decision_journal`` (FR-053).

This package never reimplements the base journal's security primitives
(atomic create-once writes, symlink/path-traversal rejection, hash binding).
It only adds what is specific to the Capa 2 pilot:

- parsing/validating the Capa 2 context header on each decision's source note
  (``scope``, ``content_ids``, ``metric_code``, ``baseline``, ``target``, ``owner``);
- rejecting text that identifies internal Soho matters (on top of the base
  journal's own personal-data filter);
- building the read-only derived view (``status.json`` / ``STATUS.md``) that
  the content loop is allowed to read.

See ``.capa2/decision-journal/README.md`` for the operational runbook.
"""

__version__ = "0.1.0"
