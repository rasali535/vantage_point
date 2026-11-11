# Ras Ali AI Trader

Ras Ali AI Trader is the planned evolution of ActionPilot, maintained in this repository. It is a crypto-first trading research and execution platform, starting with Kraken and designed for future exchange/provider adapters.

## Deployment architecture

- **Vercel** hosts the React frontend and FastAPI backend as services in one deployment.
- **MongoDB Atlas** is the persistent application database. Configure the connection string as the Vercel environment variable `MONGODB_URL`.
- **Kraken** is the initial exchange integration. Exchange credentials belong only in server-side environment variables and must never be exposed to the browser or AI agents.
- **AI agents** produce analysis and proposals. A separate deterministic risk engine must approve every order before an execution adapter can submit it.

There is no Vultr dependency. Do not use the retired Vultr VM, its IP address, SSH scripts, or provisioning scripts.

## Vercel routing

The root `vercel.json` defines two Vercel services:

- `frontend/` serves the Vite application.
- `backend/` exposes the FastAPI application from `main:app`.

Requests to `/api` and `/api/*` are routed to the backend service. All other requests are routed to the frontend service. The frontend uses same-origin API paths in production.

## Required environment configuration

Set secrets in the Vercel project environment settings, not in source files:

| Variable | Purpose |
| --- | --- |
| `MONGODB_URL` | MongoDB Atlas connection URI |
| `KRAKEN_API_KEY` | Server-side Kraken API key |
| `KRAKEN_API_SECRET` | Server-side Kraken API secret |
| `TRADING_PAIR` | Explicitly configured Kraken market pair |
| `TRADE_SIZE_USD` | Maximum proposed notional size for the current strategy |
| `FEATHERLESS_API_KEY` | AI model provider, when enabled |
| `GEMINI_API_KEY` | Gemini provider, when enabled |

Do not commit real values or share them in logs. Use a least-privilege Kraken key; withdrawals must remain disabled.

## Local development

Install frontend dependencies from `frontend/` and backend dependencies from `backend/requirements.txt`. For local MongoDB development, `docker-compose.yml` provides a local MongoDB service. Configure a local `.env` file and never commit it.

## Trading safety requirements

The platform must default to simulation/paper mode. Live execution remains disabled until the exchange adapter, authentication, deterministic risk checks, order lifecycle, persistence and audit trail have been tested.

Required controls include:

- Explicit separation of live, paper and mock data.
- Fail-closed behavior when MongoDB, market data, AI analysis or risk validation is unavailable.
- No AI agent access to exchange credentials.
- Deterministic limits and a kill switch enforced outside the LLM.
- Order status and fills recorded only after exchange confirmation.
- Idempotency and durable audit records for every order attempt.

## Security notice

Historical repository commits contained credentials and remote-server access details. Deleting the affected files from the current branch does not erase those values from Git history. Rotate/revoke exposed Kraken and SSH credentials, review API-key permissions, and coordinate history cleanup before treating the repository as safe for production use.
