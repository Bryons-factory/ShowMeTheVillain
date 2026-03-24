import os
import time
import requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

PHISHSTATS_API_URL = "https://api.phishstats.info/api/phishing"

CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
CLOUDFLARE_DATABASE_ID = os.getenv("CLOUDFLARE_DATABASE_ID")
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")
PHISHSTATS_API_KEY = os.getenv("PHISHSTATS_API_KEY")

BATCH_SIZE = int(os.getenv("PHISHSTATS_BATCH_SIZE", "20"))
OVERLAP_MINUTES = int(os.getenv("PHISHSTATS_OVERLAP_MINUTES", "90"))
SLEEP_SECONDS = int(os.getenv("PHISHSTATS_SLEEP_SECONDS", "5"))

if not CLOUDFLARE_ACCOUNT_ID or not CLOUDFLARE_DATABASE_ID or not CLOUDFLARE_API_TOKEN:
    raise ValueError("Missing Cloudflare credentials in .env")

D1_QUERY_URL = (
    f"https://api.cloudflare.com/client/v4/accounts/"
    f"{CLOUDFLARE_ACCOUNT_ID}/d1/database/{CLOUDFLARE_DATABASE_ID}/query"
)

CF_HEADERS = {
    "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
    "Content-Type": "application/json",
}


def normalize_number(value, as_int=False):
    if value is None or value == "":
        return None
    try:
        return int(value) if as_int else float(value)
    except (TypeError, ValueError):
        return None


def format_phishstats_date(dt: datetime) -> str:
    dt = dt.astimezone(timezone.utc).replace(microsecond=0)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def parse_phishstats_date(date_str: str) -> datetime:
    return datetime.fromisoformat(date_str.replace("Z", "+00:00"))


def d1_query(sql, params=None):
    payload = {
        "sql": sql,
        "params": params or []
    }

    response = requests.post(D1_QUERY_URL, headers=CF_HEADERS, json=payload, timeout=60)
    if not response.ok:
        print("D1 query failed:")
        print(response.text)
        response.raise_for_status()

    return response.json()


def d1_batch(statements):
    payload = {"batch": statements}

    response = requests.post(D1_QUERY_URL, headers=CF_HEADERS, json=payload, timeout=120)
    if not response.ok:
        print("D1 batch failed:")
        print(response.text)
        response.raise_for_status()

    return response.json()


def init_schema():
    sql = """
    CREATE TABLE IF NOT EXISTS phishing_links (
        id INTEGER PRIMARY KEY,
        url TEXT NOT NULL,
        redirect_url TEXT,
        ip TEXT,
        countrycode TEXT,
        countryname TEXT,
        regioncode TEXT,
        regionname TEXT,
        city TEXT,
        zipcode TEXT,
        latitude REAL,
        longitude REAL,
        asn TEXT,
        bgp TEXT,
        isp TEXT,
        title TEXT,
        date TEXT,
        date_update TEXT,
        hash TEXT,
        score REAL,
        host TEXT,
        domain TEXT,
        tld TEXT,
        domain_registered_n_days_ago INTEGER,
        screenshot TEXT,
        abuse_contact TEXT,
        ssl_issuer TEXT,
        ssl_subject TEXT,
        rank_host INTEGER,
        rank_domain INTEGER,
        n_times_seen_ip INTEGER,
        n_times_seen_host INTEGER,
        n_times_seen_domain INTEGER,
        http_code INTEGER,
        http_server TEXT,
        google_safebrowsing TEXT,
        virus_total TEXT,
        abuse_ch_malware TEXT,
        vulns TEXT,
        ports TEXT,
        os TEXT,
        tags TEXT,
        technology TEXT,
        page_text TEXT,
        ssl_fingerprint TEXT,
        inserted_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """
    d1_query(sql)


def fetch_batch(cursor=None):
    params = {
        "_sort": "-date",
        "_size": BATCH_SIZE,
    }

    if cursor:
        params["_where"] = f"(date,lt,{cursor})"

    response = requests.get(
        PHISHSTATS_API_URL,
        params=params,
        timeout=60,
    )
    if not response.ok:
        print("PhishStats request failed:")
        print(response.text)
        response.raise_for_status()

    data = response.json()
    if not isinstance(data, list):
        return []

    return data


