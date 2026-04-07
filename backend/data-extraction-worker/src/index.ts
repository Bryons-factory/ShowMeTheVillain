import { getIngestConfig } from "./config";
import {
  formatPhishstatsDate,
  getCurrentCursor,
  getOldestDate,
} from "./cursor";
import type { Env } from "./env";
import { fetchBatch } from "./phishstats";
import { UPSERT_SQL } from "./queries";
import { buildParams } from "./transform";

export type { Env };

async function runOnce(
  env: Env,
  cursor: string | null,
  batchSize: number,
  overlapMinutes: number
): Promise<{ nextCursor: string | null; count: number }> {
  const records = await fetchBatch(batchSize, cursor);

  if (records.length === 0) {
    return { nextCursor: cursor, count: 0 };
  }

  const statements = records.map((record) => {
    const params = buildParams(record);
    return env.DB.prepare(UPSERT_SQL).bind(...params);
  });
  await env.DB.batch(statements);

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
