"""Deterministic agent: scope gate, routing, tool execution, structured answer assembly."""

from __future__ import annotations

import re
from collections.abc import Callable

from app.router import plan_tools
from app.schemas import (
    ScopeResult,
    ScopeStatus,
    StructuredAnswer,
    ToolName,
    ToolResult,
)
from app.tools import calculator, file_search, stock_model, web_search, symbol_resolver
from app.utils.logging import get_logger

logger = get_logger(__name__)

_TICKER_STOPWORDS = frozenset(
    "THE AND FOR ARE BUT NOT YOU ALL CAN HER WAS ONE OUR OUT DAY GET HAS HIM HIS HOW ITS LET NEW NOW OLD SEE TWO WAY WHO BOY DID SHE USE MAY ANY".split()
)

_FOREIGN_OR_NON_US_PATTERNS = (
    re.compile(r"\.(hk|l|sw|to|pa|as|mc|de)\b", re.I),
    re.compile(r"\b(lse|hkex|tsx|xetra|euronext|ftse|nikkei|hang seng)\b", re.I),
    re.compile(r"\b(lon|tyo|tse|hk):\s*[A-Z0-9]", re.I),
)

_AMBIGUOUS_LISTING_PATTERNS = (
    re.compile(r"\badr\b", re.I),
    re.compile(r"also listed in", re.I),
    re.compile(r"dual[- ]listed", re.I),
)

_CRYPTO_FOREX = re.compile(
    r"\b(bitcoin|btc|ethereum|eth|crypto|dogecoin|solana|forex|fx\b|currency pair)\b",
    re.I,
)

_EXPLICIT_US_CUES = re.compile(
    r"\b(nasdaq|nyse|nyse arca|arca|amex|us[- ]listed|u\.s\.[- ]listed|us stock|"
    r"american stock|s&p|sp500|s&p 500)\b",
    re.I,
)

_EQUITY_CUES = re.compile(
    r"\b(stock|stocks|ticker|share|shares|equity|eps|p/?e|valuation|dividend|"
    r"earnings|market cap|buyback|10[- ]?[kq]|8[- ]?k|sec filing|margin of safety|"
    r"buy|sell|invest|investment)\b",
    re.I,
)

_TOOL_DISPATCH: dict[ToolName, Callable[[str], ToolResult]] = {
    ToolName.WEB_SEARCH: web_search.run,
    ToolName.FILE_SEARCH: file_search.run,
    ToolName.CALCULATOR: calculator.run,
    ToolName.STOCK_MODEL: stock_model.run,
}


