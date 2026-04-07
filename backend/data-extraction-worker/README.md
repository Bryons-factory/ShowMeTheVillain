# Data extraction worker (PhishStats → D1)

Cloudflare Worker with a **cron** trigger that pulls phishing incidents from the **PhishStats** HTTP API and **upserts** rows into D1 table **`phishing_links`**. This replaces the former Python scripts `backend/database2.py` and `backend/services/phishstats2cloud.py`.

## Overview

| Piece | Role |
|--------|------|
| **Schedule** | Top of every hour (`0 * * * *` in `wrangler.toml`) |
| **Source** | `https://api.phishstats.info/api/phishing` |
| **Sink** | D1 binding `env.DB`, table `phishing_links` |
| **Semantics** | Cursor based on `date`, overlap window, bounded batches per run (no infinite loop; safe for Worker CPU limits) |

### Deploy paths

- **Local:** From this directory, with `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` set: `npx wrangler deploy`
- **CI:** [`.github/workflows/deploy.yml`](../../.github/workflows/deploy.yml) runs `npx wrangler deploy` with `working-directory: ./backend/data-extraction-worker`
- **Cloudflare dashboard:** Optional Git-connected build; ensure the deploy command runs from this folder (or `cd` from repo root) so `wrangler.toml` and `src/index.ts` resolve

### Differences vs the old Python loop

- **No `init_schema()` in the Worker.** Schema is applied out-of-band (Tom). The cron job assumes `phishing_links` already exists.
- **No `sleep()` between batches.** One cron invocation runs up to **`PHISHSTATS_MAX_BATCHES_PER_RUN`** batches, then exits; the next hour continues backfill.

---

## Tom — schema and database maintenance

**You own** the **shape** of `phishing_links` in D1 and how it is created or migrated.

### Files

| File | Your responsibility |
|------|---------------------|
| [`schema.sql`](./schema.sql) | Canonical **`CREATE TABLE`** for `phishing_links`. Keep this aligned with production D1. |
| [`src/queries.ts`](./src/queries.ts) | **`UPSERT_SQL`** column list, `VALUES (?, …)` count, and **`ON CONFLICT(id) DO UPDATE`** assignments must match every non-default column you ingest (except `inserted_at`, which is default-only on insert). **`GET_OLDEST_DATE_SQL`** must remain valid for the cursor algorithm (uses `MIN(date)`). |

### Applying schema

From **`backend/data-extraction-worker`** (adjust `phishnstatsdb` if your `wrangler.toml` uses another `database_name`):

```bash
npx wrangler d1 execute phishnstatsdb --file=./schema.sql
```

Use the same database id/name as in [`wrangler.toml`](./wrangler.toml) `[[d1_databases]]`.

### When you change a column

1. Update **`schema.sql`** (and your migration process if you use one beyond this file).
2. Update **`UPSERT_SQL`** in **`src/queries.ts`** (insert column list, placeholders, conflict update list).
3. Tell **Matt** to update **`buildParams`** in **`src/transform.ts`** so bind order and types match the insert list exactly.

---

## Ethan — ingest algorithm

**You own** how we call PhishStats, how the cursor moves, and how much work each cron run does.

### Files

| File | Your responsibility |
|------|---------------------|
| [`src/config.ts`](./src/config.ts) | Defaults and parsing for **`PHISHSTATS_BATCH_SIZE`**, **`PHISHSTATS_OVERLAP_MINUTES`**, **`PHISHSTATS_MAX_BATCHES_PER_RUN`** (from `env` / `[vars]` in `wrangler.toml`). |
| [`src/phishstats.ts`](./src/phishstats.ts) | **`fetchBatch`**: URL, query params `_sort`, `_size`, `_where (date,lt,cursor)` — parity with the old `fetch_batch`. |
| [`src/cursor.ts`](./src/cursor.ts) | **`getCurrentCursor`**, **`getOldestDate`**, date **`format` / `parse`** — parity with `get_current_cursor` / `get_oldest_date` / `format_phishstats_date` / `parse_phishstats_date`. |
| [`src/index.ts`](./src/index.ts) | **Scheduled handler**: load initial cursor from D1, loop ≤ `maxBatchesPerRun`, call `runOnce`, log errors. Adjust error policy, logging, or batching strategy here. |

### Tunables (`wrangler.toml` `[vars]`)

| Variable | Default | Meaning |
|----------|---------|--------|
| `PHISHSTATS_BATCH_SIZE` | `20` | Page size per PhishStats request |
| `PHISHSTATS_OVERLAP_MINUTES` | `90` | Subtracted from oldest `date` when advancing cursor (overlap with previous window) |
| `PHISHSTATS_MAX_BATCHES_PER_RUN` | `10` | Max PhishStats fetch+upsert cycles per cron tick |

### Parity reference

Legacy behavior lived in **`run_once`**, **`get_current_cursor`**, and **`main()`** in the removed `phishstats2cloud.py` (see git history if needed).

---

## Matt — row transformation and downstream handoff

**You own** mapping **PhishStats JSON** → **SQL bind values** for the upsert.

### Files

| File | Your responsibility |
|------|---------------------|
| [`src/transform.ts`](./src/transform.ts) | **`normalizeNumber`**, **`buildParams`**: field names and order must match **`UPSERT_SQL`** in **`src/queries.ts`** exactly. |

### Downstream (not in this Worker)

The public map still expects **`MapPoint`** JSON (`lat`, `lon`, `intensity`, `name`, etc.) from FastAPI or the Python Worker. **This cron job does not emit map points.** A future step is a **read** path from **`phishing_links`** into that shape—for reference see:

- [`backend/models.py`](../models.py) — `MapPoint`
- [`backend/services/phishing_service.py`](../services/phishing_service.py) — `_incident_to_map_point` / `get_map_points`

Coordinate with Tom if new stored fields are needed for that projection.

---

## File map (quick)

```
backend/data-extraction-worker/
├── README.md           # This file
├── wrangler.toml       # Worker name, cron, D1 binding, [vars]
├── schema.sql          # DDL (Tom)
└── src/
    ├── index.ts        # Scheduled entry + orchestration (Ethan)
    ├── env.ts          # Env typing
    ├── config.ts       # Ingest config (Ethan)
    ├── phishstats.ts   # HTTP fetch (Ethan)
    ├── cursor.ts       # Cursor + dates (Ethan)
    ├── queries.ts      # UPSERT + MIN(date) (Tom + coordination)
    └── transform.ts    # API → bind array (Matt)
```
