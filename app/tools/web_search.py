"""Web search tool (stub). TODO: integrate real search API (e.g. Tavily, Bing)."""

from __future__ import annotations

from app.schemas import ToolName, ToolResult
from app.utils.logging import get_logger

logger = get_logger(__name__)


def run(query: str) -> ToolResult:
    """Stub: no live crawl in phase 1."""
    logger.debug("web_search.run query_len=%s", len(query))
    return ToolResult(
        name=ToolName.WEB_SEARCH,
        status="ok",
        input_summary="web_search (stub)",
        output_lines=["Status: stub only; no HTTP request executed."],
        uncertainty_notes=[
            "No live web retrieval; nothing here is verified against public sources.",
        ],
    )
