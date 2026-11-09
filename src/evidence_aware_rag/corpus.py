"""Load the knowledge base (manifest + files) and answer metadata lookups.

Everything downstream (retrievers, temporal resolution, relation expansion) reads documents
through this class, so the on-disk layout is known in one place only.
"""

from __future__ import annotations

import json
from functools import cached_property
from pathlib import Path

from evidence_aware_rag.models import Document, DocumentMeta, DomainRules, Manifest


def render_record(record: dict, title: str) -> str:
    """Render a JSON record (ticket, CRM entry) as plain text so it can be indexed like prose."""
    lines = [title]
    for key, value in record.items():
        if value is None:
            value = "none"
        lines.append(f"{key.replace('_', ' ')}: {value}")
    return "\n".join(lines)


class Corpus:
    def __init__(self, documents: list[Document], rules: DomainRules, records: dict[str, dict]):
        self._docs = {doc.id: doc for doc in documents}
        self.rules = rules
        self._records = records  # raw JSON of structured documents, by document_id

    @classmethod
    def load(cls, data_dir: Path) -> Corpus:
        manifest = Manifest.model_validate_json((data_dir / "manifest.json").read_text(encoding="utf-8"))
        rules = DomainRules.model_validate_json((data_dir / "domain_rules.json").read_text(encoding="utf-8"))
        documents, records = [], {}
        for meta in manifest.documents:
            raw = (data_dir / meta.path).read_text(encoding="utf-8")
            if meta.path.endswith(".json"):
                records[meta.document_id] = json.loads(raw)
                text = render_record(records[meta.document_id], meta.title)
            else:
                text = raw
            documents.append(Document(meta=meta, text=text))
        return cls(documents, rules, records)

    def __len__(self) -> int:
        return len(self._docs)

    def __iter__(self):
        return iter(self._docs.values())

    def __contains__(self, document_id: str) -> bool:
        return document_id in self._docs

    def get(self, document_id: str) -> Document:
        try:
            return self._docs[document_id]
        except KeyError:
            raise KeyError(f"unknown document_id {document_id!r}") from None

    def meta(self, document_id: str) -> DocumentMeta:
        return self.get(document_id).meta

    def by_customer(self, customer_id: str) -> list[Document]:
        return [doc for doc in self if customer_id in doc.meta.customer_ids]

    def policy_versions(self, family: str, include_drafts: bool = False) -> list[Document]:
        versions = [
            doc for doc in self
            if doc.meta.policy_family == family and (include_drafts or doc.meta.status != "draft")
        ]
        return sorted(versions, key=lambda d: (d.meta.valid_from is None, d.meta.valid_from or d.meta.date))

    def contract_for(self, customer_id: str) -> Document | None:
        contracts = [d for d in self.by_customer(customer_id) if d.meta.type == "contract"]
        return contracts[0] if contracts else None

    @cached_property
    def entity_aliases(self) -> dict[str, str]:
        """Lower-cased customer name -> CRM document ID (e.g. "acme corp" -> "CUS-001")."""
        return {
            record["name"].lower(): doc_id
            for doc_id, record in self._records.items()
            if self.meta(doc_id).type == "crm"
        }
