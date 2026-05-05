import type { Env } from "./env";

export const PHISHSTATS_API_URL = "https://api.phishstats.info/api/phishing";

export interface IngestConfig {
  batchSize: number;
  overlapMinutes: number;
  maxBatchesPerRun: number;
}

function parsePositiveInt(raw: string | undefined, fallback: number): number {
  const n = parseInt(raw ?? "", 10);
  return Number.isFinite(n) && n > 0 ? n : fallback;
}

//OVERLAP_MINUTES is 'current time - OVERLAP_MINUTES'. EX: 4/13/16 12:30pm --> 4/16/26 12:15pm --> 4/16/26 12:00pm

export function getIngestConfig(env: Env): IngestConfig {
  return {
    batchSize: parsePositiveInt(env.PHISHSTATS_BATCH_SIZE, 20),
    overlapMinutes: parsePositiveInt(env.PHISHSTATS_OVERLAP_MINUTES, 15),
    maxBatchesPerRun: parsePositiveInt(env.PHISHSTATS_MAX_BATCHES_PER_RUN, 10),
  };
}

export interface PurgeConfig {
  /** 0 = disabled */
  retentionDays: number;
  batchSize: number;
  maxRounds: number;
}

export function getPurgeConfig(env: Env): PurgeConfig {
  const rawDays = parseInt(env.RETENTION_DAYS ?? "730", 10);
  const retentionDays =
    Number.isFinite(rawDays) && rawDays > 0 ? rawDays : 0;
  return {
    retentionDays,
    batchSize: parsePositiveInt(env.PURGE_BATCH_SIZE, 5000),
    maxRounds: parsePositiveInt(env.PURGE_MAX_ROUNDS, 20),
  };
}
