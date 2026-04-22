"""
Static US name/ticker resolution for `assess_scope` only. Not a routed research tool.
Phase 1: local dict + parsing; no network. TODO: optional validated vendor/list later.
"""

from __future__ import annotations

import re
from typing import Optional, Tuple

from app.schemas import MatchConfidence, MatchType, ResolvedSymbol, SymbolResolution
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Ticker -> (canonical name, US exchange label or None, us_listed from table only).
_TICKER_META: dict[str, Tuple[str, Optional[str], bool]] = {
    "AAPL": ("Apple", "NASDAQ", True),
    "AMZN": ("Amazon", "NASDAQ", True),
    "COST": ("Costco", "NASDAQ", True),
    "GOOG": ("Alphabet (Class C)", "NASDAQ", True),
    "GOOGL": ("Alphabet (Class A)", "NASDAQ", True),
    "JPM": ("JPMorgan Chase", "NYSE", True),
    "META": ("Meta", "NASDAQ", True),
    "MSFT": ("Microsoft", "NASDAQ", True),
    "NVDA": ("NVIDIA", "NASDAQ", True),
    "PANW": ("Palo Alto Networks", "NASDAQ", True),
    "TSLA": ("Tesla", "NASDAQ", True),
}

# Multi-word phrases first (longest match wins for scanning order).
_NAME_PHRASES: list[tuple[str, str]] = sorted(
    [
        ("palo alto networks", "PANW"),
        ("palo alto", "PANW"),
        ("jpmorgan chase", "JPM"),
        ("jpmorgan", "JPM"),
        ("jp morgan", "JPM"),
        ("meta platforms", "META"),
        ("alphabet", "GOOGL"),
    ],
    key=lambda x: len(x[0]),
    reverse=True,
)

# Single-token lowercase aliases (word-bounded) -> ticker
_SINGLE_ALIASES: dict[str, str] = {
    "aapl": "AAPL",
    "amzn": "AMZN",
    "apple": "AAPL",
    "amazon": "AMZN",
    "costco": "COST",
    "meta": "META",
    "facebook": "META",
    "google": "GOOGL",
    "microsoft": "MSFT",
    "msft": "MSFT",
    "nvidia": "NVDA",
    "nvda": "NVDA",
    "tesla": "TSLA",
    "tsla": "TSLA",
    "panw": "PANW",
    "googl": "GOOGL",
    "goog": "GOOG",
    "jpm": "JPM",
}


def all_known_tickers() -> frozenset[str]:
    return frozenset(_TICKER_META.keys())


def resolve(question: str) -> SymbolResolution:
    """
    Deterministic resolution from a small static map. Never performs I/O.
    May return 0, 1, or multiple candidates (e.g. compare two mapped tickers).
    """
    if not question.strip():
        return SymbolResolution(notes=["empty input"])

    q_lower = question.lower()
    by_tix: dict[str, ResolvedSymbol] = {}

    for phrase, tix in _NAME_PHRASES:
        if re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", q_lower):
            _put(by_tix, tix, phrase, MatchType.name_alias)

    for m in re.finditer(r"\b([a-z]{2,20})\b", q_lower):
        tok = m.group(1)
        if tok in _SINGLE_ALIASES:
            _put(by_tix, _SINGLE_ALIASES[tok], tok, MatchType.name_alias)

    for m in re.finditer(r"\b([A-Z]{1,5})\b", question):
        tix = m.group(1)
        if tix in _TICKER_META:
            _put(by_tix, tix, tix, MatchType.exact_ticker)

    cands = sorted(by_tix.values(), key=lambda c: c.ticker)
    notes: list[str] = []
    amb: Optional[str] = None
    if not cands:
        notes.append("no static map match")
    if len(cands) > 2:
        amb = "More than two distinct in-map tickers; verify which symbols to analyze."
    logger.debug("symbol_resolver tickers=%s", [c.ticker for c in cands])
    return SymbolResolution(candidates=cands, ambiguity_reason=amb, notes=notes)


def _put(
    by_tix: dict[str, ResolvedSymbol],
    tix: str,
    via: str,
    mtype: MatchType,
) -> None:
    meta = _TICKER_META.get(tix)
    if not meta:
        return
    name, ex, us = meta
    by_tix[tix] = ResolvedSymbol(
        matched_name=name,
        ticker=tix,
        is_us_listed=True if us else None,
        exchange=ex,
        match_type=mtype,
        confidence=MatchConfidence.high,
        via=via,
    )
