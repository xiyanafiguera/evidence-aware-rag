"""Validate the consistency of the synthetic dataset.

Checks that the manifest, the document files and (if present) the evaluation questions agree with
each other, so that retrieval metrics are never computed against a broken dataset.

Usage:
    uv run scripts/validate_data.py
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from evidence_aware_rag.config import Settings
from evidence_aware_rag.models import DomainRules, Manifest, Question

DATA_DIR = Settings().data_dir
EVAL_DIR = Settings().eval_dir
NOT_INDEXED = {"WORLD.md", "manifest.json", "domain_rules.json", ".gitkeep", ".DS_Store"}
DOC_ID_LINE = re.compile(r"^Document ID:\s*(\S+)", re.MULTILINE)


def parse_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def declared_id(path: Path) -> str | None:
    """Return the ID written inside the document itself (markdown header line or JSON field)."""
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        record = json.loads(text)
        return record.get("ticket_id") or record.get("customer_id")
    match = DOC_ID_LINE.search(text)
    return match.group(1) if match else None


def validate_manifest(docs: list[dict]) -> list[str]:
    errors: list[str] = []
    by_id: dict[str, dict] = {}

    for doc in docs:
        doc_id = doc["document_id"]
        if doc_id in by_id:
            errors.append(f"duplicate document_id {doc_id}")
        by_id[doc_id] = doc

    listed_paths = set()
    for doc in docs:
        doc_id, rel_path = doc["document_id"], doc["path"]
        listed_paths.add(rel_path)
        path = DATA_DIR / rel_path
        if not path.exists():
            errors.append(f"{doc_id}: file not found {rel_path}")
            continue
        if (found := declared_id(path)) != doc_id:
            errors.append(f"{doc_id}: file {rel_path} declares ID {found!r}")

        for field in ("date", "valid_from", "valid_to", "occurred_at", "ingested_at"):
            try:
                parse_date(doc.get(field))
            except ValueError:
                errors.append(f"{doc_id}: invalid date in {field}: {doc.get(field)!r}")

        linked = list(doc.get("references", []))
        linked += [doc[f] for f in ("supersedes", "superseded_by") if doc.get(f)]
        linked += [pin["document_id"] for pin in doc.get("pinned_policies", {}).values()]
        linked += doc.get("customer_ids", [])
        for target in linked:
            if target not in by_id:
                errors.append(f"{doc_id}: references unknown document {target}")

    for path in DATA_DIR.rglob("*"):
        rel_path = path.relative_to(DATA_DIR).as_posix()
        if path.is_file() and path.name not in NOT_INDEXED and rel_path not in listed_paths:
            errors.append(f"file not listed in manifest: {rel_path}")

    errors += validate_versions(by_id)
    return errors


def validate_versions(by_id: dict[str, dict]) -> list[str]:
    """Versions of a policy family must not overlap in time and must link to each other."""
    errors: list[str] = []
    families: dict[str, list[dict]] = defaultdict(list)
    for doc in by_id.values():
        if doc.get("policy_family") and doc.get("status") != "draft":
            families[doc["policy_family"]].append(doc)

    for family, versions in families.items():
        versions.sort(key=lambda d: d["valid_from"])
        for older, newer in zip(versions, versions[1:]):
            older_end = parse_date(older["valid_to"])
            if older_end is None or older_end >= parse_date(newer["valid_from"]):
                errors.append(f"{family}: {older['document_id']} overlaps {newer['document_id']}")
            if older.get("superseded_by") != newer["document_id"]:
                errors.append(f"{family}: {older['document_id']}.superseded_by should be {newer['document_id']}")
            if newer.get("supersedes") != older["document_id"]:
                errors.append(f"{family}: {newer['document_id']}.supersedes should be {older['document_id']}")
        if versions and versions[-1]["valid_to"] is not None:
            errors.append(f"{family}: latest version {versions[-1]['document_id']} should be open-ended")
    return errors


def validate_questions(known_ids: set[str]) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for path in sorted(EVAL_DIR.glob("questions_*.json")):
        for question in json.loads(path.read_text(encoding="utf-8")):
            qid = question["id"]
            if qid in seen:
                errors.append(f"{path.name}: duplicate question id {qid}")
            seen.add(qid)
            for doc_id in question.get("gold_evidence", []):
                if doc_id not in known_ids:
                    errors.append(f"{path.name} {qid}: unknown gold evidence {doc_id}")
            for doc_id in question.get("gold_version", {}).values():
                if doc_id not in known_ids:
                    errors.append(f"{path.name} {qid}: unknown gold version {doc_id}")
    return errors


def validate_schemas() -> list[str]:
    """Schema-level validation with the package's own pydantic models."""
    errors: list[str] = []
    checks = [
        (DATA_DIR / "manifest.json", Manifest.model_validate_json),
        (DATA_DIR / "domain_rules.json", DomainRules.model_validate_json),
    ]
    question_list = TypeAdapter(list[Question])
    checks += [(path, question_list.validate_json) for path in sorted(EVAL_DIR.glob("questions_*.json"))]
    for path, validate in checks:
        try:
            validate(path.read_text(encoding="utf-8"))
        except ValidationError as exc:
            errors.append(f"{path.name}: schema error\n{exc}")
    return errors


def validate_rules(docs: list[dict]) -> list[str]:
    rules = json.loads((DATA_DIR / "domain_rules.json").read_text(encoding="utf-8"))
    families = {d["policy_family"] for d in docs if d.get("policy_family")}
    errors = [f"domain_rules: unknown policy family {f}" for f in rules["policy_families"] if f not in families]
    errors += [f"domain_rules: no clause rules for family {f}" for f in families if f not in rules["policy_families"]]
    return errors


def main() -> int:
    errors = validate_schemas()
    if errors:
        print("\n".join(errors))
        return 1
    manifest = json.loads((DATA_DIR / "manifest.json").read_text(encoding="utf-8"))
    docs = manifest["documents"]
    errors = validate_manifest(docs)
    errors += validate_rules(docs)
    errors += validate_questions({d["document_id"] for d in docs})

    if errors:
        print(f"✗ {len(errors)} problem(s) found:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(f"✓ dataset OK: {len(docs)} documents")
    return 0


if __name__ == "__main__":
    sys.exit(main())
