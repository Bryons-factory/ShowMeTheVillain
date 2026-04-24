/** PhishStats API row -> SQL bind values (Matt). Order must match queries.ts UPSERT columns. */

export type PhishStatsRecord = Record<string, unknown>;

/** Keeps D1 row size predictable (PhishStats `page_text` can be very large). */
const PAGE_TEXT_MAX_CHARS = 100_000;

function truncateStringField(value: unknown, maxLen: number): unknown {
  if (value == null || typeof value !== "string") {
    return value;
  }
  if (value.length <= maxLen) {
    return value;
  }
  return value.slice(0, maxLen);
}

export function normalizeNumber(
  value: unknown,
  asInt = false
): number | null {
  if (value === null || value === undefined || value === "") {
    return null;
  }
  const n = asInt ? parseInt(String(value), 10) : parseFloat(String(value));
  return Number.isFinite(n) ? n : null;
}

export function buildParams(record: PhishStatsRecord): unknown[] {
  return [
    record["id"],
    record["url"],
    record["redirect_url"],
    record["ip"],
    record["countrycode"],
    record["countryname"],
    record["regioncode"],
    record["regionname"],
    record["city"],
    record["zipcode"],
    normalizeNumber(record["latitude"]),
    normalizeNumber(record["longitude"]),
    record["asn"],
    record["bgp"],
    record["isp"],
    record["title"],
    record["date"],
    record["date_update"],
    record["hash"],
    normalizeNumber(record["score"]),
    record["host"],
    record["domain"],
    record["tld"],
    normalizeNumber(record["domain_registered_n_days_ago"], true),
    record["screenshot"],
    record["abuse_contact"],
    record["ssl_issuer"],
    record["ssl_subject"],
    normalizeNumber(record["rank_host"], true),
    normalizeNumber(record["rank_domain"], true),
    normalizeNumber(record["n_times_seen_ip"], true),
    normalizeNumber(record["n_times_seen_host"], true),
    normalizeNumber(record["n_times_seen_domain"], true),
    normalizeNumber(record["http_code"], true),
    record["http_server"],
    record["google_safebrowsing"],
    record["virus_total"],
    record["abuse_ch_malware"],
    record["vulns"],
    record["ports"],
    record["os"],
    record["tags"],
    record["technology"],
    truncateStringField(record["page_text"], PAGE_TEXT_MAX_CHARS),
    record["ssl_fingerprint"],
  ];
}
