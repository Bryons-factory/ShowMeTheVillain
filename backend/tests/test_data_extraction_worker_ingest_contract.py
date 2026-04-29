from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKER_SRC = ROOT / "data-extraction-worker" / "src"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_ingest_cursor_sql_uses_newest_date():
    content = _read(WORKER_SRC / "queries.ts")
    assert "GET_NEWEST_DATE_SQL" in content
    assert "SELECT MAX(date) AS newest_date FROM phishing_links" in content
    assert "GET_OLDEST_DATE_SQL" not in content


def test_phishstats_fetch_uses_forward_tail_filter():
    content = _read(WORKER_SRC / "phishstats.ts")
    assert '_sort: "date"' in content
    assert '(date,gt,' in content
    assert '(date,lt,' not in content


def test_run_once_advances_cursor_without_reapplying_overlap():
    content = _read(WORKER_SRC / "index.ts")
    assert "const nextCursor = formatPhishstatsDate(newest);" in content
    assert "newest.getTime() - overlapMinutes" not in content


def test_bootstrap_cursor_applies_overlap_from_newest_date():
    content = _read(WORKER_SRC / "cursor.ts")
    assert "GET_NEWEST_DATE_SQL" in content
    assert "newestDt.getTime() - overlapMinutes * 60 * 1000" in content
    assert "return formatPhishstatsDate(new Date(nextMs));" in content


def test_scheduled_ingest_bootstraps_cursor_once_and_reuses_next_cursor():
    content = _read(WORKER_SRC / "index.ts")
    assert "let cursor = await getCurrentCursor(env.DB, cfg.overlapMinutes);" in content
    assert "const { nextCursor, count } = await runOnce(" in content
    assert "cursor = nextCursor;" in content
    assert "while (batches < cfg.maxBatchesPerRun)" in content


def test_fetch_supports_cors_preflight_and_allows_get_options():
    content = _read(WORKER_SRC / "index.ts")
    assert 'if (request.method === "OPTIONS")' in content
    assert '"Access-Control-Allow-Methods": "GET, OPTIONS"' in content
    assert '"Access-Control-Allow-Origin": "*"' in content


def test_fetch_rejects_non_get_methods_with_405():
    content = _read(WORKER_SRC / "index.ts")
    assert 'if (request.method !== "GET")' in content
    assert 'return jsonResponse({ error: "method_not_allowed" }, 405);' in content


def test_map_mode_grid_uses_grid_query_and_mapper():
    content = _read(WORKER_SRC / "index.ts")
    assert 'if (mapMode === "grid")' in content
    assert "const gridLimit = parseGridLimit(url);" in content
    assert ".prepare(MAP_GRID_CELLS_SELECT_SQL)" in content
    assert ".map((r) => gridCellToMapPoint(r))" in content


def test_non_grid_mode_uses_limit_sensitive_map_query():
    content = _read(WORKER_SRC / "index.ts")
    assert "const limit = parseMapLimit(url);" in content
    assert "limit === null" in content
    assert "env.DB.prepare(MAP_POINTS_SELECT_ALL_SQL)" in content
    assert "env.DB.prepare(MAP_POINTS_SELECT_SQL).bind(limit)" in content
    assert ".map((r) => rowToMapPoint(r))" in content


def test_fetch_maps_db_errors_to_database_error_502():
    content = _read(WORKER_SRC / "index.ts")
    assert 'console.error("map-points: D1 query failed", e);' in content
    assert 'return jsonResponse({ error: "database_error" }, 502);' in content


def test_map_limit_parsing_defaults_and_all_sentinel():
    content = _read(WORKER_SRC / "index.ts")
    assert "const DEFAULT_MAP_LIMIT = 800;" in content
    assert "if (!raw) return null;" in content
    assert 'if (raw.toLowerCase() === "all") return null;' in content
    assert "if (!Number.isFinite(n) || n < 1) return DEFAULT_MAP_LIMIT;" in content


