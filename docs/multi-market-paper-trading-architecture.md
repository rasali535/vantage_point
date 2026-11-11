# Multi-Market Paper Trading Architecture

## Product decision

Ras Ali AI Trader supports two first-class markets:

- **Crypto spot** — Kraken is the initial exchange adapter; do not assume BTC/USD is the only instrument.
- **Forex** — a broker-neutral FX market with multiple independently configurable broker adapters.

The initial delivery is strictly **paper trading and market research**. Live trading is not part of this implementation. No live broker credentials, live endpoints, or live order routes are to be enabled.

## Current implementation constraints

The current backend is not yet multi-market:

- `backend/routes/trading.py` obtains a `KrakenAgent` directly and `scan_and_analyze()` reads one `TRADING_PAIR` (default `BTC/USD`).
- The paper engine accepts only USD-quoted spot pairs and models cash-funded long positions; it does not model FX base units, pip values, FX margin, swaps, or broker contract rules.
- Paper account and position data are currently held in one MongoDB account document, with pair-keyed positions.
- The frontend and status response describe Kraken as the only market-data source.
- The existing deterministic risk policy is configured at 0.5% max trade risk, 2% daily loss, 5% drawdown, 5 open positions, 1x maximum leverage, and mandatory stop-loss.

These are explicit migration points, not reasons to replace the existing six-agent system.

## Target architecture

```
Dashboard / API
      |
Market & Instrument Registry
      |
Market Data Router ----------------------+
      |                                  |
Crypto Market Adapter                 FX Market Data Adapters
      |                                  |
Kraken public market data       OANDA / FXCM / IBKR / other providers
      |                                  |
      +---------- Normalized Quotes -----+
                         |
                Multi-Market Scanner
                         |
       Six agents: intelligence, technical,
       strategy, risk advisory, execution gate,
       performance
                         |
              Deterministic Risk Engine
                         |
                 Paper Execution Router
                    /          \
             Crypto Paper    FX Paper
                Engine        Engine
                    \          /
                  Unified Paper Ledger
                         |
                 Audit / Performance
```

### 1. Instrument and market model

Introduce a canonical instrument registry. Each instrument has:

- Stable instrument ID and market type (`crypto_spot` or `forex`).
- Base and quote currencies, normalized symbol, provider-specific symbols.
- Price precision, quantity precision, minimum size, size increment and minimum notional.
- FX pip size, contract/unit convention, and trading-session calendar where applicable.
- Supported data providers and supported paper execution adapters.

Discover the available instruments from connected providers where possible. Do not claim that every broker supports every pair. The UI should distinguish available, unsupported, stale and unavailable instruments. Include major, minor and exotic FX pairs when a selected provider offers them; USD/BWP must be shown only if a provider actually supplies it.

### 2. Provider boundaries

Keep market-data providers separate from execution brokers. A provider can supply quotes/candles without being permitted to execute orders.

Define typed interfaces for:

- `MarketDataProvider`: instruments, quote, candles, stream/heartbeat, provider status.
- `PaperBrokerAdapter`: account capabilities, instrument discovery, paper order simulation or broker-native practice order, order status and fills.
- `InstrumentMetadataProvider`: precision, size increments, pip/contract rules and sessions.

Initial adapter sequence:

1. **Kraken** — retain the existing public spot market-data adapter and add instrument discovery; no private API calls.
2. **OANDA Practice** — first FX integration candidate because OANDA documents a dedicated fxTrade Practice REST and streaming environment.
3. **FXCM Demo** — second FX adapter candidate; keep the demo endpoint and credentials isolated from any live endpoint.
4. **Interactive Brokers Paper** — later adapter after validating account eligibility, paper API access and market-data subscription requirements.

Adapters must expose environment identity and capabilities. A demo or practice environment is not automatically available to every account or jurisdiction. Verify access, supported products, data entitlements, fees and local regulatory availability before implementation is marked complete.

### 3. Normalized market data

Normalize provider data into one internal quote/candle schema while preserving:

- Provider, instrument ID, bid, ask, mid, timestamp and sequence where available.
- Candle interval, OHLC, volume if supplied, and source.
- Spread, quote age and market/session state.
- Provider errors and stale-data status.

Never silently substitute another provider or fabricated prices. A stale or missing quote blocks analysis that requires current prices and always blocks paper fills. Persist source and timestamp with every scan and simulated fill.

### 4. Six-agent orchestration

Retain the existing six roles. Pass a typed market context rather than a Kraken-specific pair/ticker:

- Market Intelligence: verified market and macro context.
- Technical Analyst: market-aware EMA/RSI/ATR and FX pip-aware levels.
- Strategy: typed proposal with instrument, market, direction, entry, stop, target and rationale.
- Risk Manager: advisory only; it cannot approve or bypass deterministic controls.
- Execution: paper-only capability check and deterministic risk decision.
- Performance: calculate from the unified, closed paper ledger, segmented by market, instrument and broker.

The AI must not receive broker credentials. The deterministic risk engine remains authoritative.

### 5. Unified paper account and risk

Keep the approved initial virtual equity at **USD 1,000**. Use one unified USD-denominated paper portfolio with market and broker sub-ledgers so Forex and Crypto compete for the same risk and equity budget rather than receiving independent, additive capital.

Retain the currently approved limits:

- Maximum planned loss per trade: 0.5% of current eligible equity.
- Daily loss threshold: 2%.
- Maximum drawdown threshold: 5%.
- Maximum open positions: 5 across both markets.
- Maximum leverage: 1x.
- Stop-loss required.

Do not increase leverage to simulate conventional leveraged FX. Initial FX simulation must be unleveraged (1x) and fully collateralized. Any future margin model requires a separately reviewed risk design and explicit approval.

