import { PHISHSTATS_API_URL } from "./config";
import type { PhishStatsRecord } from "./transform";

const OUTBOUND_HEADERS = {
  Accept: "application/json",
  "User-Agent": "ShowMeTheVillain-data-extraction-worker/1.0 (Cloudflare Worker)",
};

function truncateForLog(value: unknown, maxChars = 512): string {
  const raw =
    value === null || value === undefined
      ? String(value)
      : typeof value === "object"
        ? JSON.stringify(value)
        : String(value);
  if (raw.length <= maxChars) return raw;
  return `${raw.slice(0, maxChars)}…`;
}

export async function fetchBatch(
  batchSize: number,
  cursor: string | null
): Promise<PhishStatsRecord[]> {
  const params = new URLSearchParams({
    _sort: "-date",
    _size: String(batchSize),
  });
  if (cursor) {
    params.set("_where", `(date,lt,${cursor})`);
  }

  const url = `${PHISHSTATS_API_URL}?${params.toString()}`;
  const response = await fetch(url, { headers: OUTBOUND_HEADERS });
  const contentType = response.headers.get("content-type") ?? "";

  if (!response.ok) {
    throw new Error(
      `PhishStats HTTP ${response.status}: ${await response.text()}`
    );
  }

  const data: unknown = await response.json();
  if (!Array.isArray(data)) {
    console.error(
      `phishstats-fetch: expected JSON array; Content-Type=${contentType} status=${response.status} body=${truncateForLog(data)}`
    );
    throw new Error(
      `PhishStats response must be a top-level JSON array (got ${typeof data})`
    );
  }

  console.log(`phishstats-fetch: GET ${url} → ${String(data.length)} row(s)`);
  return data as PhishStatsRecord[];
}
