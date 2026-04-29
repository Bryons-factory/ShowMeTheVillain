# Data extraction worker (PhishStats → D1 + map API)

Cloudflare Worker that:

1. **Ingest (cron)** — Pulls phishing incidents from the **PhishStats** HTTP API and **upserts** into D1 table **`phishing_links`**.
2. **Map API (`fetch`)** — **`GET /`** reads the latest rows from D1 and returns a **JSON array** in the shape expected by [`frontend/index.html`](../../frontend/index.html) (Plotly density map + filter bar).

This replaces the former Python scripts `backend/database2.py` and `backend/services/phishstats2cloud.py`.

## Overview

| Piece | Role |
|--------|------|
| **Schedule** | Top of every hour (`0 * * * *` in `wrangler.toml`) |
| **Ingest source** | `https://api.phishstats.info/api/phishing` |
| **Sink** | D1 binding `env.DB`, table `phishing_links` |
| **Map HTTP** | `GET https://<worker>/` → JSON array of map points (raw rows or aggregated grid; see Map HTTP API) |
| **Ingest semantics** | Tail cursor from newest ingested `date` (minus overlap), bounded batches per run |

### Hosted frontend (Cloudflare Pages)

GitHub Actions deploys this Worker, then runs [`frontend/scripts/patch_pages_meta.py`](../../frontend/scripts/patch_pages_meta.py), which sets **`api-base`** to this Worker’s **HTTPS** URL (`D1_WORKER_URL` from deploy output, or secret `D1_WORKER_URL`) and **`data-source=worker`**. The map page then loads data from **D1 via this Worker**, not from the Python BFF Worker.

**Local without D1:** Use FastAPI + `data-source=api` and `api-base=http://127.0.0.1:8000`, or run `npx wrangler dev` here and point `api-base` at the dev URL with `data-source=worker`.

### Deploy paths

- **Local:** From this directory, with `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` set: `npx wrangler deploy`
- **CI:** [`.github/workflows/deploy.yml`](../../.github/workflows/deploy.yml) runs `npx wrangler deploy` with `working-directory: ./backend/data-extraction-worker` and captures the Worker URL for Pages.
- **Dashboard:** Deploy from this folder so `wrangler.toml` and `src/index.ts` resolve.

### Differences vs the old Python loop

- **No `init_schema()` in the Worker.** Schema is applied out-of-band. The cron job assumes `phishing_links` already exists.
- **No `sleep()` between batches.** One cron run executes up to **`PHISHSTATS_MAX_BATCHES_PER_RUN`** batches, then exits.

---

## Map HTTP API

| Method | Path | Response |
|--------|------|----------|
| `GET` | `/` | `200`, `Content-Type: application/json`, body = `[{ lat, lon, intensity, name, threat_level, company, country, isp }, ...]` |
| `GET` | `/?limit=N` | Raw `phishing_links` rows (newest first), capped at `N` (invalid/missing `limit` falls back to 800) |
| `GET` | `/?limit=all` | Raw rows: full result set (heavy on D1 reads; avoid for public traffic) |
| `GET` | `/?mode=grid&limit=N` | **Bounded read** from `map_grid_cells` (default `N` = 5000 if omitted; max 50000). Populate table via SQL refresh; see [`schema-map-grid-cells.sql`](./schema-map-grid-cells.sql). |
| `OPTIONS` | `*` | CORS preflight |

**CORS:** `Access-Control-Allow-Origin: *` (tighten for production if needed).

**Row mapping:** See [`src/map-points.ts`](./src/map-points.ts). Raw points: `threat_level` / `intensity` from **`score`**. Grid cells: `gridCellToMapPoint` (intensity from `point_count`, threat from `avg_score`).

---

## Tom — schema, read SQL, ingest DML

**You own** the **shape** of `phishing_links`, migrations, and SQL that must stay consistent.

### Files

| File | Your responsibility |
|------|---------------------|
| [`schema.sql`](./schema.sql) | Canonical **`CREATE TABLE`** for `phishing_links`. Keep aligned with production D1. |
| [`src/queries.ts`](./src/queries.ts) | **`UPSERT_SQL`**, **`GET_NEWEST_DATE_SQL`**, **`MAP_POINTS_SELECT_SQL`**: columns must match **`schema.sql`** and ingest bind order. |

### Applying schema

```bash
npx wrangler d1 execute phishnstatsdb --file=./schema.sql
```

Use the `database_name` from [`wrangler.toml`](./wrangler.toml).

### When you change a column

1. Update **`schema.sql`**.
2. Update **`UPSERT_SQL`** and **`MAP_POINTS_SELECT_SQL`** in **`src/queries.ts`**.
3. Tell **Matt** to update **`buildParams`** / **`map-points.ts`** as needed.

---

## Ethan — ingest algorithm

**You own** PhishStats paging, cursor, and batch limits.

### Files

| File | Your responsibility |
|------|---------------------|
| [`src/config.ts`](./src/config.ts) | **`PHISHSTATS_*`** env defaults. |
| [`src/phishstats.ts`](./src/phishstats.ts) | **`fetchBatch`**. |
| [`src/cursor.ts`](./src/cursor.ts) | **`getCurrentCursor`**, **`getNewestDate`**, date helpers. |
| [`src/index.ts`](./src/index.ts) | **`scheduled`** handler: orchestration and logging. |

### Tunables (`wrangler.toml` `[vars]`)

| Variable | Default | Meaning |
|----------|---------|--------|
| `PHISHSTATS_BATCH_SIZE` | `20` | Page size per request |
| `PHISHSTATS_OVERLAP_MINUTES` | `90` | Cursor overlap |
| `PHISHSTATS_MAX_BATCHES_PER_RUN` | `10` | Max ingest cycles per cron tick |

---

## Matt — ingest transform + map JSON + HTTP behavior

**You own:**

| File | Responsibility |
|------|----------------|
| [`src/transform.ts`](./src/transform.ts) | PhishStats JSON → **`UPSERT_SQL`** bind array (order must match `queries.ts`). |
| [`src/map-points.ts`](./src/map-points.ts) | D1 row → frontend map/filter JSON; score → `threat_level` / `intensity`. |
| [`src/index.ts`](./src/index.ts) | **`fetch`**: CORS, `limit`, error responses, calls D1 + mapper. |

Reference for parity with FastAPI naming: [`backend/models.py`](../models.py) (`MapPoint`), [`backend/services/phishing_service.py`](../services/phishing_service.py) (`_incident_to_map_point`).

---

## File map

```
backend/data-extraction-worker/
├── README.md           # This file
├── wrangler.toml       # Worker name, cron, D1 binding, [vars]
├── schema.sql          # DDL (Tom)
└── src/
    ├── index.ts        # scheduled (Ethan) + fetch map API (Matt)
    ├── env.ts          # Env typing
    ├── config.ts       # Ingest config (Ethan)
    ├── phishstats.ts   # PhishStats HTTP (Ethan)
    ├── cursor.ts       # Cursor + dates (Ethan)
    ├── queries.ts      # UPSERT, MIN(date), map SELECT (Tom + coordination)
    ├── transform.ts    # API → upsert binds (Matt)
    └── map-points.ts   # D1 row → MapPoint JSON (Matt)
```
