# Ras Ali AI Trader

Ras Ali AI Trader is the evolution of ActionPilot, maintained in this repository. It is a multi-market trading platform being built for Crypto and Forex, with Kraken as the initial crypto market-data adapter and broker-neutral Forex adapters planned. The current autonomous execution implementation is paper-only and initially supports configured USD-quoted Kraken spot pairs; Forex automation follows after the FX data, sizing and broker-practice adapters are implemented.

## Deployment architecture

- **Vercel Services** hosts the React/Vite frontend and FastAPI backend in one project and deployment.
- **MongoDB Atlas** is the persistent application database. Configure `MONGODB_URL` in Vercel's server-side environment.
- **Kraken Spot REST** supplies public ticker and OHLC market data. Private account reads are opt-in and disabled by default.
- **Meta Model API** (`muse-spark-1.3` by default) powers the research, risk and strategy agents. The API key remains server-side. They do not receive exchange credentials.
- **Live order execution is disabled permanently in the current release.** The paper engine supports simulated entries and exits; the autonomous paper supervisor can be enabled by an authenticated operator.

There is no Vultr dependency. Do not use the retired Vultr VM, its IP address, SSH scripts, or provisioning scripts.

## Hostinger static frontend deployment

The frontend can be deployed to Hostinger without a local Node.js installation or a Hostinger Node.js runtime. GitHub Actions builds `frontend/` using Node.js on a GitHub-hosted runner and uploads only `frontend/dist/` over FTPS. The FastAPI backend remains on Vercel and MongoDB Atlas remains the database. Configure the four `HOSTINGER_FTP_*` repository secrets described in [the Hostinger deployment guide](docs/hostinger-deployment.md). The workflow does not deploy from pull requests and will skip the upload until all four secrets are configured.

## Vercel routing

The root `vercel.json` defines two services. The Vercel project framework must be set to **Services**:

- `frontend/` uses the Vite framework.
- `backend/` uses FastAPI with entrypoint `main:app`.

Requests to `/api` and `/api/*` route to the backend. All other requests route to the frontend. The frontend uses same-origin API paths in production.

## Required environment configuration

Set secrets in Vercel project environment settings, not in source files.

| Variable | Purpose |
| --- | --- |
| `MONGODB_URL` | MongoDB Atlas connection URI |
| `MONGODB_DB_NAME` | Optional database name; defaults to `action_pilot` |
| `CORS_ORIGINS` | Comma-separated allowed frontend origins |
| `KRAKEN_API_KEY` | Server-side Kraken API key |
| `KRAKEN_API_SECRET` | Server-side Kraken API secret (base64) |
| `KRAKEN_ACCOUNT_READS_ENABLED` | Keep `false` until credentials are rotated and read-only permissions are verified |
| `TRADING_PAIR` | Kraken market pair to analyse; defaults to `BTC/USD` |
| `MODEL_API_KEY` | Meta Model API bearer key; create it in the Meta Model API dashboard |
| `META_MODEL_API_BASE_URL` | Optional Meta API base URL; defaults to `https://api.meta.ai/v1` |
| `RESEARCH_MODEL` | Market intelligence model; defaults to Meta `muse-spark-1.3` |
| `RISK_MODEL` | Risk analysis model; defaults to Meta `muse-spark-1.3` |
| `TRADING_MODEL` | Strategy synthesis model; defaults to Meta `muse-spark-1.3` |
| `SPEECHMATICS_API_KEY` | Optional audio transcription provider key |
| `RISK_MAX_TRADE_RISK_PCT` | Operator-defined maximum stop-loss risk per proposed trade |
| `RISK_MAX_DAILY_LOSS_PCT` | Operator-defined daily loss ceiling |
| `RISK_MAX_DRAWDOWN_PCT` | Operator-defined maximum drawdown |
| `RISK_MAX_OPEN_POSITIONS` | Operator-defined maximum concurrent positions |
| `RISK_MAX_LEVERAGE` | Operator-defined maximum leverage |
| `RISK_REQUIRE_STOP_LOSS` | Explicit `true` or `false`; recommended `true` |
| `PAPER_TRADING_ENABLED` | Set `true` only when paper simulation is ready; defaults to `false` |
| `PAPER_API_TOKEN` | Server-side secret required in the `X-Paper-Token` header |
| `PAPER_INITIAL_BALANCE_USD` | Explicit starting virtual USD balance; no default is applied |
| `PAPER_FEE_RATE` | Simulated fee fraction; defaults to `0.0026` (0.26%) |
| `PAPER_SLIPPAGE_BPS` | Simulated slippage in basis points; defaults to `5` |
| `PAPER_AUTOTRADING_ALLOWED` | Server-side permission for autonomous paper trading; defaults to `true`, but the operator must still start it |
| `PAPER_AUTOTRADE_PAIRS` | Comma-separated USD-quoted Kraken spot pairs; defaults to a diversified BTC, ETH, SOL, XRP, ADA, DOGE, LTC, LINK, DOT and BCH basket |
| `PAPER_AUTOTRADING_SCAN_SECONDS` | AI analysis interval; defaults to `300` seconds |
| `PAPER_AUTOTRADING_MONITOR_SECONDS` | Protective exit check interval; defaults to `20` seconds |
| `PAPER_AUTOTRADING_MIN_CONFIDENCE` | Minimum AI strategy confidence; defaults to `0.70` |
| `PAPER_AUTOTRADING_CANDLE_INTERVAL` | Kraken candle interval in minutes; defaults to `60` |