def test_grid_limit_parsing_defaults_and_max_clamp():
    content = _read(WORKER_SRC / "index.ts")
    assert "const DEFAULT_GRID_LIMIT = 5000;" in content
    assert "const MAX_GRID_LIMIT = 50_000;" in content
    assert "if (!raw) return DEFAULT_GRID_LIMIT;" in content
    assert "if (!Number.isFinite(n) || n < 1) return DEFAULT_GRID_LIMIT;" in content
    assert "return Math.min(n, MAX_GRID_LIMIT);" in content


def test_map_points_threat_and_intensity_boundaries_are_stable():
    content = _read(WORKER_SRC / "map-points.ts")
    assert "if (score <= 0) return \"none\";" in content
    assert "if (score <= 2) return \"low\";" in content
    assert "if (score <= 4) return \"moderate\";" in content
    assert "if (score <= 6) return \"elevated\";" in content
    assert "if (score <= 8) return \"high\";" in content
    assert "if (score <= 10) return \"critical\";" in content
    assert "return \"unknown\";" in content
    assert "return Math.min(10, Math.max(1, rounded));" in content


def test_map_point_row_and_grid_require_valid_coordinates():
    content = _read(WORKER_SRC / "map-points.ts")
    assert "if (lat === null || lon === null) return null;" in content
    assert "if (lat < -90 || lat > 90 || lon < -180 || lon > 180) return null;" in content
    assert "const lat = num(row.centroid_lat);" in content
    assert "const lon = num(row.centroid_lon);" in content


def test_map_filter_predicates_keep_case_insensitive_and_strict_semantics():
    content = _read(WORKER_SRC / "map-points.ts")
    assert "if (filters.country) {" in content
    assert "r.country !== null && r.country.toLowerCase() === country" in content
    assert "if (filters.isp) {" in content
    assert "r.isp !== null && r.isp.toLowerCase() === isp" in content
    assert "if (filters.intensity_above !== undefined) {" in content
    assert "r.intensity > filters.intensity_above!" in content
    assert "if (filters.intensity_below !== undefined) {" in content
    assert "r.intensity < filters.intensity_below!" in content


def test_cursor_format_and_newest_selection_contracts():
    content = _read(WORKER_SRC / "cursor.ts")
    assert "d.setUTCMilliseconds(0);" in content
    assert "return `${y}-${m}-${day}T${h}:${min}:${s}.000Z`;" in content
    assert "return new Date(Math.max(...dates.map((d) => d.getTime())));" in content


def test_run_once_upserts_batched_records_and_preserves_empty_cursor():
    content = _read(WORKER_SRC / "index.ts")
    assert "const stmt = env.DB.prepare(UPSERT_SQL);" in content
    assert "const params = buildParams(record);" in content
    assert "return stmt.bind(...params);" in content
    assert "await env.DB.batch(statements);" in content
    assert "if (records.length === 0) {" in content
    assert "return { nextCursor: cursor, count: 0 };" in content


def test_scheduled_loop_stops_on_no_records_and_logs_completion():
    content = _read(WORKER_SRC / "index.ts")
    assert "if (count === 0) {" in content
    assert "break;" in content
    assert "totalUpserted += count;" in content
    assert "phishstats-ingest: done, total rows this run" in content


def test_phishstats_request_shape_and_error_handling_contracts():
    content = _read(WORKER_SRC / "phishstats.ts")
    assert 'const params = new URLSearchParams({' in content
    assert '_sort: "date"' in content
    assert "_size: String(batchSize)" in content
    assert 'params.set("_where", `(date,gt,${cursor})`);' in content
    assert "if (!response.ok) {" in content
    assert "`PhishStats HTTP ${response.status}: ${await response.text()}`" in content
    assert "if (!Array.isArray(data)) {" in content
    assert "return [];" in content


def test_ingest_config_uses_positive_int_fallbacks():
    content = _read(WORKER_SRC / "config.ts")
    assert "return Number.isFinite(n) && n > 0 ? n : fallback;" in content
    assert "batchSize: parsePositiveInt(env.PHISHSTATS_BATCH_SIZE, 20)," in content
    assert "overlapMinutes: parsePositiveInt(env.PHISHSTATS_OVERLAP_MINUTES, 15)," in content
    assert "maxBatchesPerRun: parsePositiveInt(env.PHISHSTATS_MAX_BATCHES_PER_RUN, 10)," in content
