# Render deployment

The root `render.yaml` deploys one public gateway and two private detector
services in Render's Singapore region:

```text
Cloudflare Pages Function -> fraudster-gateway -> fraudster-text
                                              \-> fraudster-url
```

Only `fraudster-gateway` is public. The text and URL services are Render private
services and have no public URL. Preview environments are disabled to avoid
creating duplicate paid services.

## Deploy

1. In Render, create a **Blueprint** from `FaisalTabrez/Fraudster` and use the
   root `render.yaml`.
2. Review the cost before applying it. The gateway uses Render's free web plan;
   the two private services use the smallest private-service plan because Render
   does not offer free private services.
3. When prompted, enter `TEXT_API_KEY` as a secret. Never put the key in GitHub,
   Cloudflare, `.env`, logs, screenshots, or demo messages.
4. Apply the Blueprint and wait for all three services to deploy. Render injects
   the private `host:port` values into the gateway; the gateway normalizes those
   fixed service addresses to internal HTTP URLs.
5. Copy the public `https://fraudster-gateway-...onrender.com` origin. In the
   Cloudflare Pages project, set `GATEWAY_ORIGIN` to that origin for Production
   and redeploy the Pages project. Do not add `/api`, a trailing path, query, or
   credentials.

## Verify before the demo

Use synthetic text only. Replace `<gateway-origin>` and `<pages-origin>` with
the deployed HTTPS origins:

```powershell
Invoke-RestMethod <gateway-origin>/health/live
Invoke-RestMethod <gateway-origin>/health/ready
py -3 scripts\smoke.py --base-url <gateway-origin> --expect live-no-key
py -3 scripts\smoke.py --base-url <pages-origin>/api --expect live-no-key
```

`/health/live` is the Render deployment health check and only proves that the
gateway process is running. Do not call the stack ready until `/health/ready`
returns HTTP 200 with both detectors ready and a synthetic request through the
Cloudflare `/api` path completes. A configured text service can still encounter
a provider error, so the final request is required.

The free gateway can spin down when idle. Open `/health/live` shortly before the
demo, or upgrade only that service if avoiding cold starts is worth the added
cost. Detector failures stay explicit; they must not be presented as zero risk.
