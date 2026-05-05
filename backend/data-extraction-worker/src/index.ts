import { getIngestConfig, getPurgeConfig } from "./config";
import {
  formatPhishstatsDate,
  getCurrentCursor,
  getNewestDate,
} from "./cursor";
import type { Env } from "./env";
import { fetchBatch } from "./phishstats";
import {
  DELETE_PHISHING_OLDER_THAN_SQL,
  ISP_STATS_BY_ISP_SQL,
  MAP_GRID_CELLS_SELECT_SQL,
  MAP_POINTS_SELECT_ALL_SQL,
  MAP_POINTS_SELECT_SQL,
  UPSERT_SQL,
} from "./queries";
import {
  gridCellToMapPoint,
  rowToMapPoint,
  filterMapPoints,
} from "./map-points";
import { buildParams } from "./transform";

export type { Env };

const DEFAULT_MAP_LIMIT = 3000;
const DEFAULT_GRID_LIMIT = 5000;
const MAX_GRID_LIMIT = 50_000;
const DEFAULT_VICTIM_LIST_LIMIT = 20;
const MAX_VICTIM_LIST_LIMIT = 100;

const CORS_JSON_HEADERS: Record<string, string> = {
  "Content-Type": "application/json",
  "Access-Control-Allow-Origin": "*",
};

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: CORS_JSON_HEADERS,
  });
}

function parseMapLimit(url: URL): number | null {
  const raw = url.searchParams.get("limit");
  if (!raw) return null;
  if (raw.toLowerCase() === "all") return null;
  const n = parseInt(raw, 10);
  if (!Number.isFinite(n) || n < 1) return DEFAULT_MAP_LIMIT;
  return n;
}

function parseGridLimit(url: URL): number {
  const raw = url.searchParams.get("limit");
  if (!raw) return DEFAULT_GRID_LIMIT;
  const n = parseInt(raw, 10);
  if (!Number.isFinite(n) || n < 1) return DEFAULT_GRID_LIMIT;
  return Math.min(n, MAX_GRID_LIMIT);
}

function normalizePathname(pathname: string): string {
  if (!pathname || pathname === "/") return "/";
  const trimmed = pathname.replace(/\/+$/, "");
  return trimmed === "" ? "/" : trimmed;
}

function parseVictimListLimit(url: URL): number {
  const raw = url.searchParams.get("limit");
  if (!raw) return DEFAULT_VICTIM_LIST_LIMIT;
  const n = parseInt(raw, 10);
  if (!Number.isFinite(n) || n < 1) return DEFAULT_VICTIM_LIST_LIMIT;
  return Math.min(n, MAX_VICTIM_LIST_LIMIT);
}

async function runOnce(
  env: Env,
  cursor: string | null,
  batchSize: number
): Promise<{ nextCursor: string | null; count: number }> {
  const records = await fetchBatch(batchSize, cursor);

  if (records.length === 0) {
    return { nextCursor: cursor, count: 0 };
  }

  const stmt = env.DB.prepare(UPSERT_SQL);
  const statements = records.map((record) => {
    const params = buildParams(record);
    return stmt.bind(...params);
  });
  await env.DB.batch(statements);

  const newest = getNewestDate(records);
  if (!newest) {
    return { nextCursor: cursor, count: records.length };
  }

  // Keep overlap at DB bootstrap only; during a run we must advance forward,
  // otherwise each batch can keep re-reading the same overlap window.
  const nextCursor = formatPhishstatsDate(newest);

  return { nextCursor, count: records.length };
}

/** Cutoff ISO string: rows with date strictly older than this are purged. */
function retentionCutoffIso(retentionDays: number): string {
  const ms = Date.now() - retentionDays * 24 * 60 * 60 * 1000;
  return formatPhishstatsDate(new Date(ms));
}