def get_oldest_date(records):
    dates = []
    for record in records:
        raw_date = record.get("date")
        if raw_date:
            try:
                dates.append(parse_phishstats_date(raw_date))
            except Exception:
                pass

    if not dates:
        return None

    return min(dates)


def upsert_records(records):
    if not records:
        return

    sql = """
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
    """

    statements = []

    for r in records:
        statements.append({
            "sql": sql,
            "params": [
                r.get("id"),
                r.get("url"),
                r.get("redirect_url"),
                r.get("ip"),
                r.get("countrycode"),
                r.get("countryname"),
                r.get("regioncode"),
                r.get("regionname"),
                r.get("city"),
                r.get("zipcode"),
                normalize_number(r.get("latitude")),
                normalize_number(r.get("longitude")),
                r.get("asn"),
                r.get("bgp"),
                r.get("isp"),
                r.get("title"),
                r.get("date"),
                r.get("date_update"),
                r.get("hash"),
                normalize_number(r.get("score")),
                r.get("host"),
                r.get("domain"),
                r.get("tld"),
                normalize_number(r.get("domain_registered_n_days_ago"), as_int=True),
                r.get("screenshot"),
                r.get("abuse_contact"),
                r.get("ssl_issuer"),
                r.get("ssl_subject"),
                normalize_number(r.get("rank_host"), as_int=True),
                normalize_number(r.get("rank_domain"), as_int=True),
                normalize_number(r.get("n_times_seen_ip"), as_int=True),
                normalize_number(r.get("n_times_seen_host"), as_int=True),
                normalize_number(r.get("n_times_seen_domain"), as_int=True),
                normalize_number(r.get("http_code"), as_int=True),
                r.get("http_server"),
                r.get("google_safebrowsing"),
                r.get("virus_total"),
                r.get("abuse_ch_malware"),
                r.get("vulns"),
                r.get("ports"),
                r.get("os"),
                r.get("tags"),
                r.get("technology"),
                r.get("page_text"),
                r.get("ssl_fingerprint"),
            ]
        })

    d1_batch(statements)


def get_current_cursor():
    sql = "SELECT MIN(date) AS oldest_date FROM phishing_links"
    result = d1_query(sql)

    rows = result.get("result", [])
    if not rows:
        return None

    results = rows[0].get("results", [])
    if not results:
        return None

    oldest_date = results[0].get("oldest_date")
    if not oldest_date:
        return None

    oldest_dt = parse_phishstats_date(oldest_date)
    next_dt = oldest_dt - timedelta(minutes=OVERLAP_MINUTES)
    return format_phishstats_date(next_dt)


def run_once(cursor):
    print("=" * 80)
    if cursor:
        print(f"Fetching batch before: {cursor}")
    else:
        print("Fetching newest batch")

    records = fetch_batch(cursor)

    if not records:
        print("No records returned")
        return cursor, 0

    upsert_records(records)

    oldest = get_oldest_date(records)
    if not oldest:
        print("Could not determine oldest date from batch")
        return cursor, len(records)

    next_cursor_dt = oldest - timedelta(minutes=OVERLAP_MINUTES)
    next_cursor = format_phishstats_date(next_cursor_dt)

    newest_date = records[0].get("date")
    oldest_date = records[-1].get("date")

    print(f"Fetched: {len(records)}")
    print(f"Newest in batch: {newest_date}")
    print(f"Oldest in batch: {oldest_date}")
    print(f"Next cursor: {next_cursor}")

    return next_cursor, len(records)


def main():
    init_schema()

    cursor = get_current_cursor()

    if cursor:
        print(f"Resuming from database-derived cursor: {cursor}")
    else:
        print("No existing data found, starting from newest records")

    while True:
        try:
            cursor, count = run_once(cursor)

            if count == 0:
                print(f"Sleeping {SLEEP_SECONDS} seconds before retry...")
                time.sleep(SLEEP_SECONDS)
                continue

            print(f"Sleeping {SLEEP_SECONDS} seconds before next run...")
            time.sleep(SLEEP_SECONDS)

        except KeyboardInterrupt:
            print("\nStopped by user")
            break
        except Exception as exc:
            print(f"Loop error: {exc}")
            print(f"Sleeping {SLEEP_SECONDS} seconds before retry...")
            time.sleep(SLEEP_SECONDS)


if __name__ == "__main__":
    main()