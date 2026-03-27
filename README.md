# ShowMeTheVillain

Global phishing threat tracker: a **Plotly density map** with a **top filter bar** (threat level, target company, country, ISP). Data comes from the **FastAPI backend** or, for static demos, from the **Cloudflare Worker** stub.

## What you see in the UI

- Full-height map under a dark toolbar with dropdown filters.
- Status line shows total threats loaded and how many match the current filters.
- **Client-side filtering**: the page fetches a batch of points once (by default), then filters in the browser.

## Architecture

| Piece | Role |
| --- | --- |
| [frontend/index.html](frontend/index.html) | Plotly map, filters, configurable data URL via `<meta>` or `window.__API_BASE__` |
| [frontend/entry.py](frontend/entry.py) | Cloudflare Worker: demo JSON **or** optional proxy to FastAPI when `BACKEND_MAP_URL` is set (configure in Wrangler/env as supported by Python Workers) |
| [backend/](backend/) | FastAPI + PhishStats pipeline; canonical source when running |

**Direct browser → FastAPI**: set `<meta name="api-base" content="https://your-api.example.com">` and `<meta name="data-source" content="api">`. Ensure CORS: set `FRONTEND_ORIGIN` and optional comma-separated `FRONTEND_ORIGINS` for Cloudflare Pages (see [backend/config.py](backend/config.py)).

**Worker demo (no FastAPI)**: set `data-source` to `worker` and `api-base` to your Worker URL (root returns the same JSON shape as `map-points`).

## Quick start

### Backend

```bash
cd backend
pip install -r requirements.txt
python3 main.py  # or: python main.py
# On Windows, you can also use: py -3 main.py
# or: uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Open [http://localhost:8000/docs](http://localhost:8000/docs) and try `GET /api/phishing/map-points`.

### Frontend (map)

Serve [frontend/](frontend/) with any static server (or open via Cloudflare Pages). In [frontend/index.html](frontend/index.html), default meta is:

- `api-base`: `http://127.0.0.1:8000`
- `data-source`: `api` → loads `{api-base}/api/phishing/map-points?limit=800`

Override at runtime:

```html
<script>window.__API_BASE__ = 'https://your-worker.workers.dev';</script>
```

(If you use a Worker without `/api/...` paths, switch `<meta name="data-source" content="worker">`.)

## API shape for the map

`GET /api/phishing/map-points` returns a JSON array of objects:

`lat`, `lon`, `intensity`, `name`, `threat_level`, `company`, `country`, `isp`

Optional query params match server-side filters: `threat_level`, `company`, `country`, `isp`, `limit`, `offset`.

The older `GET /api/phishing/heatmap` response (`HeatmapData`: `coordinates`, `incident_count`, `last_updated`) is still available for simple heatmaps that only need lat/lon pairs.

## Deploy

GitHub Actions (see [.github/workflows/deploy.yml](.github/workflows/deploy.yml)) deploys `./frontend` to Cloudflare Pages and the Python Worker from [frontend/entry.py](frontend/entry.py).

## Documentation

- [backend/BACKEND_README.md](backend/BACKEND_README.md) — full backend architecture
- [backend/QUICKSTART.md](backend/QUICKSTART.md) — short setup and endpoint cheat sheet
