/**
 * phishing_links row → JSON shape expected by frontend/index.html (Plotly + filters).
 * Aligns with backend/models.py MapPoint intent; D1 has no PhishStats threat_level — derive from score.
 */

export interface MapPointRow {
  lat: number;
  lon: number;
  intensity: number;
  name: string;
  threat_level: string;
  company: string | null;
  country: string | null;
  isp: string | null;
}

function num(v: unknown): number | null {
  if (v === null || v === undefined) return null;
  const n = typeof v === "number" ? v : parseFloat(String(v));
  return Number.isFinite(n) ? n : null;
}

function str(v: unknown): string | null {
  if (v === null || v === undefined) return null;
  const s = String(v).trim();
  return s.length ? s : null;
}

/** PhishStats score → threat_level. Aligned with testBuilder.py getThreatLevel. */
export function scoreToThreatLevel(score: number | null): string {
  if (score === null) return "unknown";
  if (score <= 0) return "none";
  if (score <= 2) return "low";
  if (score <= 4) return "moderate";
  if (score <= 6) return "elevated";
  if (score <= 8) return "high";
  if (score <= 10) return "critical";
  return "unknown";
}

/** Map score to intensity 1–10 for density map z. */
export function scoreToIntensity(score: number | null): number {
  if (score === null) return 4;
  const rounded = Math.round(score);
  return Math.min(10, Math.max(1, rounded));
}

/** Filter predicates aligned with testBuilder.py filter functions. */
export function filterMapPoints(
  rows: MapPointRow[],
  filters: {
    threat_level?: string;
    country?: string;
    isp?: string;
    intensity_above?: number;
    intensity_below?: number;
  }
): MapPointRow[] {
  let result = rows;

  if (filters.threat_level) {
    const level = filters.threat_level.toLowerCase();
    result = result.filter((r) => r.threat_level === level);
  }
  if (filters.country) {
    const country = filters.country.toLowerCase();
    result = result.filter(
      (r) => r.country !== null && r.country.toLowerCase() === country
    );
  }
  if (filters.isp) {
    const isp = filters.isp.toLowerCase();
    result = result.filter(
      (r) => r.isp !== null && r.isp.toLowerCase() === isp
    );
  }
  if (filters.intensity_above !== undefined) {
    result = result.filter((r) => r.intensity > filters.intensity_above!);
  }
  if (filters.intensity_below !== undefined) {
    result = result.filter((r) => r.intensity < filters.intensity_below!);
  }

  return result;
}

export function rowToMapPoint(row: Record<string, unknown>): MapPointRow | null {
  const lat = num(row.latitude);
  const lon = num(row.longitude);
  if (lat === null || lon === null) return null;
  if (lat < -90 || lat > 90 || lon < -180 || lon > 180) return null;

  const score = num(row.score);
  const title = str(row.title);
  const host = str(row.host);
  const domain = str(row.domain);
  const name =
    title ?? host ?? domain ?? "Unknown";

  return {
    lat,
    lon,
    intensity: scoreToIntensity(score),
    name,
    threat_level: scoreToThreatLevel(score),
    company: title ?? host ?? domain ?? null,
    country: str(row.countryname),
    isp: str(row.isp),
  };
}
