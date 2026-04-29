var __defProp = Object.defineProperty;
var __name = (target, value) => __defProp(target, "name", { value, configurable: true });

// .wrangler/tmp/bundle-2VNteX/checked-fetch.js
var urls = /* @__PURE__ */ new Set();
function checkURL(request, init) {
  const url = request instanceof URL ? request : new URL(
    (typeof request === "string" ? new Request(request, init) : request).url
  );
  if (url.port && url.port !== "443" && url.protocol === "https:") {
    if (!urls.has(url.toString())) {
      urls.add(url.toString());
      console.warn(
        `WARNING: known issue with \`fetch()\` requests to custom HTTPS ports in published Workers:
 - ${url.toString()} - the custom port will be ignored when the Worker is published using the \`wrangler deploy\` command.
`
      );
    }
  }
}
__name(checkURL, "checkURL");
globalThis.fetch = new Proxy(globalThis.fetch, {
  apply(target, thisArg, argArray) {
    const [request, init] = argArray;
    checkURL(request, init);
    return Reflect.apply(target, thisArg, argArray);
  }
});

// src/config.ts
var PHISHSTATS_API_URL = "https://api.phishstats.info/api/phishing";
function parsePositiveInt(raw, fallback) {
  const n = parseInt(raw ?? "", 10);
  return Number.isFinite(n) && n > 0 ? n : fallback;
}
__name(parsePositiveInt, "parsePositiveInt");
function getIngestConfig(env) {
  return {
    batchSize: parsePositiveInt(env.PHISHSTATS_BATCH_SIZE, 20),
    overlapMinutes: parsePositiveInt(env.PHISHSTATS_OVERLAP_MINUTES, 15),
    maxBatchesPerRun: parsePositiveInt(env.PHISHSTATS_MAX_BATCHES_PER_RUN, 10)
  };
}
__name(getIngestConfig, "getIngestConfig");

