"""MCP server exposing the knowledge base to AI agents (stdio transport).

Run:
    uv run python -m evidence_aware_rag.mcp_server

Register in Claude Code:
    claude mcp add evidence-aware-rag -- uv --directory /path/to/repo run python -m evidence_aware_rag.mcp_server

Built on the `mcp` 2.x SDK, where the high-level server class is `MCPServer` (formerly FastMCP).
"""

from __future__ import annotations

import difflib
from datetime import date

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError  # message reaches the agent; other errors stay server-side
from mcp.types import ToolAnnotations

from evidence_aware_rag.models import DateMention
from evidence_aware_rag.pipeline import KnowledgeBase, build_pipeline
from evidence_aware_rag.temporal import TemporalResolver

INSTRUCTIONS = """\
Knowledge base of Northstar Cloud (synthetic data): policies with versions, contracts, tickets,
CRM records and meeting notes. Start with `search_knowledge`. It returns an evidence package with
the governing policy version, temporal ambiguity flags and a structural sufficiency verdict.
If `sufficiency.status` is not "sufficient", or `clarification_needed` is true, say so instead of
guessing. Call `get_document` before quoting a document in full.
"""

READ_ONLY = ToolAnnotations(readOnlyHint=True, openWorldHint=False)


def parse_date(value: str | None, field: str) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ToolError(f"{field} must be an ISO date (YYYY-MM-DD), got {value!r}") from None


def create_server(kb: KnowledgeBase) -> MCPServer:
    server = MCPServer("evidence-aware-rag", instructions=INSTRUCTIONS)
    pipeline = build_pipeline("full", kb)
    resolver = TemporalResolver(kb.corpus)
    corpus = kb.corpus

    def require_document(document_id: str) -> None:
        if document_id not in corpus:
            close = difflib.get_close_matches(document_id.upper(), [d.id for d in corpus], n=3)
            hint = f" Did you mean: {', '.join(close)}?" if close else " Use list_sources to see valid IDs."
            raise ToolError(f"Unknown document_id {document_id!r}.{hint}")

    @server.tool(annotations=READ_ONLY)
    def search_knowledge(query: str, as_of_date: str | None = None, max_documents: int = 8) -> dict:
        """Retrieve evidence for a question.

        Returns an evidence package: documents with the chunks that matched and why each was
        included, the governing policy version (and why: in force, contract pin or exception),
        temporal ambiguity / clarification flags, and a structural sufficiency verdict.
        `as_of_date` (YYYY-MM-DD) is the date the question is asked; it never overrides a date
        the question refers to (e.g. an incident date), but a difference is reported in `date_notes`.
        """
        package = pipeline.run(query, as_of=parse_date(as_of_date, "as_of_date"))
        package.evidence = package.evidence[: max(1, max_documents)]
        return package.model_dump(mode="json")

    @server.tool(annotations=READ_ONLY)
    def get_document(document_id: str) -> dict:
        """Full text and metadata of one document (e.g. "SLA-002", "INC-014", "CTR-004")."""
        require_document(document_id)
        doc = corpus.get(document_id)
        return {"metadata": doc.meta.model_dump(mode="json", exclude_defaults=True), "text": doc.text}

    @server.tool(annotations=READ_ONLY)
    def list_sources(type: str | None = None) -> list[dict]:
        """List the documents in the knowledge base, optionally filtered by type
        (policy, policy_draft, contract, ticket, crm, meeting, marketing, runbook)."""
        docs = [d for d in corpus if type is None or d.meta.type == type]
        return [{"document_id": d.id, "title": d.meta.title, "type": d.meta.type,
                 "date": d.meta.date.isoformat(), "status": d.meta.status} for d in docs]

    @server.tool(annotations=READ_ONLY)
    def get_applicable_policy(policy_family: str, on_date: str, customer_id: str | None = None) -> dict:
        """Which policy version governs `policy_family` on `on_date` (YYYY-MM-DD), for an optional
        customer (CRM ID, e.g. "CUS-002"): applies contract exceptions, pins and plan coverage.
        Families: service_sla, refund_policy, security_policy, support_policy."""
        if policy_family not in corpus.rules.policy_families:
            raise ToolError(f"Unknown policy_family {policy_family!r}. "
                             f"Valid: {', '.join(corpus.rules.policy_families)}")
        if customer_id is not None:
            require_document(customer_id)
        day = parse_date(on_date, "on_date")
        assessment = resolver.resolve(
            policy_family, [DateMention(day=day, source="question", detail="on_date")], customer_id
        )
        return assessment.model_dump(mode="json")

    return server


def main() -> None:
    create_server(KnowledgeBase.load()).run("stdio")


if __name__ == "__main__":
    main()
