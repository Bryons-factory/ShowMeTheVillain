export interface Env {
  DB: D1Database;
  PHISHSTATS_BATCH_SIZE?: string;
  PHISHSTATS_OVERLAP_MINUTES?: string;
  PHISHSTATS_MAX_BATCHES_PER_RUN?: string;
}
