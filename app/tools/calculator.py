"""Narrow phase-1 numeric templates only. TODO: expand with validated parsers / libraries."""

from __future__ import annotations

import re
from typing import Optional, Tuple

from app.schemas import ToolName, ToolResult
from app.utils.logging import get_logger

logger = get_logger(__name__)


def question_matches_numeric_template(question: str) -> bool:
    """True iff run() would not return status unsupported (for router use)."""
    q = question.lower()
    if _match_eps_pe(question):
        return True
    if _match_yoy(question):
        return True
    if _match_margin(question):
        return True
    if _match_upside_downside(question):
        return True
    if "dcf" in q and _dcf_inputs_present(question):
        return True
    return False


def run(question: str) -> ToolResult:
    """Run first matching template in fixed order; otherwise unsupported."""
    logger.debug("calculator.run")
    if _match_eps_pe(question):
        return _tool_eps_pe(question)
    if _match_yoy(question):
        return _tool_yoy(question)
    if _match_margin(question):
        return _tool_margin(question)
    if _match_upside_downside(question):
        return _tool_upside(question)
    q = question.lower()
    if "dcf" in q:
        return _tool_dcf(question)
    return ToolResult(
        name=ToolName.CALCULATOR,
        status="unsupported",
        input_summary="calculator",
        output_lines=[],
        uncertainty_notes=[
            "No supported numeric template matched (phase 1).",
            "Valuation questions need explicit template inputs (EPS/PE, YoY pair, "
            "labeled margin inputs, target+price pair, or full DCF inputs).",
        ],
    )


def _num_re() -> str:
    return r"(\d+(?:\.\d+)?)"


def _match_eps_pe(text: str) -> bool:
    tl = text.lower()
    if not (("eps" in tl or "earnings per share" in tl) and ("p/e" in tl or re.search(r"\bpe\b", tl) or "price to earnings" in tl)):
        return False
    eps_m = re.search(rf"eps\s*(?:of|is|=|:)?\s*{_num_re()}", tl)
    if not eps_m:
        eps_m = re.search(rf"earnings per share\s*(?:of|is|=|:)?\s*{_num_re()}", tl)
    pe_m = re.search(rf"(?:p/?e|price to earnings)\s*(?:of|is|=|:)?\s*{_num_re()}", tl)
    if not pe_m:
        pe_m = re.search(rf"\bpe\s*(?:of|is|=|:)?\s*{_num_re()}", tl)
    return bool(eps_m and pe_m)


def _tool_eps_pe(text: str) -> ToolResult:
    tl = text.lower()
    eps_m = re.search(rf"eps\s*(?:of|is|=|:)?\s*{_num_re()}", tl) or re.search(
        rf"earnings per share\s*(?:of|is|=|:)?\s*{_num_re()}", tl
    )
    pe_m = re.search(rf"(?:p/?e|price to earnings)\s*(?:of|is|=|:)?\s*{_num_re()}", tl) or re.search(
        rf"\bpe\s*(?:of|is|=|:)?\s*{_num_re()}", tl
    )
    assert eps_m and pe_m
    eps = float(eps_m.group(1))
    pe = float(pe_m.group(1))
    price = eps * pe
    return ToolResult(
        name=ToolName.CALCULATOR,
        status="ok",
        input_summary="implied_price = EPS * P/E",
        output_lines=[f"Implied price = EPS * P/E = {eps} * {pe} = {price:g}."],
        uncertainty_notes=[
            "Arithmetic on user-provided inputs only; not a market price.",
        ],
    )


def _match_yoy(text: str) -> bool:
    tl = text.lower()
    if not (re.search(r"\b(yoy|year[- ]over[- ]year)\b", tl) or ("prior" in tl and "current" in tl)):
        return False
    return _extract_yoy_pair(text) is not None


