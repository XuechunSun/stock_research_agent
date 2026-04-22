# Sample test prompts (manual)

## In scope — static map + calculator

- `MSFT EPS 5.2 P/E 35 implied price?`
- `prior 100 current 121 yoy growth` (with YoY wording or prior/current pattern per calculator)

## In scope — static map + public / time-sensitive (expect web_search routed)

- `Latest NVDA earnings headlines`
- `What was announced in recent MSFT 8-K filing` (public-filing cue)

## In scope — explicit US context, no company name

- `Explain margin of safety for US stocks on NYSE`

## Router — should **not** route web_search (no time/public cue)

- `What does DCF mean for equity valuation?`

## Router — file_search cue (stub)

- `Summarize my notes on AAPL in my file research.txt`

## Router — stock_model (auxiliary cue)

- `Give an auxiliary signal view for NVDA risk screen (mock only)`

## Needs clarification

- `Is Rivian stock reasonably valued?` (Rivian not in phase-1 static map; no explicit US listing phrase) → expect NEEDS_CLARIFICATION
- `Compare AAPL and RIVN` (RIVN unmapped) → expect NEEDS_CLARIFICATION
- `Meta` / `Palo Alto Networks` / `Is AMZN overvalued?` (in static map) → in scope when not contradicted

## Out of scope

- `Buy Bitcoin now`
- `Best pizza in NYC`

## Calculator unsupported (valuation language, no template)

- `Is COST fairly valued vs peers?` (no numeric template)
