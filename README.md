# stock_research_agent

Minimal **phase 1** prototype: a **deterministic** CLI pipeline for a **US-equity-only** research assistant. Tools are **stubs**; there is **no LLM** and no live web retrieval. This is **not** trading or execution software and **not** financial advice.

## Phase 1 vs phase 2

- **Phase 1 (current):** scope gate → conservative routing → stub tools → rule-based `StructuredAnswer`. Fully local and reproducible.
- **Phase 2 (future):** optional LLM JSON synthesis using the same schemas (not implemented here).

## Setup

Requires **Python 3.10+**.

```bash
cd stock_research_agent
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # optional; sets LOG_LEVEL
```

## Run

From the project root (`stock_research_agent/`):

```bash
python -m app.main "Your question here"
# or
python -m app.main -q "Your question here"
```

## Layout

- `app/main.py` — CLI
- `app/agent.py` — scope, orchestration, synthesis
- `app/router.py` — tool routing
- `app/schemas.py` — Pydantic models
- `app/prompts.py` — policy strings
- `app/tools/` — stub tools + narrow calculator templates

## Limitations

Stub outputs are **operational status only**, not verified research. Scope uses a small **static symbol map** (local, not a data feed) plus explicit US market cues; unmapped names/tickers need clarification or explicit US context.