def assess_scope(question: str) -> ScopeResult:
    """Classify request scope; prefer clarification over guessing US listing."""
    q_raw = question.strip()
    q = q_raw.lower()
    detected: list[str] = []

    if not q_raw:
        return ScopeResult(
            status=ScopeStatus.OUT_OF_SCOPE,
            reason="Empty question.",
            detected_symbols=[],
        )

    if _CRYPTO_FOREX.search(q):
        return ScopeResult(
            status=ScopeStatus.OUT_OF_SCOPE,
            reason="Crypto/FX is out of scope (US equities only).",
            detected_symbols=[],
        )

    for pat in _FOREIGN_OR_NON_US_PATTERNS:
        if pat.search(q_raw):
            return ScopeResult(
                status=ScopeStatus.OUT_OF_SCOPE,
                reason="Non-US market/exchange cues detected.",
                detected_symbols=[],
            )

    ambiguous_listing = any(p.search(q) for p in _AMBIGUOUS_LISTING_PATTERNS)
    resolution = symbol_resolver.resolve(q_raw)
    resolved_syms = [c.ticker for c in resolution.candidates if c.ticker]
    has_resolved = bool(resolved_syms)
    detected.extend(resolved_syms)

    foreign_hint = ambiguous_listing  # ADR / dual-listed → clarify if mixed signals

    explicit_us = bool(_EXPLICIT_US_CUES.search(q))
    equity_cue = bool(_EQUITY_CUES.search(q))
    unknown_tickers = _unknown_us_style_tickers(q_raw)

    if foreign_hint and (has_resolved or explicit_us):
        return ScopeResult(
            status=ScopeStatus.NEEDS_CLARIFICATION,
            reason="Ambiguous listing (e.g. ADR/dual-listed) with US cues; confirm US primary listing intent.",
            detected_symbols=sorted(set(detected)),
        )

    if foreign_hint and not has_resolved and not explicit_us:
        return ScopeResult(
            status=ScopeStatus.NEEDS_CLARIFICATION,
            reason="ADR/dual-listed language without clear US-only focus.",
            detected_symbols=sorted(set(detected)),
        )

    if has_resolved and not foreign_hint:
        if resolution.ambiguity_reason:
            return ScopeResult(
                status=ScopeStatus.NEEDS_CLARIFICATION,
                reason=resolution.ambiguity_reason,
                detected_symbols=sorted(set(detected) | set(unknown_tickers)),
            )
        if unknown_tickers:
            return ScopeResult(
                status=ScopeStatus.NEEDS_CLARIFICATION,
                reason="Resolved in-map symbol(s) alongside other unmapped ticker-like tokens; verify tickers and US listing.",
                detected_symbols=sorted(set(detected) | set(unknown_tickers)),
            )
        return ScopeResult(
            status=ScopeStatus.IN_SCOPE,
            reason="Resolved US symbol(s) from phase-1 static map (not live listing verification).",
            detected_symbols=sorted(set(detected)),
        )

    if explicit_us and equity_cue:
        if unknown_tickers:
            return ScopeResult(
                status=ScopeStatus.NEEDS_CLARIFICATION,
                reason="Explicit US cues with unmapped ticker-like symbols; verify US listing/ticker.",
                detected_symbols=sorted(set(detected) | set(unknown_tickers)),
            )
        return ScopeResult(
            status=ScopeStatus.IN_SCOPE,
            reason="Explicit US market context with equity research cues (no specific symbol resolved).",
            detected_symbols=sorted(set(detected)),
        )

    if unknown_tickers:
        return ScopeResult(
            status=ScopeStatus.NEEDS_CLARIFICATION,
            reason="Unmapped ticker-like symbols; not verified against phase-1 static map or US context.",
            detected_symbols=sorted(set(detected) | set(unknown_tickers)),
        )

    if equity_cue and not has_resolved:
        return ScopeResult(
            status=ScopeStatus.NEEDS_CLARIFICATION,
            reason="Equity research cues without a resolved in-map symbol and without explicit US market context.",
            detected_symbols=sorted(set(detected)),
        )

    return ScopeResult(
        status=ScopeStatus.OUT_OF_SCOPE,
        reason="No US equity scope cues (resolved symbol, explicit US market + equity, or other equity terms).",
        detected_symbols=sorted(set(detected)),
    )


def _unknown_us_style_tickers(question: str) -> list[str]:
    known = symbol_resolver.all_known_tickers()
    out: list[str] = []
    for m in re.finditer(r"\b([A-Z]{2,5})\b", question):
        t = m.group(1)
        if t in _TICKER_STOPWORDS:
            continue
        if t in known:
            continue
        out.append(t)
    return sorted(set(out))


def _extract_user_numeric_tokens(question: str) -> list[str]:
    seen: set[str] = set()
    facts: list[str] = []
    for m in re.finditer(r"\$?\d+(?:\.\d+)?%?", question):
        tok = m.group(0)
        if tok not in seen:
            seen.add(tok)
            facts.append(f"User-provided numeric token: {tok}")
    return facts


def _scope_plain(status: ScopeStatus) -> str:
    return {
        ScopeStatus.IN_SCOPE: "IN_SCOPE",
        ScopeStatus.OUT_OF_SCOPE: "OUT_OF_SCOPE",
        ScopeStatus.NEEDS_CLARIFICATION: "NEEDS_CLARIFICATION",
    }[status]


def _evidence_limitation_bullet() -> str:
    return (
        "Evidence limitation: phase-1 deterministic run; stub tools; no live web verification; "
        "no local document corpus."
    )


def _build_summary(scope: ScopeResult) -> list[str]:
    return [
        f"Scope status: {_scope_plain(scope.status)} — {scope.reason}",
        _evidence_limitation_bullet(),
    ]


