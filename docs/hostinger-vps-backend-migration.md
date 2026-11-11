# Hostinger VPS backend migration (preparation only)

## Current and target hosting

- The existing Hostinger Cloud Startup account continues to serve the Vite static frontend.
- The FastAPI application moves from Vercel to a Linux Hostinger VPS when one is provisioned.
- MongoDB Atlas remains the only application database. Do not deploy the local MongoDB service from the development `docker-compose.yml` to production.
- Meta model calls remain server-side. Never put `MODEL_API_KEY`, MongoDB credentials, or the paper API token in Vite variables or browser storage.
- Kraken remains public-market-data-only for this migration. Paper mode only; no live exchange order path is enabled by this deployment.

Hostinger documents Python as VPS-only because Web and Cloud hosting do not provide the root access needed to install and manage Python dependencies: https://support.hostinger.com/en/articles/3648030-is-python-supported-at-hostinger

## Prepared deployment files

- `compose.vps.yml`: API container plus Caddy reverse proxy; no MongoDB container and no public API container port.
- `deploy/Caddyfile`: HTTPS reverse proxy. Caddy obtains and renews certificates automatically after DNS points to the VPS and ports 80/443 are reachable.
- `.env.production.example`: variable-name template only. Copy it to `.env.production` on the VPS and fill secrets there. The real file must never be committed.
- Existing `backend/Dockerfile` builds the FastAPI application on Python 3.12.

## VPS requirements

Recommended starting point: Hostinger KVM 1 or equivalent, subject to actual workload testing:
- Ubuntu 24.04 LTS (or another currently supported Ubuntu LTS image).
- 1 vCPU, 4 GB RAM, 50 GB NVMe is a reasonable initial baseline for one API container plus Caddy when Atlas is external.
- Upgrade to 2 vCPU / 8 GB RAM if concurrent scans, model calls, or background work show CPU or memory pressure.
- Root access for initial hardening and Docker installation.
- Public IPv4 address and ability to configure DNS A records.
- Hostinger VPS firewall and Ubuntu firewall access.

Hostinger's published KVM specifications: https://support.hostinger.com/en/articles/6976044-parameters-and-limits-of-hosting-plans-in-hostinger

## Network and security requirements

Allow inbound:
- TCP 22 (SSH), preferably restricted to the operator's trusted IP.
- TCP 80 (HTTP; certificate issuance and redirect).
- TCP 443 (HTTPS).

Do not expose 8000, MongoDB 27017, Docker socket, or any database port to the public internet. Use SSH keys, a non-root deploy user, unattended security updates, and Docker least privilege. Keep Hostinger's network firewall and the OS firewall consistent.

## Secrets to configure on the VPS

Copy `.env.production.example` to `.env.production` and configure:
- `MONGODB_URL`: least-privilege MongoDB Atlas application user connection string.
- `MONGODB_DB_NAME`: `action_pilot` unless the existing Atlas database is named differently.
- `API_DOMAIN`: the API hostname selected for the project.
- `CORS_ORIGINS`: exact production frontend origin(s), comma-separated.
- `MODEL_API_KEY`: current Meta model API key.
- Paper variables only when intentionally enabling paper trading: `PAPER_TRADING_ENABLED`, `PAPER_API_TOKEN`, and a deliberately selected `PAPER_INITIAL_BALANCE_USD`. Do not invent a paper balance or turn paper trading on by default.
- Configure any risk-policy environment variables required by the existing risk engine before allowing paper BUY operations.

File permissions: `chmod 600 .env.production`. Do not send secrets in chat, issue comments, logs, or commits. Rotate any credentials that were previously exposed.

## Deployment procedure (after VPS is provisioned)

1. Provision VPS manually in Hostinger; this repository change does not purchase or provision infrastructure.
2. Select Ubuntu LTS, attach an SSH public key, and record the VPS public IPv4.
3. Harden SSH, create a non-root deploy account, install Docker Engine and the Compose plugin.
4. Configure firewall rules for SSH (restricted), 80 and 443 only.
5. Add DNS A record for the selected API hostname to the VPS IPv4. Wait for DNS propagation.
6. Create `.env.production` on the server using the template and secure file permissions.
7. Clone the approved repository revision and run `docker compose -f compose.vps.yml up -d --build`.
8. Verify `https://API_DOMAIN/health` and `https://API_DOMAIN/api/health` report database connectivity. Check container health and logs without printing secrets.
9. Test authenticated paper endpoints using a dedicated paper token and a disposable paper account. Confirm all responses state paper mode and no exchange order was submitted.
10. Update the frontend build's `VITE_API_URL` to the new API origin in the Hostinger deployment workflow, then deploy the static frontend.
11. Verify browser CORS, login/session behavior, scans, paper account, protective-exit monitoring, and error handling from the real Hostinger frontend.
12. Keep the Vercel API available as rollback until the new API has passed the full smoke test. Do not delete Vercel configuration or switch production traffic before explicit approval.

## Cutover and rollback

Cutover is a separate operator-approved step. Before cutover, capture the currently deployed Vercel commit and environment configuration (not secret values). Rollback means restoring the previous `VITE_API_URL` and redeploying the static frontend. Keep both API deployments on the same compatible application revision during the transition.

## Not done by this preparation

- No VPS has been purchased or provisioned.
- No DNS records have been changed.
- No secrets have been copied or rotated.
- No frontend API URL has been switched.
- No Vercel service has been removed.
- No live trading or live Kraken order capability has been enabled.
