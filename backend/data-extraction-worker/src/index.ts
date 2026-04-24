import { getIngestConfig } from "./config";
import {
  formatPhishstatsDate,
  getCurrentCursor,
  getOldestDate,
} from "./cursor";
import type { Env } from "./env";
import { fetchBatch } from "./phishstats";
import { MAP_POINTS_SELECT_SQL, UPSERT_SQL } from "./queries";
import { rowToMapPoint, filterMapPoints } from "./map-points";
import { buildParams } from "./transform";

export type { Env };

const DEFAULT_MAP_LIMIT = 800;
const MAX_MAP_LIMIT = 2000;

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

function parseMapLimit(url: URL): number {
  const raw = url.searchParams.get("limit");
  if (!raw) return DEFAULT_MAP_LIMIT;
  const n = parseInt(raw, 10);
  if (!Number.isFinite(n) || n < 1) return DEFAULT_MAP_LIMIT;
  return Math.min(n, MAX_MAP_LIMIT);
}

async function runOnce(
  env: Env,
  cursor: string | null,
  batchSize: number,
  overlapMinutes: number
): Promise<{ nextCursor: string | null; count: number }> {
  console.log(
    `phishstats-ingest: runOnce cursor=${cursor ?? "null"} batchSize=${String(batchSize)}`
  );
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

  const firstId = records[0]?.["id"];
  console.log(
    `phishstats-ingest: D1 batch ok (${String(records.length)} statements), first_id=${String(firstId ?? "n/a")}`
  );

  const oldest = getOldestDate(records);
  if (!oldest) {
    return { nextCursor: cursor, count: records.length };
  }

  const nextCursorDt = new Date(
    oldest.getTime() - overlapMinutes * 60 * 1000
  );
  const nextCursor = formatPhishstatsDate(nextCursorDt);

  return { nextCursor, count: records.length };
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
    const limit = parseMapLimit(url);

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
      const { results } = await env.DB.prepare(MAP_POINTS_SELECT_SQL)
        .bind(limit)
        .all<Record<string, unknown>>();
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
    console.log(
      `phishstats-ingest: start cursor=${cursor ?? "null"} batchSize=${String(cfg.batchSize)} overlapMinutes=${String(cfg.overlapMinutes)} maxBatchesPerRun=${String(cfg.maxBatchesPerRun)}`
    );
    let totalUpserted = 0;
    let batches = 0;

    try {
      while (batches < cfg.maxBatchesPerRun) {
        const { nextCursor, count } = await runOnce(
          env,
          cursor,
          cfg.batchSize,
          cfg.overlapMinutes
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
    } catch (e) {
      console.error("phishstats-ingest: fatal", e);
      throw e;
    }
  },
};