def run_agent(question: str) -> tuple[ScopeResult, StructuredAnswer]:
    """Run scope gate, optional tools, and assemble StructuredAnswer (no LLM)."""
    scope = assess_scope(question)
    logger.info("scope=%s symbols=%s", scope.status, scope.detected_symbols)

    if scope.status in (ScopeStatus.OUT_OF_SCOPE, ScopeStatus.NEEDS_CLARIFICATION):
        return scope, _answer_without_tools(question, scope)

    plan = plan_tools(question)
    logger.info("route=%s", plan.rationale)
    results: list[ToolResult] = []
    for tool in plan.tools:
        runner = _TOOL_DISPATCH[tool]
        results.append(runner(question))

    return scope, _synthesize(question, scope, plan.rationale, results)


def _answer_without_tools(question: str, scope: ScopeResult) -> StructuredAnswer:
    user_nums = _extract_user_numeric_tokens(question)
    sys_facts: list[str] = []
    if scope.status == ScopeStatus.OUT_OF_SCOPE:
        sys_facts.append("System: request treated as out of scope; no tools executed.")
    else:
        sys_facts.append("System: clarification required; no tools executed.")

    return StructuredAnswer(
        summary=_build_summary(scope),
        confirmed_facts=user_nums + sys_facts,
        key_positives=[
            "No investment merits identified from verified external data (tools not run for this scope state).",
        ],
        risks=[
            "US listing and instrument type may be unclear; do not act without confirming scope.",
            "Phase-1 output is not verified research.",
        ],
        valuation_and_calculations=["No calculator run (tools not executed for this scope state)."],
        model_signal=["No auxiliary model run (tools not executed for this scope state)."],
        uncertainty=[
            f"Scope: {scope.reason}",
            _evidence_limitation_bullet(),
        ],
        next_steps=[
            "If US-listed equity: restate with explicit US listing or a name/ticker covered by the phase-1 static map.",
            "Avoid trading decisions based on this stub output alone.",
        ],
    )


def _synthesize(
    question: str,
    scope: ScopeResult,
    route_rationale: str,
    results: list[ToolResult],
) -> StructuredAnswer:
    user_facts = _extract_user_numeric_tokens(question)
    sys_facts: list[str] = [f"System: routing rationale — {route_rationale}."]

    valuation_lines: list[str] = []
    model_lines: list[str] = []
    uncertainty: list[str] = [
        f"Scope: {scope.reason}",
        _evidence_limitation_bullet(),
    ]

    for tr in results:
        if tr.name == ToolName.WEB_SEARCH:
            sys_facts.append("System: web search executed as stub only (no live HTTP retrieval).")
        elif tr.name == ToolName.FILE_SEARCH:
            sys_facts.append("System: file search executed as stub (no local corpus configured).")
        elif tr.name == ToolName.CALCULATOR:
            if tr.status == "ok":
                sys_facts.append("System: calculator returned arithmetic on user-stated inputs (not market data).")
                valuation_lines.extend(tr.output_lines)
            elif tr.status == "unsupported":
                sys_facts.append("System: calculator reported unsupported template for this question.")
            elif tr.status == "error":
                sys_facts.append("System: calculator reported an input error (e.g. divide by zero).")
            uncertainty.extend(tr.uncertainty_notes)
        elif tr.name == ToolName.STOCK_MODEL:
            sys_facts.append("System: stock_model executed as non-predictive stub only.")
            model_lines.extend(tr.output_lines)
            uncertainty.extend(tr.uncertainty_notes)

    if not valuation_lines:
        valuation_lines.append("No calculator result produced (no match or not routed).")

    if not model_lines:
        model_lines.append("No auxiliary model output (tool not routed or stub only).")

    return StructuredAnswer(
        summary=_build_summary(scope),
        confirmed_facts=user_facts + sys_facts,
        key_positives=[
            "No verified fundamental positives retrieved; phase-1 stubs do not ingest filings or live data.",
        ],
        risks=[
            "Data may be incomplete; margin-of-safety work requires primary sources and cross-checks.",
            "Stub tools can omit material information; uncertainty is not fully enumerable.",
        ],
        valuation_and_calculations=valuation_lines,
        model_signal=model_lines,
        uncertainty=uncertainty,
        next_steps=[
            "Confirm key inputs against primary sources before relying on any arithmetic.",
            "If time-sensitive public facts are needed, integrate a real web retrieval tool (phase 2+).",
        ],
    )