FX sizing must calculate pip value and quote-to-account-currency conversion correctly. Risk checks must include spread, simulated slippage, commissions, conversion cost and any applicable financing/swap assumptions. If a required conversion quote or instrument specification is missing or stale, reject the proposal/order.

Use Decimal arithmetic and provider-specific precision/size increments. The engine must reject invalid sizes, unsupported instruments, short/oversold positions where not explicitly modeled, duplicate idempotency keys, stale prices and risk-limit breaches.

### 6. Paper execution and persistence

Refactor the current spot-only paper engine behind market-specific execution models while preserving its tested behavior. The common paper order lifecycle should record:

- Account, market, instrument, broker/provider and paper environment.
- Side, quantity/unit convention, requested price, bid/ask reference, simulated fill.
- Spread, slippage, fees, conversion and financing assumptions.
- Stop-loss, take-profit, risk decision and rejection reasons.
- Idempotency key, timestamps, status and ledger version.

Keep the MongoDB ledger auditable and concurrency-safe. Add schema/version fields and migrations or backward-compatible readers for existing Kraken paper account documents. Do not discard or reinterpret existing records.

Protective exits must use the same instrument metadata, quote source and fill model as entry orders. Monitoring should report missing/stale prices and must never assume a position has been protected when its market is closed or data is unavailable.

### 7. API and dashboard

Expose market discovery, provider status, quotes/candles, multi-market scans, paper account, paper orders, positions, protective monitoring and performance through typed APIs.

Dashboard navigation should provide:

- **Overview** — unified equity, risk usage and portfolio exposure.
- **Crypto** — Kraken instruments, crypto scans and paper positions.
- **Forex** — provider selector, pair universe, FX scans, pip-based risk and paper positions.
- **Providers** — data vs execution capability, environment, health and connection state.
- **Paper portfolio** — combined account and market-specific breakdown.
- **Performance** — combined and per-market metrics.

Do not expose credential values to the browser. Store only paper-session access material in memory or a secure server-side session; never localStorage. Status must explicitly show `paper_only` and `live_execution_disabled`.

### 8. Safety invariants

- Hard-code live order execution as unavailable in this release; a UI flag or environment variable must not turn it on.
- Do not configure or request live broker credentials.
- No adapter may silently fall back from practice/demo to live.
- AI agents never access credentials and never call broker order APIs.
- Every proposed order passes the deterministic risk engine.
- Fail closed on missing market data, stale quotes, missing instrument metadata, database failures, conversion-rate failures and provider errors.
- Every paper fill must persist `execution_mode=paper` and `exchange_order_submitted=false`.
- Paper trading must never invoke a live/private exchange or broker order endpoint.
- Add tests that assert the absence of live order calls, not only the presence of paper fills.

## Implementation phases

### Phase 0 — Baseline and compatibility
- Resolve the outstanding frontend-to-Render API PR before UI work depends on it.
- Capture existing API contracts and paper-ledger fixtures.
- Add regression tests for current Kraken paper behavior and existing $1,000 account.
- Correct stale README claims that currently say no paper orders can be submitted, after confirming the deployed behavior.

### Phase 1 — Market abstraction and registry
- Add typed market/instrument/provider contracts.
- Adapt Kraken public ticker/OHLC behind the market-data interface.
- Add instrument discovery and provider capability/status APIs.
- Make scans accept an explicit supported instrument rather than a single global `TRADING_PAIR`.
- Add tests for unsupported, stale and unavailable instruments.

### Phase 2 — Multi-market risk and paper domain
- Introduce FX pip/contract/precision and currency conversion models.
- Add FX paper pricing, spread/slippage, sizing and fully collateralized 1x positions.
- Unify cross-market exposure, equity, position count and loss limits.
- Preserve the current Kraken paper ledger through backward-compatible migration.
- Add property, boundary, idempotency, concurrency and fail-closed tests.

### Phase 3 — FX practice data and broker adapters
- Integrate OANDA Practice market data and instrument metadata first.
- Add OANDA Practice paper execution only after adapter tests prove that requests are pinned to the practice host.
- Add FXCM Demo next, then assess IBKR Paper.
- Require explicit provider selection and show account/data eligibility limitations.
- Do not configure live endpoints or live credentials.

### Phase 4 — Agents and dashboard
- Upgrade orchestration to typed multi-market contexts and market-specific prompts.
- Add market selector, Forex workspace, provider health and unified paper portfolio.
- Show per-market and consolidated risk/performance.
- Add user-visible stale-data, session-closed and provider-unavailable states.

### Phase 5 — Validation and release
- Run full backend safety suite, frontend typecheck/build, dependency/security checks and provider contract tests.
- Run end-to-end paper tests for crypto and FX, including mixed-market exposure against one $1,000 account.
- Verify every fill is paper-only and no live order endpoint is reachable.
- Deploy only after review and explicit operator approval.

## Acceptance criteria

1. BTC/USD is no longer the only selectable instrument; supported Kraken spot instruments and provider-discovered FX pairs can be selected.
2. Forex and Crypto scans run through the same six-agent workflow using normalized, source-attributed data.
3. FX calculations correctly handle pips, quote currency, USD conversion, precision and provider minimum sizes.
4. One $1,000 virtual USD portfolio and one deterministic risk budget cover both markets.
5. Paper fills and protective exits are idempotent, auditable and use realistic spread/slippage/fee assumptions.
6. Provider outages, stale quotes, closed sessions, missing conversions and unknown instruments fail closed.
7. No live credentials, live order routes, or live order submissions are present or enabled.
8. Existing Kraken paper account data and behavior remain backward-compatible.
