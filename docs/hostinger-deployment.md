# Hostinger frontend deployment

The frontend is a Vite/React static site. GitHub Actions builds it with Node.js in GitHub's hosted runner; neither a local Node.js installation nor a Hostinger Node.js runtime is required.

## Architecture

- Hostinger serves the compiled static frontend from the domain's document root.
- Vercel continues to host the FastAPI backend at `https://actionpilot.vercel.app`.
- MongoDB Atlas remains the application database.
- The build sets the public `VITE_API_URL` to the Vercel API origin. No backend credentials are included in the frontend build.

## GitHub Actions secrets

In **Repository → Settings → Secrets and variables → Actions**, create these repository secrets:

| Secret | Value |
| --- | --- |
| `HOSTINGER_FTP_SERVER` | FTP hostname shown in Hostinger (hostname only; no scheme or path) |
| `HOSTINGER_FTP_USERNAME` | FTP account username |
| `HOSTINGER_FTP_PASSWORD` | FTP account password |
| `HOSTINGER_FTP_SERVER_DIR` | Exact remote directory for this domain's document root, with a trailing slash |

Use the FTP account created for this website and restrict it to the website's document root where Hostinger allows this. Do not paste credentials into chat, source files, workflow logs, or commits.

The remote directory varies by Hostinger account and FTP user. Confirm it in Hostinger's FTP Accounts / connection details. It may be `/public_html/` or a domain-specific path such as `/domains/example.com/public_html/`; do not guess. The workflow deliberately requires the path as a secret so it cannot silently deploy to the wrong directory.

## Deployment

- A push to `main` builds and deploys `frontend/dist/` to the configured Hostinger directory.
- A manual run is available under **Actions → Hostinger static frontend deployment → Run workflow**.
- Pull requests are built by the existing CI workflow; they do not deploy.
- If FTP secrets are missing, the workflow still verifies the production build and reports that deployment was skipped.
- The workflow uses FTPS on port 21 and does not perform a destructive clean-slate of the destination.

## Hostinger site configuration

This is a static deployment. The Hostinger site should serve files from the same remote directory configured in `HOSTINGER_FTP_SERVER_DIR`. Do not configure this deployment as a PHP/Composer application or a Node.js application. The `frontend/public/.htaccess` file is copied into the Vite output and provides the Apache SPA fallback.

## API CORS

The Vercel backend's `CORS_ORIGINS` environment variable must include the exact Hostinger site origin, for example:

```text
https://darkblue-turkey-867661.hostingersite.com
```

Keep any other origins already required by the application. Redeploy the Vercel backend after changing its environment variable.