def _extract_yoy_pair(text: str) -> Optional[Tuple[float, float]]:
    """Prior/earlier value and current value (prior first)."""
    tl = text.lower()
    m = re.search(rf"prior\s+{_num_re()}\s+current\s+{_num_re()}", tl)
    if m:
        return float(m.group(1)), float(m.group(2))
    m = re.search(rf"previous\s+{_num_re()}\s+current\s+{_num_re()}", tl)
    if m:
        return float(m.group(1)), float(m.group(2))
    m = re.search(rf"from\s+{_num_re()}\s+to\s+{_num_re()}\s+(?:yoy|year)", tl)
    if m:
        return float(m.group(1)), float(m.group(2))
    return None


def _tool_yoy(text: str) -> ToolResult:
    pair = _extract_yoy_pair(text)
    if not pair:
        return ToolResult(
            name=ToolName.CALCULATOR,
            status="unsupported",
            input_summary="yoy",
            output_lines=[],
            uncertainty_notes=["YoY template requires explicit prior/current or from/to with yoy cue."],
        )
    prior, current = pair
    if prior == 0:
        return ToolResult(
            name=ToolName.CALCULATOR,
            status="error",
            input_summary="yoy",
            output_lines=[],
            uncertainty_notes=["Prior value cannot be zero for YoY growth."],
        )
    pct = (current - prior) / prior * 100.0
    return ToolResult(
        name=ToolName.CALCULATOR,
        status="ok",
        input_summary="yoy_growth",
        output_lines=[f"YoY growth = (current - prior) / prior = {pct:.4f}%."],
        uncertainty_notes=["Uses only the two user-provided values."],
    )


def _match_margin(text: str) -> bool:
    tl = text.lower()
    if "gross profit" in tl and "revenue" in tl:
        return bool(
            re.search(rf"gross profit\s*(?:of|is|=|:)?\s*{_num_re()}", tl)
            and re.search(rf"revenue\s*(?:of|is|=|:)?\s*{_num_re()}", tl)
        )
    if "operating income" in tl and "revenue" in tl:
        return bool(
            re.search(rf"operating income\s*(?:of|is|=|:)?\s*{_num_re()}", tl)
            and re.search(rf"revenue\s*(?:of|is|=|:)?\s*{_num_re()}", tl)
        )
    return False


def _tool_margin(text: str) -> ToolResult:
    tl = text.lower()

    def extract_pair(label_a: str, label_b: str) -> Optional[Tuple[float, float]]:
        ma = re.search(rf"{label_a}\s*(?:of|is|=|:)?\s*{_num_re()}", tl)
        mb = re.search(rf"{label_b}\s*(?:of|is|=|:)?\s*{_num_re()}", tl)
        if ma and mb:
            return float(ma.group(1)), float(mb.group(1))
        return None

    if "gross profit" in tl:
        pair = extract_pair("gross profit", "revenue")
        kind = "Gross margin"
    else:
        pair = extract_pair("operating income", "revenue")
        kind = "Operating margin"
    if not pair:
        return ToolResult(
            name=ToolName.CALCULATOR,
            status="unsupported",
            input_summary="margin",
            output_lines=[],
            uncertainty_notes=["Margin template requires labeled numerator and revenue."],
        )
    part, base = pair
    if base == 0:
        return ToolResult(
            name=ToolName.CALCULATOR,
            status="error",
            input_summary="margin",
            output_lines=[],
            uncertainty_notes=["Revenue (base) cannot be zero."],
        )
    m = part / base * 100.0
    return ToolResult(
        name=ToolName.CALCULATOR,
        status="ok",
        input_summary="margin",
        output_lines=[f"{kind} = part / revenue = {part} / {base} = {m:.4f}%."],
        uncertainty_notes=["Uses only user-provided numerator and revenue."],
    )


