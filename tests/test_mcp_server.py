"""Integration tests: the MCP tools are actually invoked through an MCP client, not just imported."""

import json
import sys

import pytest
from mcp import Client, StdioServerParameters

from evidence_aware_rag.config import REPO_ROOT
from evidence_aware_rag.mcp_server import create_server
from evidence_aware_rag.pipeline import KnowledgeBase

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="module")
def server():
    return create_server(KnowledgeBase.load())


def payload(result):
    assert not result.is_error, result.content
    return result.structured_content if result.structured_content is not None else json.loads(result.content[0].text)


async def test_lists_the_four_read_only_tools(server):
    async with Client(server) as client:
        tools = (await client.list_tools()).tools
    assert {t.name for t in tools} == {"search_knowledge", "get_document", "list_sources", "get_applicable_policy"}
    assert all(t.annotations.read_only_hint for t in tools)


async def test_search_knowledge_returns_an_evidence_package(server):
    async with Client(server) as client:
        package = payload(await client.call_tool(
            "search_knowledge", {"query": "What compensation is Acme Corp entitled to for INC-014?"}))
    assert package["sufficiency"]["status"] == "sufficient"
    assert package["temporal"][0]["applicable"] == ["SLA-002"]
    assert package["evidence"][0]["document_id"] == "SLA-002"


async def test_get_applicable_policy_reuses_the_resolver(server):
    async with Client(server) as client:
        pinned = payload(await client.call_tool(
            "get_applicable_policy", {"policy_family": "service_sla", "on_date": "2026-09-03", "customer_id": "CUS-002"}))
    assert (pinned["applicable"], pinned["governed_by"]) == (["SLA-001"], "contract_pin")


async def test_unknown_document_gives_a_helpful_error(server):
    async with Client(server) as client:
        result = await client.call_tool("get_document", {"document_id": "INC-14"})
    assert result.is_error
    assert "Did you mean" in result.content[0].text


async def test_invalid_date_is_rejected_clearly(server):
    async with Client(server) as client:
        result = await client.call_tool("search_knowledge", {"query": "x", "as_of_date": "11/10/2026"})
    assert result.is_error and "ISO date" in result.content[0].text


async def test_stdio_round_trip_like_a_real_agent():
    params = StdioServerParameters(command=sys.executable, args=["-m", "evidence_aware_rag.mcp_server"],
                                   cwd=str(REPO_ROOT))
    async with Client(params, read_timeout_seconds=120) as client:
        sources = payload(await client.call_tool("list_sources", {"type": "contract"}))
    assert len(sources["result"] if isinstance(sources, dict) else sources) == 5
