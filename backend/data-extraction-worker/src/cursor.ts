import { GET_OLDEST_DATE_SQL } from "./queries";
import type { PhishStatsRecord } from "./transform";

/** UTC format aligned with legacy Python phishstats2cloud.format_phishstats_date */
export function formatPhishstatsDate(dt: Date): string {
  const d = new Date(dt.getTime());
  d.setUTCMilliseconds(0);
  const y = d.getUTCFullYear();
  const m = String(d.getUTCMonth() + 1).padStart(2, "0");
  const day = String(d.getUTCDate()).padStart(2, "0");
  const h = String(d.getUTCHours()).padStart(2, "0");
  const min = String(d.getUTCMinutes()).padStart(2, "0");
  const s = String(d.getUTCSeconds()).padStart(2, "0");
  return `${y}-${m}-${day}T${h}:${min}:${s}.000Z`;
}

export function parsePhishstatsDate(dateStr: string): Date {
  const normalized = dateStr.replace("Z", "+00:00");
  return new Date(normalized);
}

export function getOldestDate(records: PhishStatsRecord[]): Date | null {
  const dates: Date[] = [];
  for (const record of records) {
    const raw = record["date"];
    if (typeof raw === "string" && raw) {
      try {
        dates.push(parsePhishstatsDate(raw));
      } catch {
        /* skip */
      }
    }
  }
  if (dates.length === 0) return null;
  return new Date(Math.min(...dates.map((d) => d.getTime())));
}

/** Resume cursor from DB: oldest stored date minus overlap (Ethan). */
export async function getCurrentCursor(
  db: D1Database,
  overlapMinutes: number
): Promise<string | null> {
  const row = await db
    .prepare(GET_OLDEST_DATE_SQL)
    .first<{ oldest_date: string | null }>();
  if (!row?.oldest_date) return null;
  const oldestDt = parsePhishstatsDate(row.oldest_date);
  const nextMs = oldestDt.getTime() - overlapMinutes * 60 * 1000;
  return formatPhishstatsDate(new Date(nextMs));
}