def _match_upside_downside(text: str) -> bool:
    tl = text.lower()
    if "target" in tl and ("price" in tl or "trading" in tl or "at" in tl):
        return bool(
            re.search(rf"target\s+(?:price\s+)?\$?{_num_re()}", tl)
            and re.search(rf"(?:price|trading at)\s+\$?{_num_re()}", tl)
        )
    if re.search(r"upside|downside", tl):
        return bool(re.search(rf"from\s+\$?{_num_re()}\s+to\s+\$?{_num_re()}", tl))
    return False


def _tool_upside(text: str) -> ToolResult:
    tl = text.lower()
    tm = re.search(rf"target\s+(?:price\s+)?\$?{_num_re()}", tl)
    pm = re.search(rf"(?:price|trading at)\s+(?:is\s+)?\$?{_num_re()}", tl)
    if tm and pm:
        target = float(tm.group(1))
        price = float(pm.group(1))
    else:
        m = re.search(rf"from\s+\$?{_num_re()}\s+to\s+\$?{_num_re()}", tl)
        if not m:
            return ToolResult(
                name=ToolName.CALCULATOR,
                status="unsupported",
                input_summary="upside",
                output_lines=[],
                uncertainty_notes=["Upside/downside template requires target+price or from/to numbers."],
            )
        price = float(m.group(1))
        target = float(m.group(2))
    if price == 0:
        return ToolResult(
            name=ToolName.CALCULATOR,
            status="error",
            input_summary="upside",
            output_lines=[],
            uncertainty_notes=["Current price cannot be zero."],
        )
    pct = (target - price) / price * 100.0
    return ToolResult(
        name=ToolName.CALCULATOR,
        status="ok",
        input_summary="upside_pct",
        output_lines=[f"Move = (target - price) / price = {pct:.4f}%."],
        uncertainty_notes=["Uses only user-provided target and price."],
    )


def _parse_rate(raw: str) -> float:
    v = float(raw)
    if v > 1.0 and v <= 100.0:
        return v / 100.0
    return v


def _dcf_inputs_present(text: str) -> bool:
    return _extract_dcf_inputs(text) is not None


def _extract_dcf_inputs(text: str) -> Optional[Tuple[float, float, float]]:
    tl = text.lower()
    fcf_m = re.search(rf"(?:fcf|free cash flow)\s*(?:of|is|=|:)?\s*{_num_re()}", tl)
    w_m = re.search(rf"(?:wacc|discount rate)\s*(?:of|is|=|:)?\s*{_num_re()}\s*%?", tl)
    g_m = re.search(rf"(?:terminal growth|tg)\s*(?:of|is|=|:)?\s*{_num_re()}\s*%?", tl)
    if fcf_m and w_m and g_m:
        fcf = float(fcf_m.group(1))
        wacc = _parse_rate(w_m.group(1))
        g = _parse_rate(g_m.group(1))
        return fcf, wacc, g
    return None


def _tool_dcf(text: str) -> ToolResult:
    """Single-stage terminal placeholder only when FCF, WACC, and tg are explicit."""
    triple = _extract_dcf_inputs(text)
    if not triple:
        return ToolResult(
            name=ToolName.CALCULATOR,
            status="unsupported",
            input_summary="dcf",
            output_lines=[],
            uncertainty_notes=[
                "DCF template requires explicit FCF, WACC (or discount rate), and terminal growth (tg).",
            ],
        )
    fcf, wacc, g = triple
    if wacc <= g:
        return ToolResult(
            name=ToolName.CALCULATOR,
            status="error",
            input_summary="dcf",
            output_lines=[],
            uncertainty_notes=["WACC must be greater than terminal growth for this placeholder."],
        )
    tv = fcf * (1 + g) / (wacc - g)
    return ToolResult(
        name=ToolName.CALCULATOR,
        status="ok",
        input_summary="dcf_terminal_placeholder",
        output_lines=[
            f"Placeholder terminal value = {fcf} × (1 + {g}) / ({wacc} − {g}) = {tv:g}.",
        ],
        uncertainty_notes=[
            "Single-stage placeholder on user inputs only; not enterprise value or equity value.",
        ],
    )