async function purgeOlderThan(
  env: Env,
  cutoffIso: string,
  batchSize: number,
  maxRounds: number
): Promise<number> {
  let total = 0;
  for (let round = 0; round < maxRounds; round++) {
    const result = await env.DB
      .prepare(DELETE_PHISHING_OLDER_THAN_SQL)
      .bind(cutoffIso, batchSize)
      .run();
    const deleted = result.meta?.changes ?? 0;
    if (deleted === 0) {
      break;
    }
    total += deleted;
  }
  return total;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    if (request.method === "OPTIONS") {
      return new Response("", {
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "GET, OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type",
          "Access-Control-Max-Age": "86400",
        },
      });
    }

    if (request.method !== "GET") {
      return jsonResponse({ error: "method_not_allowed" }, 405);
    }

    const url = new URL(request.url);
    const path = normalizePathname(url.pathname);

    if (path === "/victim-list") {
      try {
        const lim = parseVictimListLimit(url);
        const { results } = await env.DB
          .prepare(ISP_STATS_BY_ISP_SQL)
          .bind(lim)
          .all<Record<string, unknown>>();
        const rows = (results ?? []).map((r) => ({
          isp: String(r.isp ?? ""),
          incident_count: Number(r.incident_count ?? 0),
          avg_score: Number(r.avg_score ?? 0),
          max_score: Number(r.max_score ?? 0),
        }));
        return jsonResponse(rows);
      } catch (e) {
        console.error("victim-list: D1 query failed", e);
        return jsonResponse({ error: "database_error" }, 502);
      }
    }

    if (path !== "/") {
      return jsonResponse({ error: "not_found" }, 404);
    }

    const limit = parseMapLimit(url);
    const mapMode = (url.searchParams.get("mode") ?? "").toLowerCase();

    const filters = {
      threat_level: url.searchParams.get("threat_level") ?? undefined,
      country: url.searchParams.get("country") ?? undefined,
      isp: url.searchParams.get("isp") ?? undefined,
      intensity_above: url.searchParams.has("intensity_above")
        ? parseFloat(url.searchParams.get("intensity_above")!)
        : undefined,
      intensity_below: url.searchParams.has("intensity_below")
        ? parseFloat(url.searchParams.get("intensity_below")!)
        : undefined,
    };

    try {
      if (mapMode === "grid") {
        const gridLimit = parseGridLimit(url);
        const { results } = await env.DB
          .prepare(MAP_GRID_CELLS_SELECT_SQL)
          .bind(gridLimit)
          .all<Record<string, unknown>>();
        let rows = (results ?? [])
          .map((r) => gridCellToMapPoint(r))
          .filter((p): p is NonNullable<typeof p> => p !== null);
        rows = filterMapPoints(rows, filters);
        return jsonResponse(rows);
      }

      const stmt =
        limit === null
          ? env.DB.prepare(MAP_POINTS_SELECT_ALL_SQL)
          : env.DB.prepare(MAP_POINTS_SELECT_SQL).bind(limit);
      const { results } = await stmt.all<Record<string, unknown>>();
      let rows = (results ?? [])
        .map((r) => rowToMapPoint(r))
        .filter((p): p is NonNullable<typeof p> => p !== null);
      rows = filterMapPoints(rows, filters);
      return jsonResponse(rows);
    } catch (e) {
      console.error("map-points: D1 query failed", e);
      return jsonResponse({ error: "database_error" }, 502);
    }
  },

  async scheduled(
    _event: ScheduledEvent,
    env: Env,
    _ctx: ExecutionContext
  ): Promise<void> {
    const cfg = getIngestConfig(env);
    let cursor = await getCurrentCursor(env.DB, cfg.overlapMinutes);
    let totalUpserted = 0;
    let batches = 0;

    try {
      while (batches < cfg.maxBatchesPerRun) {
        const { nextCursor, count } = await runOnce(
          env,
          cursor,
          cfg.batchSize
        );
        batches += 1;

        if (count === 0) {
          console.log(
            `phishstats-ingest: no records (batch ${batches}, cursor=${cursor ?? "null"})`
          );
          break;
        }

        totalUpserted += count;
        cursor = nextCursor;

        console.log(
          `phishstats-ingest: upserted ${count} rows (batch ${batches}/${cfg.maxBatchesPerRun}, next cursor set)`
        );
      }

      console.log(
        `phishstats-ingest: done, total rows this run: ${totalUpserted}, batches: ${batches}`
      );

      const purgeCfg = getPurgeConfig(env);
      if (purgeCfg.retentionDays > 0) {
        const cutoff = retentionCutoffIso(purgeCfg.retentionDays);
        const removed = await purgeOlderThan(
          env,
          cutoff,
          purgeCfg.batchSize,
          purgeCfg.maxRounds
        );
        console.log(
          `phishstats-retention: removed ${removed} row(s) with date < ${cutoff} (retention ${purgeCfg.retentionDays}d, batch ${purgeCfg.batchSize})`
        );
      } else {
        console.log("phishstats-retention: skipped (RETENTION_DAYS is 0)");
      }
    } catch (e) {
      console.error("phishstats-ingest: fatal", e);
      throw e;
    }
  },
};
