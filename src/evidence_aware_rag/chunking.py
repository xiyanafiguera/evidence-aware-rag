"""Split documents into retrievable chunks.

Documents are short, so the unit is the markdown section (`## ...`) rather than a sliding token
window. Structured records (JSON) become a single chunk. Every chunk starts with the document
title so it stays meaningful when read out of context.
"""

from __future__ import annotations

import re

from evidence_aware_rag.models import Chunk, Document

SECTION_HEADING = re.compile(r"^##\s+(.+)$", re.MULTILINE)


def chunk_document(doc: Document) -> list[Chunk]:
    if doc.meta.path.endswith(".json"):
        return [Chunk(chunk_id=f"{doc.id}#0", document_id=doc.id, section=None, text=doc.text)]

    headings = list(SECTION_HEADING.finditer(doc.text))
    if not headings:
        return [Chunk(chunk_id=f"{doc.id}#0", document_id=doc.id, section=None, text=doc.text.strip())]

    chunks = []
    preamble = doc.text[: headings[0].start()].strip()
    if preamble:
        chunks.append(Chunk(chunk_id=f"{doc.id}#0", document_id=doc.id, section=None, text=preamble))

    for i, heading in enumerate(headings):
        end = headings[i + 1].start() if i + 1 < len(headings) else len(doc.text)
        section = heading.group(1).strip()
        body = doc.text[heading.end():end].strip()
        chunks.append(Chunk(
            chunk_id=f"{doc.id}#{len(chunks)}",
            document_id=doc.id,
            section=section,
            text=f"{doc.meta.title} — {section}\n{body}",
        ))
    return chunks


def chunk_corpus(docs) -> list[Chunk]:
    return [chunk for doc in docs for chunk in chunk_document(doc)]
