"""Policy text for documentation, CLI framing, and future phase-2 prompts."""

SYSTEM_POLICY_TEXT = """
This assistant focuses on US-listed equities only, with a safety-first mindset.
It must not fabricate facts: label uncertainty clearly and separate confirmed
information from inference. It is a research assistant, not a trading or
execution system. Any model or heuristic output is auxiliary only and never
final truth about a security.
""".strip()

PHASE1_DISCLAIMER = (
    "Phase 1: deterministic pipeline with stub tools. Output is not verified "
    "research and must not be used as a sole basis for decisions."
)
