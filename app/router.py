"""Conservative tool routing from user questions (phase 1, keyword heuristics)."""

from __future__ import annotations

import re

from app.schemas import RoutingPlan, ToolName
from app.tools import calculator


def plan_tools(question: str) -> RoutingPlan:
    """
    Decide which tools to invoke. No default web_search; empty plan is valid.
    Order is stable: web_search, file_search, calculator, stock_model.
    """
    q = question.lower()
    chosen: list[ToolName] = []
    reasons: list[str] = []

    if _wants_public_time_sensitive(q):
        chosen.append(ToolName.WEB_SEARCH)
        reasons.append("public/time-sensitive cue")

    if _wants_user_documents(q):
        chosen.append(ToolName.FILE_SEARCH)
        reasons.append("user-document cue")

    if calculator.question_matches_numeric_template(question):
        chosen.append(ToolName.CALCULATOR)
        reasons.append("numeric template matched")

    if _wants_auxiliary_model(q):
        chosen.append(ToolName.STOCK_MODEL)
        reasons.append("auxiliary/heuristic cue")

    rationale = "; ".join(reasons) if reasons else "no tool cues matched"
    return RoutingPlan(tools=chosen, rationale=rationale)


def _wants_public_time_sensitive(q: str) -> bool:
    """Only clear public / time-sensitive research cues (bias to false negatives)."""
    patterns = (
        r"\b(latest|current)\s+(news|headlines?|developments?)\b",
        r"\brecent\b",
        r"\btoday\b",
        r"\bnews\b",
        r"\b(headline|announced|announcement)\b",
        r"\bearnings\b",
        r"\bguidance\b",
        r"\b8[- ]?k\b",
        r"\b10[- ]?[kq]\b",
        r"\bsec\b.*\b(filing|filed)\b",
        r"\bpublic\s+filing\b",
    )
    return any(re.search(p, q) for p in patterns)


def _wants_user_documents(q: str) -> bool:
    cues = (
        "my notes",
        "my file",
        "local file",
        "uploaded",
        "upload",
        "in my document",
        "from my pdf",
        "/users/",
        "c:\\",
    )
    return any(c in q for c in cues)


def _wants_auxiliary_model(q: str) -> bool:
    """Auxiliary / heuristic only — not generic 'forecast' alone."""
    if re.search(r"\bforecast\b", q) and "mock" not in q and "auxiliary" not in q:
        return False
    return bool(
        re.search(
            r"risk screen|auxiliary|heuristic|model signal|mock signal|auxiliary signal",
            q,
        )
    )
