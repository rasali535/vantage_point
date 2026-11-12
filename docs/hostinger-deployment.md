# Hostinger frontend deployment

The frontend is a Vite/React static site. GitHub Actions builds it with Node.js in GitHub's hosted runner; neither a local Node.js installation nor a Hostinger Node.js runtime is required.

## Architecture

- Hostinger serves the compiled static frontend from the domain's document root.
- Render hosts the FastAPI backend at `https://vantage-point-1qv7.onrender.com` (Virginia; Frankfurt and Oregon egress is rejected by the Meta Model API).
- MongoDB Atlas remains the application database.
- The build sets the public `VITE_API_URL` to the Render API origin. No backend credentials are included in the frontend build.

## GitHub Actions secrets

In **Repository → Settings → Secrets and variables → Actions**, create these repository secrets:

| Secret | Value |
| --- | --- |
| `HOSTINGER_SFTP_HOST` | The IP address shown in Hostinger hPanel under Advanced → SSH Access (use the displayed IP, not the FTP hostname) |
| `HOSTINGER_SFTP_USERNAME` | The FTP/SSH username shown in the same section |
| `HOSTINGER_SFTP_PRIVATE_KEY` | The private key matching the public key added to Hostinger |
| `HOSTINGER_SFTP_REMOTE_PATH` | Exact absolute path to this website's document root |

Do not paste credentials or private keys into chat, source files, workflow logs, or commits.

### Configure an SSH key

1. Generate a dedicated Ed25519 key pair for this deployment on a trusted computer:
   `ssh-keygen -t ed25519 -C "vantage-point-hostinger-deploy" -f hostinger_vantage_point`
2. In Hostinger hPanel, open **Advanced → SSH Access** (or **Remote Access → SSH/SFTP Keys**, depending on the hosting interface) and add the contents of `hostinger_vantage_point.pub`.
3. Add the contents of the private `hostinger_vantage_point` file as the GitHub Actions secret `HOSTINGER_SFTP_PRIVATE_KEY`. Keep the private key private.
4. Copy the IP address and SSH username shown by Hostinger into the matching GitHub secrets. The workflow uses Hostinger's SFTP port **65002**.
5. Confirm the exact remote document-root path in Hostinger File Manager / FTP or SSH details. Do not guess it; it varies by account and domain.

Hostinger's SFTP connection instructions specify the SSH Access IP, FTP/SSH username, and port 65002. See [Hostinger's SFTP guide](https://support.hostinger.com/en/articles/5972689-how-to-connect-to-your-hosting-using-sftp).

## Deployment

- A push to `main` builds and deploys `frontend/dist/` to the configured Hostinger directory.
- A manual run is available under **Actions → Hostinger static frontend deployment → Run workflow**.
- Pull requests are built by the existing CI workflow; they do not deploy.
- If SFTP secrets are missing, the workflow still verifies the production build and reports that deployment was skipped.
- Deployment uses SFTP over SSH on port 65002. It does not delete the destination directory or perform a destructive clean-slate.

## Hostinger site configuration

This is a static deployment. The Hostinger site should serve files from the same remote directory configured in `HOSTINGER_SFTP_REMOTE_PATH`. Do not configure this deployment as a PHP/Composer application or a Node.js application. The `frontend/public/.htaccess` file is copied into the Vite output and provides the Apache SPA fallback.

## API CORS

The Render backend's `CORS_ORIGINS` environment variable must include the exact Hostinger site origin, for example:

```text
https://darkblue-turkey-867661.hostingersite.com
```

Keep any other origins already required by the application. Redeploy the Render backend after changing its environment variable.
