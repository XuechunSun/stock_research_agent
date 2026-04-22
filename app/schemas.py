"""Pydantic models for scope, routing, tools, and structured answers."""

from __future__ import annotations

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field


class ScopeStatus(str, Enum):
    IN_SCOPE = "IN_SCOPE"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"


class ToolName(str, Enum):
    WEB_SEARCH = "web_search"
    FILE_SEARCH = "file_search"
    CALCULATOR = "calculator"
    STOCK_MODEL = "stock_model"


class ScopeResult(BaseModel):
    status: ScopeStatus
    reason: str
    detected_symbols: list[str] = Field(default_factory=list)


class MatchType(str, Enum):
    """How a static-map symbol match was made (scope resolver only, phase 1)."""

    exact_ticker = "exact_ticker"
    name_alias = "name_alias"
    unresolved = "unresolved"


class MatchConfidence(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class ResolvedSymbol(BaseModel):
    """One resolved US identity candidate from the phase-1 static table (not live data)."""

    matched_name: str
    ticker: str
    is_us_listed: Optional[bool] = None
    exchange: Optional[str] = None
    match_type: MatchType
    confidence: MatchConfidence
    via: str = ""  # e.g. alias text or 'META' (internal diagnostics only)


class SymbolResolution(BaseModel):
    """Output of internal symbol resolution for scope; not a routed tool result."""

    candidates: list[ResolvedSymbol] = Field(default_factory=list)
    ambiguity_reason: Optional[str] = None
    notes: list[str] = Field(default_factory=list)


class RoutingPlan(BaseModel):
    tools: list[ToolName]
    rationale: str


ToolRunStatus = Literal["ok", "skipped", "unsupported", "error"]


class ToolResult(BaseModel):
    name: ToolName
    status: ToolRunStatus
    input_summary: str
    output_lines: list[str] = Field(default_factory=list)
    uncertainty_notes: list[str] = Field(default_factory=list)
    citations_or_sources: list[str] = Field(default_factory=list)


class StructuredAnswer(BaseModel):
    """All sections are bullet lines only (list[str])."""

    summary: list[str]
    confirmed_facts: list[str]
    key_positives: list[str]
    risks: list[str]
    valuation_and_calculations: list[str]
    model_signal: list[str]
    uncertainty: list[str]
    next_steps: list[str]


def render_answer_for_cli(answer: StructuredAnswer) -> str:
    """Render structured answer as readable plain text for the CLI."""
    sections: list[tuple[str, list[str]]] = [
        ("Summary", answer.summary),
        ("Confirmed facts", answer.confirmed_facts),
        ("Key positives", answer.key_positives),
        ("Risks", answer.risks),
        ("Valuation / calculations", answer.valuation_and_calculations),
        ("Model signal (auxiliary only)", answer.model_signal),
        ("Uncertainty", answer.uncertainty),
        ("Next steps", answer.next_steps),
    ]
    lines: list[str] = []
    for title, items in sections:
        lines.append(f"## {title}")
        if not items:
            lines.append("  (none)")
        else:
            for item in items:
                lines.append(f"  - {item}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"