Do not commit real values or expose them in logs. Use a least-privilege Kraken key; withdrawals must remain disabled. Do not enable private account reads until exposed credentials have been rotated.

## Database and runtime

The backend uses the native PyMongo asynchronous client, reused within the ASGI process with a small per-instance connection pool suited to serverless workloads. If MongoDB is not configured or is unavailable, stateful routes return HTTP 503. They do not silently switch to mock balances, mock market data, or fabricated ledger entries.

The default database name remains `action_pilot` to preserve the existing collection namespace. The trading routes use the existing `trading_ledger`, `boardroom_history`, and `audit_logs` collections.

## Meta AI provider

All AI chat, market research, risk analysis, strategy synthesis and meeting-note analysis use Meta's official Model API at `https://api.meta.ai/v1/chat/completions`. Configure `MODEL_API_KEY` in Vercel server-side environment variables. The default model is `muse-spark-1.3`; `RESEARCH_MODEL`, `RISK_MODEL`, and `TRADING_MODEL` can override it independently. No Featherless endpoint or API key is used.

## Kraken adapter

Public market data is fetched from Kraken Spot REST `Ticker` and `OHLC`. Private `Balance` requests use server-side API signing but remain disabled by default until credentials are rotated and the API key's read-only permissions are verified. The adapter no longer depends on the Kraken CLI or a Docker-installed binary.

## Trading safety requirements

Meta Model API and transcription provider failures are returned as service errors; no synthetic analysis or transcript is substituted. The platform runs in **research + optional paper-simulation mode**. Live execution remains disabled. Paper simulation is disabled unless `PAPER_TRADING_ENABLED=true`, `PAPER_API_TOKEN` and `PAPER_INITIAL_BALANCE_USD` are configured. The `/api/trading/paper/account`, `/api/trading/paper/orders` GET/POST and `/api/trading/paper/monitor` POST routes require the `X-Paper-Token` header. Paper fills use the latest public Kraken ticker, configurable fee and slippage assumptions, and a single MongoDB account document with optimistic version checks. Paper BUY orders require a configured deterministic risk policy and a stop-loss when policy requires one. Spot SELL orders can only reduce an existing virtual position; shorting is rejected. Simulated fills are marked `execution_mode=paper` and `exchange_order_submitted=false`. The paper engine does not call Kraken private endpoints or order placement.

The Paper Trading workspace displays virtual equity, cash, positions and simulated fills. Its authenticated autonomous supervisor can analyse configured Kraken USD-quoted spot pairs, calculate a risk-sized position, simulate entries, close a held position on a confirmed opposite signal, and monitor stored stop-loss/take-profit exits. Start/stop controls are protected by the paper token. Stopping the supervisor blocks new entries while continuing protective monitoring for already-open virtual positions. The worker uses a MongoDB lease to reduce duplicate execution across API instances. The current worker runs inside the FastAPI process; a Render Free web service may sleep while idle, so reliable continuous operation requires an always-on deployment. This phase does not yet automate Forex pairs; the multi-market FX adapter and FX-specific sizing must be completed first. Before any live execution can be enabled, the following must be implemented and tested:

- Authentication and authorization for every state-changing route.
- A separately reviewed deterministic risk gate for any future live order path, using operator-configured limits. Missing limits must continue to reject every proposal; no unconfirmed defaults are applied.
- A kill switch and explicit operator approval for any transition to live execution.
- Idempotent live order submission and exchange-confirmed order/fill reconciliation.
- Durable audit records for every proposal, approval, rejection, order attempt, and fill.
- Automated tests proving that database, model, market-data, or risk failures cannot result in an order.

## CI

GitHub Actions runs backend compilation and safety tests plus the frontend TypeScript/Vite production build. The repository still has a legacy ESLint backlog, so lint is tracked separately rather than used as a release gate. Vercel builds the frontend and backend services as part of the preview deployment.

## Security notice

Historical repository commits contained credentials and remote-server access details. Deleting affected files from the current branch does not erase values from Git history. Rotate/revoke exposed Kraken and SSH credentials, review API-key permissions, and coordinate history cleanup before treating the repository as safe for production use.


## Six-agent architecture

The market scan is orchestrated by six distinct agents:

1. **Market Intelligence** — Meta Model API analysis of verified Kraken ticker and candle data only.
2. **Technical Analyst** — deterministic EMA, RSI and ATR calculations; insufficient history returns HOLD.
3. **Strategy** — Meta Model API synthesizes the market, technical and risk findings into a typed BUY/SELL/HOLD research proposal.
4. **Risk Manager** — Meta Model API provides downside and uncertainty analysis. It is advisory only; the deterministic risk engine is authoritative.
5. **Execution** — validates readiness and configured risk policy. This stage does not submit orders; sizing, human approval, authentication, idempotency and exchange-confirmed lifecycle remain mandatory before any execution implementation.
6. **Performance** — computes performance only from closed, exchange-confirmed ledger records; it reports insufficient history rather than fabricating metrics.

The six-agent cycle is invoked by `POST /api/trading/scan`. Its complete structured output is persisted to MongoDB boardroom history and its summary to the audit log. All responses are research-only and `execution_enabled` remains false.

Optional model overrides: `MARKET_INTELLIGENCE_MODEL`, `RISK_MODEL`, and `TRADING_MODEL`. All default to Meta `muse-spark-1.3`.