// src/queries.ts
var UPSERT_SQL = `
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
var GET_NEWEST_DATE_SQL = "SELECT MAX(date) AS newest_date FROM phishing_links";
var MAP_POINTS_SELECT_BASE_SQL = `
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
var MAP_POINTS_SELECT_SQL = `
${MAP_POINTS_SELECT_BASE_SQL}
LIMIT ?
`.trim();
var MAP_POINTS_SELECT_ALL_SQL = `
${MAP_POINTS_SELECT_BASE_SQL}
`.trim();
var MAP_GRID_CELLS_SELECT_SQL = `
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

// src/cursor.ts
function formatPhishstatsDate(dt) {
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
__name(formatPhishstatsDate, "formatPhishstatsDate");
function parsePhishstatsDate(dateStr) {
  const normalized = dateStr.replace("Z", "+00:00");
  return new Date(normalized);
}
__name(parsePhishstatsDate, "parsePhishstatsDate");
function getNewestDate(records) {
  const dates = [];
  for (const record of records) {
    const raw = record["date"];
    if (typeof raw === "string" && raw) {
      try {
        dates.push(parsePhishstatsDate(raw));
      } catch {
      }
    }
  }
  if (dates.length === 0) return null;
  return new Date(Math.max(...dates.map((d) => d.getTime())));
}
__name(getNewestDate, "getNewestDate");
async function getCurrentCursor(db, overlapMinutes) {
  const row = await db.prepare(GET_NEWEST_DATE_SQL).first();
  if (!row?.newest_date) return null;
  const newestDt = parsePhishstatsDate(row.newest_date);
  const nextMs = newestDt.getTime() - overlapMinutes * 60 * 1e3;
  return formatPhishstatsDate(new Date(nextMs));
}
__name(getCurrentCursor, "getCurrentCursor");

// src/phishstats.ts
async function fetchBatch(batchSize, cursor) {
  const params = new URLSearchParams({
    _sort: "date",
    _size: String(batchSize)
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
  const data = await response.json();
  if (!Array.isArray(data)) {
    return [];
  }
  return data;
}
__name(fetchBatch, "fetchBatch");

// src/map-points.ts
function num(v) {
  if (v === null || v === void 0) return null;
  const n = typeof v === "number" ? v : parseFloat(String(v));
  return Number.isFinite(n) ? n : null;
}
__name(num, "num");
function str(v) {
  if (v === null || v === void 0) return null;
  const s = String(v).trim();
  return s.length ? s : null;
}
__name(str, "str");
function scoreToThreatLevel(score) {
  if (score === null) return "unknown";
  if (score <= 0) return "none";
  if (score <= 2) return "low";
  if (score <= 4) return "moderate";
  if (score <= 6) return "elevated";
  if (score <= 8) return "high";
  if (score <= 10) return "critical";
  return "unknown";
}
__name(scoreToThreatLevel, "scoreToThreatLevel");
function scoreToIntensity(score) {
  if (score === null) return 4;
  const rounded = Math.round(score);
  return Math.min(10, Math.max(1, rounded));
}
__name(scoreToIntensity, "scoreToIntensity");
function filterMapPoints(rows, filters) {
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
  if (filters.intensity_above !== void 0) {
    result = result.filter((r) => r.intensity > filters.intensity_above);
  }
  if (filters.intensity_below !== void 0) {
    result = result.filter((r) => r.intensity < filters.intensity_below);
  }
  return result;
}
__name(filterMapPoints, "filterMapPoints");
function rowToMapPoint(row) {
  const lat = num(row.latitude);
  const lon = num(row.longitude);
  if (lat === null || lon === null) return null;
  if (lat < -90 || lat > 90 || lon < -180 || lon > 180) return null;
  const score = num(row.score);
  const title = str(row.title);
  const host = str(row.host);
  const domain = str(row.domain);
  const name = title ?? host ?? domain ?? "Unknown";
  return {
    lat,
    lon,
    intensity: scoreToIntensity(score),
    name,
    threat_level: scoreToThreatLevel(score),
    company: title ?? host ?? domain ?? null,
    country: str(row.countryname),
    isp: str(row.isp)
  };
}
__name(rowToMapPoint, "rowToMapPoint");
function gridCellToMapPoint(row) {
  const lat = num(row.centroid_lat);
  const lon = num(row.centroid_lon);
  if (lat === null || lon === null) return null;
  if (lat < -90 || lat > 90 || lon < -180 || lon > 180) return null;
  const count = num(row.point_count);
  const pc = count !== null && count >= 1 ? Math.floor(count) : 1;
  const z = Math.log10(pc + 1);
  const intensity = Math.min(10, Math.max(1, Math.round(z * 3.33)));
  const avgScore = num(row.avg_score);
  const maxDate = str(row.max_date);
  const name = maxDate !== null ? `${pc} incidents (latest ${maxDate})` : `${pc} incidents (grid cell)`;
  return {
    lat,
    lon,
    intensity,
    name,
    threat_level: scoreToThreatLevel(avgScore),
    company: null,
    country: null,
    isp: null
  };
}
__name(gridCellToMapPoint, "gridCellToMapPoint");

// src/transform.ts
function normalizeNumber(value, asInt = false) {
  if (value === null || value === void 0 || value === "") {
    return null;
  }
  const n = asInt ? parseInt(String(value), 10) : parseFloat(String(value));
  return Number.isFinite(n) ? n : null;
}
__name(normalizeNumber, "normalizeNumber");
function buildParams(record) {
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
    record["page_text"],
    record["ssl_fingerprint"]
  ];
}
__name(buildParams, "buildParams");

// src/index.ts
var DEFAULT_MAP_LIMIT = 800;
var DEFAULT_GRID_LIMIT = 5e3;
var MAX_GRID_LIMIT = 5e4;
var CORS_JSON_HEADERS = {
  "Content-Type": "application/json",
  "Access-Control-Allow-Origin": "*"
};
function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: CORS_JSON_HEADERS
  });
}
__name(jsonResponse, "jsonResponse");
function parseMapLimit(url) {
  const raw = url.searchParams.get("limit");
  if (!raw) return null;
  if (raw.toLowerCase() === "all") return null;
  const n = parseInt(raw, 10);
  if (!Number.isFinite(n) || n < 1) return DEFAULT_MAP_LIMIT;
  return n;
}
__name(parseMapLimit, "parseMapLimit");
function parseGridLimit(url) {
  const raw = url.searchParams.get("limit");
  if (!raw) return DEFAULT_GRID_LIMIT;
  const n = parseInt(raw, 10);
  if (!Number.isFinite(n) || n < 1) return DEFAULT_GRID_LIMIT;
  return Math.min(n, MAX_GRID_LIMIT);
}
__name(parseGridLimit, "parseGridLimit");
async function runOnce(env, cursor, batchSize) {
  const records = await fetchBatch(batchSize, cursor);
  if (records.length === 0) {
    return { nextCursor: cursor, count: 0 };
  }
  const stmt = env.DB.prepare(UPSERT_SQL);
  const statements = records.map((record) => {
    const params = buildParams(record);
    return stmt.bind(...params);
  });
  await env.DB.batch(statements);
  const newest = getNewestDate(records);
  if (!newest) {
    return { nextCursor: cursor, count: records.length };
  }
  const nextCursor = formatPhishstatsDate(newest);
  return { nextCursor, count: records.length };
}
__name(runOnce, "runOnce");
var src_default = {
  async fetch(request, env) {
    if (request.method === "OPTIONS") {
      return new Response("", {
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "GET, OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type",
          "Access-Control-Max-Age": "86400"
        }
      });
    }
    if (request.method !== "GET") {
      return jsonResponse({ error: "method_not_allowed" }, 405);
    }
    const url = new URL(request.url);
    const limit = parseMapLimit(url);
    const mapMode = (url.searchParams.get("mode") ?? "").toLowerCase();
    const filters = {
      threat_level: url.searchParams.get("threat_level") ?? void 0,
      country: url.searchParams.get("country") ?? void 0,
      isp: url.searchParams.get("isp") ?? void 0,
      intensity_above: url.searchParams.has("intensity_above") ? parseFloat(url.searchParams.get("intensity_above")) : void 0,
      intensity_below: url.searchParams.has("intensity_below") ? parseFloat(url.searchParams.get("intensity_below")) : void 0
    };
    try {
      if (mapMode === "grid") {
        const gridLimit = parseGridLimit(url);
        const { results: results2 } = await env.DB.prepare(MAP_GRID_CELLS_SELECT_SQL).bind(gridLimit).all();
        let rows2 = (results2 ?? []).map((r) => gridCellToMapPoint(r)).filter((p) => p !== null);
        rows2 = filterMapPoints(rows2, filters);
        return jsonResponse(rows2);
      }
      const stmt = limit === null ? env.DB.prepare(MAP_POINTS_SELECT_ALL_SQL) : env.DB.prepare(MAP_POINTS_SELECT_SQL).bind(limit);
      const { results } = await stmt.all();
      let rows = (results ?? []).map((r) => rowToMapPoint(r)).filter((p) => p !== null);
      rows = filterMapPoints(rows, filters);
      return jsonResponse(rows);
    } catch (e) {
      console.error("map-points: D1 query failed", e);
      return jsonResponse({ error: "database_error" }, 502);
    }
  },
  async scheduled(_event, env, _ctx) {
    const cfg = getIngestConfig(env);
    let cursor = await getCurrentCursor(env.DB, cfg.overlapMinutes);
    let totalUpserted = 0;
    let batches = 0;
    try {
      while (batches < cfg.maxBatchesPerRun) {
        const { nextCursor, count } = await runOnce(
          env,
          cursor,
          cfg.batchSize
        );
        batches += 1;
        if (count === 0) {
          console.log(
            `phishstats-ingest: no records (batch ${batches}, cursor=${cursor ?? "null"})`
          );
          break;
        }
        totalUpserted += count;
        cursor = nextCursor;
        console.log(
          `phishstats-ingest: upserted ${count} rows (batch ${batches}/${cfg.maxBatchesPerRun}, next cursor set)`
        );
      }
      console.log(
        `phishstats-ingest: done, total rows this run: ${totalUpserted}, batches: ${batches}`
      );
    } catch (e) {
      console.error("phishstats-ingest: fatal", e);
      throw e;
    }
  }
};

// ../../../../../../AppData/Roaming/npm/node_modules/wrangler/templates/middleware/middleware-ensure-req-body-drained.ts
var drainBody = /* @__PURE__ */ __name(async (request, env, _ctx, middlewareCtx) => {
  try {
    return await middlewareCtx.next(request, env);
  } finally {
    try {
      if (request.body !== null && !request.bodyUsed) {
        const reader = request.body.getReader();
        while (!(await reader.read()).done) {
        }
      }
    } catch (e) {
      console.error("Failed to drain the unused request body.", e);
    }
  }
}, "drainBody");
var middleware_ensure_req_body_drained_default = drainBody;

// ../../../../../../AppData/Roaming/npm/node_modules/wrangler/templates/middleware/middleware-scheduled.ts
var scheduled = /* @__PURE__ */ __name(async (request, env, _ctx, middlewareCtx) => {
  const url = new URL(request.url);
  if (url.pathname === "/__scheduled") {
    const cron = url.searchParams.get("cron") ?? "";
    await middlewareCtx.dispatch("scheduled", { cron });
    return new Response("Ran scheduled event");
  }
  const resp = await middlewareCtx.next(request, env);
  if (request.headers.get("referer")?.endsWith("/__scheduled") && url.pathname === "/favicon.ico" && resp.status === 500) {
    return new Response(null, { status: 404 });
  }
  return resp;
}, "scheduled");
var middleware_scheduled_default = scheduled;

// ../../../../../../AppData/Roaming/npm/node_modules/wrangler/templates/middleware/middleware-miniflare3-json-error.ts
function reduceError(e) {
  return {
    name: e?.name,
    message: e?.message ?? String(e),
    stack: e?.stack,
    cause: e?.cause === void 0 ? void 0 : reduceError(e.cause)
  };
}
__name(reduceError, "reduceError");
var jsonError = /* @__PURE__ */ __name(async (request, env, _ctx, middlewareCtx) => {
  try {
    return await middlewareCtx.next(request, env);
  } catch (e) {
    const error = reduceError(e);
    return Response.json(error, {
      status: 500,
      headers: { "MF-Experimental-Error-Stack": "true" }
    });
  }
}, "jsonError");
var middleware_miniflare3_json_error_default = jsonError;

// .wrangler/tmp/bundle-2VNteX/middleware-insertion-facade.js
var __INTERNAL_WRANGLER_MIDDLEWARE__ = [
  middleware_ensure_req_body_drained_default,
  middleware_scheduled_default,
  middleware_miniflare3_json_error_default
];
var middleware_insertion_facade_default = src_default;

// ../../../../../../AppData/Roaming/npm/node_modules/wrangler/templates/middleware/common.ts
var __facade_middleware__ = [];
function __facade_register__(...args) {
  __facade_middleware__.push(...args.flat());
}
__name(__facade_register__, "__facade_register__");
function __facade_invokeChain__(request, env, ctx, dispatch, middlewareChain) {
  const [head, ...tail] = middlewareChain;
  const middlewareCtx = {
    dispatch,
    next(newRequest, newEnv) {
      return __facade_invokeChain__(newRequest, newEnv, ctx, dispatch, tail);
    }
  };
  return head(request, env, ctx, middlewareCtx);
}
__name(__facade_invokeChain__, "__facade_invokeChain__");
function __facade_invoke__(request, env, ctx, dispatch, finalMiddleware) {
  return __facade_invokeChain__(request, env, ctx, dispatch, [
    ...__facade_middleware__,
    finalMiddleware
  ]);
}
__name(__facade_invoke__, "__facade_invoke__");

// .wrangler/tmp/bundle-2VNteX/middleware-loader.entry.ts
var __Facade_ScheduledController__ = class ___Facade_ScheduledController__ {
  constructor(scheduledTime, cron, noRetry) {
    this.scheduledTime = scheduledTime;
    this.cron = cron;
    this.#noRetry = noRetry;
  }
  static {
    __name(this, "__Facade_ScheduledController__");
  }
  #noRetry;
  noRetry() {
    if (!(this instanceof ___Facade_ScheduledController__)) {
      throw new TypeError("Illegal invocation");
    }
    this.#noRetry();
  }
};
function wrapExportedHandler(worker) {
  if (__INTERNAL_WRANGLER_MIDDLEWARE__ === void 0 || __INTERNAL_WRANGLER_MIDDLEWARE__.length === 0) {
    return worker;
  }
  for (const middleware of __INTERNAL_WRANGLER_MIDDLEWARE__) {
    __facade_register__(middleware);
  }
  const fetchDispatcher = /* @__PURE__ */ __name(function(request, env, ctx) {
    if (worker.fetch === void 0) {
      throw new Error("Handler does not export a fetch() function.");
    }
    return worker.fetch(request, env, ctx);
  }, "fetchDispatcher");
  return {
    ...worker,
    fetch(request, env, ctx) {
      const dispatcher = /* @__PURE__ */ __name(function(type, init) {
        if (type === "scheduled" && worker.scheduled !== void 0) {
          const controller = new __Facade_ScheduledController__(
            Date.now(),
            init.cron ?? "",
            () => {
            }
          );
          return worker.scheduled(controller, env, ctx);
        }
      }, "dispatcher");
      return __facade_invoke__(request, env, ctx, dispatcher, fetchDispatcher);
    }
  };
}
__name(wrapExportedHandler, "wrapExportedHandler");
function wrapWorkerEntrypoint(klass) {
  if (__INTERNAL_WRANGLER_MIDDLEWARE__ === void 0 || __INTERNAL_WRANGLER_MIDDLEWARE__.length === 0) {
    return klass;
  }
  for (const middleware of __INTERNAL_WRANGLER_MIDDLEWARE__) {
    __facade_register__(middleware);
  }
  return class extends klass {
    #fetchDispatcher = /* @__PURE__ */ __name((request, env, ctx) => {
      this.env = env;
      this.ctx = ctx;
      if (super.fetch === void 0) {
        throw new Error("Entrypoint class does not define a fetch() function.");
      }
      return super.fetch(request);
    }, "#fetchDispatcher");
    #dispatcher = /* @__PURE__ */ __name((type, init) => {
      if (type === "scheduled" && super.scheduled !== void 0) {
        const controller = new __Facade_ScheduledController__(
          Date.now(),
          init.cron ?? "",
          () => {
          }
        );
        return super.scheduled(controller);
      }
    }, "#dispatcher");
    fetch(request) {
      return __facade_invoke__(
        request,
        this.env,
        this.ctx,
        this.#dispatcher,
        this.#fetchDispatcher
      );
    }
  };
}
__name(wrapWorkerEntrypoint, "wrapWorkerEntrypoint");
var WRAPPED_ENTRY;
if (typeof middleware_insertion_facade_default === "object") {
  WRAPPED_ENTRY = wrapExportedHandler(middleware_insertion_facade_default);
} else if (typeof middleware_insertion_facade_default === "function") {
  WRAPPED_ENTRY = wrapWorkerEntrypoint(middleware_insertion_facade_default);
}
var middleware_loader_entry_default = WRAPPED_ENTRY;
export {
  __INTERNAL_WRANGLER_MIDDLEWARE__,
  middleware_loader_entry_default as default
};
//# sourceMappingURL=index.js.map
