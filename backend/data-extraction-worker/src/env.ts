export interface Env {
  DB: D1Database;
  PHISHSTATS_BATCH_SIZE?: string;
  PHISHSTATS_OVERLAP_MINUTES?: string;
  PHISHSTATS_MAX_BATCHES_PER_RUN?: string;
  /** Rows with date older than this many days (UTC) are deleted after ingest. 0 or unset = skip purge. */
  RETENTION_DAYS?: string;
  /** Rows per DELETE batch (SQLite LIMIT). */
  PURGE_BATCH_SIZE?: string;
  /** Max DELETE batches per cron (safety cap). */
  PURGE_MAX_ROUNDS?: string;
}
