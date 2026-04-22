"""Auxiliary model signal (stub). TODO: optional real model vendor integration."""

from __future__ import annotations

from app.schemas import ToolName, ToolResult
from app.utils.logging import get_logger

logger = get_logger(__name__)


def run(query: str) -> ToolResult:
    """Stub: non-predictive placeholder only (not a forecast)."""
    logger.debug("stock_model.run query_len=%s", len(query))
    return ToolResult(
        name=ToolName.STOCK_MODEL,
        status="ok",
        input_summary="stock_model (stub)",
        output_lines=["Mock auxiliary signal: not computed."],
        uncertainty_notes=[
            "Non-predictive mock only; not investment advice.",
            "Not a trained forecast and not alpha.",
        ],
    )
