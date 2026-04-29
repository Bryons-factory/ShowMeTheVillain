/** DML for phishing_links. Must match schema.sql columns and transform.ts bind order (Tom + Matt). */

export const UPSERT_SQL = `
INSERT INTO phishing_links (
    id,
    url,
    redirect_url,
    ip,
    countrycode,
    countryname,
    regioncode,
    regionname,
    city,
    zipcode,
    latitude,
    longitude,
    asn,
    bgp,
    isp,
    title,
    date,
    date_update,
    hash,
    score,
    host,
    domain,
    tld,
    domain_registered_n_days_ago,
    screenshot,
    abuse_contact,
    ssl_issuer,
    ssl_subject,
    rank_host,
    rank_domain,
    n_times_seen_ip,
    n_times_seen_host,
    n_times_seen_domain,
    http_code,
    http_server,
    google_safebrowsing,
    virus_total,
    abuse_ch_malware,
    vulns,
    ports,
    os,
    tags,
    technology,
    page_text,
    ssl_fingerprint
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(id) DO UPDATE SET
    url = excluded.url,
    redirect_url = excluded.redirect_url,
    ip = excluded.ip,
    countrycode = excluded.countrycode,
    countryname = excluded.countryname,
    regioncode = excluded.regioncode,
    regionname = excluded.regionname,
    city = excluded.city,
    zipcode = excluded.zipcode,
    latitude = excluded.latitude,
    longitude = excluded.longitude,
    asn = excluded.asn,
    bgp = excluded.bgp,
    isp = excluded.isp,
    title = excluded.title,
    date = excluded.date,
    date_update = excluded.date_update,
    hash = excluded.hash,
    score = excluded.score,
    host = excluded.host,
    domain = excluded.domain,
    tld = excluded.tld,
    domain_registered_n_days_ago = excluded.domain_registered_n_days_ago,
    screenshot = excluded.screenshot,
    abuse_contact = excluded.abuse_contact,
    ssl_issuer = excluded.ssl_issuer,
    ssl_subject = excluded.ssl_subject,
    rank_host = excluded.rank_host,
    rank_domain = excluded.rank_domain,
    n_times_seen_ip = excluded.n_times_seen_ip,
    n_times_seen_host = excluded.n_times_seen_host,
    n_times_seen_domain = excluded.n_times_seen_domain,
    http_code = excluded.http_code,
    http_server = excluded.http_server,
    google_safebrowsing = excluded.google_safebrowsing,
    virus_total = excluded.virus_total,
    abuse_ch_malware = excluded.abuse_ch_malware,
    vulns = excluded.vulns,
    ports = excluded.ports,
    os = excluded.os,
    tags = excluded.tags,
    technology = excluded.technology,
    page_text = excluded.page_text,
    ssl_fingerprint = excluded.ssl_fingerprint
`.trim();

export const GET_NEWEST_DATE_SQL =
  "SELECT MAX(date) AS newest_date FROM phishing_links";

/** Latest rows with coordinates for the map API (Tom: keep columns in sync with schema.sql). */
const MAP_POINTS_SELECT_BASE_SQL = `
SELECT
    latitude,
    longitude,
    score,
    title,
    host,
    domain,
    countryname,
    isp,
    tags,
    date
FROM phishing_links
WHERE latitude IS NOT NULL
  AND longitude IS NOT NULL
ORDER BY date DESC
`.trim();

/** Latest rows with optional limit for map API. */
export const MAP_POINTS_SELECT_SQL = `
${MAP_POINTS_SELECT_BASE_SQL}
LIMIT ?
`.trim();

/** Full table scan for map API (no LIMIT). */
export const MAP_POINTS_SELECT_ALL_SQL = `
${MAP_POINTS_SELECT_BASE_SQL}
`.trim();

/** Bounded read from pre-aggregated grid (see schema-map-grid-cells.sql). */
export const MAP_GRID_CELLS_SELECT_SQL = `
SELECT
    lat_bucket,
    lon_bucket,
    point_count,
    centroid_lat,
    centroid_lon,
    max_date,
    avg_score
FROM map_grid_cells
ORDER BY point_count DESC
LIMIT ?
`.trim();
