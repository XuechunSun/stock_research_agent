"""User document search (stub). TODO: local index / RAG over user corpus."""

from __future__ import annotations

from app.schemas import ToolName, ToolResult
from app.utils.logging import get_logger

logger = get_logger(__name__)


def run(query: str) -> ToolResult:
    """Stub: no corpus configured in phase 1."""
    logger.debug("file_search.run query_len=%s", len(query))
    return ToolResult(
        name=ToolName.FILE_SEARCH,
        status="ok",
        input_summary="file_search (stub)",
        output_lines=["Status: no local file corpus configured."],
        uncertainty_notes=[
            "No documents were indexed or searched.",
        ],
    )
