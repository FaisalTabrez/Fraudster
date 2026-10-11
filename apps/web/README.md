# Cloudflare Pages deployment

The Fraudster browser app is a Vite static site. Cloudflare Pages can build it from the GitHub repository. Its only browser API is `/api/v1/analyze`; the Pages Function in `functions/api/v1/analyze.js` forwards that request to a separately hosted HTTPS gateway. The text, URL, and OCR services must remain behind the gateway.

## Create the Pages project

In Cloudflare, open **Workers & Pages → Create application → Pages → Import an existing Git repository** and select `FaisalTabrez/Fraudster`. Configure:

| Setting | Value |
| --- | --- |
| Project name | `fraudster` (or another available name) |
| Production branch | `main` |
| Root directory | `apps/web` |
| Framework preset | `React (Vite)` |
| Build command | `npm run build` |
| Build output directory | `dist` |

The `.node-version` file selects Node 24, as required by `package.json`. Deploy with Git integration so the Pages Function is included; dashboard Direct Upload does not support a source `functions` directory.

## Connect the API

Host the FastAPI gateway separately at a public HTTPS origin, such as `https://gateway.example.com`. In the Pages project, set `GATEWAY_ORIGIN` to that **origin only** under **Settings → Variables and Secrets** for both Production and Preview as needed. Do not include `/api`, `/v1/analyze`, a trailing path, credentials, a query, or a fragment. Do not use a `VITE_` variable for the gateway address or provider secrets. Redeploy after changing the setting.

Until the gateway is deployed and `GATEWAY_ORIGIN` is configured, the site loads but analysis returns HTTP 503 with a clear configuration message. Pages only hosts the frontend and Function; it does not run the Python gateway or detectors. A fixture-mode gateway is suitable for a labeled demo only. Its results must remain identified as demo data.

After deployment, open the `*.pages.dev` URL and submit a test message. The request should go to `/api/v1/analyze` on the Pages domain. If it returns 503, check `GATEWAY_ORIGIN`, the gateway's public HTTPS reachability, and its `/health/live` endpoint. Keep real private messages out of initial deployment checks.
