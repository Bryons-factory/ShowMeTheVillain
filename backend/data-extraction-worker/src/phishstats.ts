import { PHISHSTATS_API_URL } from "./config";
import type { PhishStatsRecord } from "./transform";

export async function fetchBatch(
  batchSize: number,
  cursor: string | null
): Promise<PhishStatsRecord[]> {
  const params = new URLSearchParams({
    _sort: "date",
    _size: String(batchSize),
  });
  if (cursor) {
    params.set("_where", `(date,gt,${cursor})`);
  }

  const url = `${PHISHSTATS_API_URL}?${params.toString()}`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(
      `PhishStats HTTP ${response.status}: ${await response.text()}`
    );
  }

  const data: unknown = await response.json();
  if (!Array.isArray(data)) {
    return [];
  }
  return data as PhishStatsRecord[];
}
