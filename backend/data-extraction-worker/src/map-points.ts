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

/** PhishStats score (REAL) → UI threat_level. Tune thresholds with Tom/Matt if needed. */
export function scoreToThreatLevel(score: number | null): string {
  if (score === null) return "unknown";
  if (score >= 8) return "critical";
  if (score >= 6) return "high";
  if (score >= 4) return "medium";
  if (score >= 1) return "low";
  return "unknown";
}

/** Map score to intensity 1–10 for density map z. */
export function scoreToIntensity(score: number | null): number {
  if (score === null) return 4;
  const rounded = Math.round(score);
  return Math.min(10, Math.max(1, rounded));
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
