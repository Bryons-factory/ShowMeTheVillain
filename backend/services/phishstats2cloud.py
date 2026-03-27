import os
import time
import requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

from ..database2 import CREATE_TABLE_SQL, UPSERT_SQL, GET_OLDEST_DATE_SQL
import database

load_dotenv()

PHISHSTATS_API_URL = "https://api.phishstats.info/api/phishing"

CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
CLOUDFLARE_DATABASE_ID = os.getenv("CLOUDFLARE_DATABASE_ID")
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")

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
    d1_query(CREATE_TABLE_SQL)


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


def build_params(record):
    return [
        record.get("id"),
        record.get("url"),
        record.get("redirect_url"),
        record.get("ip"),
        record.get("countrycode"),
        record.get("countryname"),
        record.get("regioncode"),
        record.get("regionname"),
        record.get("city"),
        record.get("zipcode"),
        normalize_number(record.get("latitude")),
        normalize_number(record.get("longitude")),
        record.get("asn"),
        record.get("bgp"),
        record.get("isp"),
        record.get("title"),
        record.get("date"),
        record.get("date_update"),
        record.get("hash"),
        normalize_number(record.get("score")),
        record.get("host"),
        record.get("domain"),
        record.get("tld"),
        normalize_number(record.get("domain_registered_n_days_ago"), as_int=True),
        record.get("screenshot"),
        record.get("abuse_contact"),
        record.get("ssl_issuer"),
        record.get("ssl_subject"),
        normalize_number(record.get("rank_host"), as_int=True),
        normalize_number(record.get("rank_domain"), as_int=True),
        normalize_number(record.get("n_times_seen_ip"), as_int=True),
        normalize_number(record.get("n_times_seen_host"), as_int=True),
        normalize_number(record.get("n_times_seen_domain"), as_int=True),
        normalize_number(record.get("http_code"), as_int=True),
        record.get("http_server"),
        record.get("google_safebrowsing"),
        record.get("virus_total"),
        record.get("abuse_ch_malware"),
        record.get("vulns"),
        record.get("ports"),
        record.get("os"),
        record.get("tags"),
        record.get("technology"),
        record.get("page_text"),
        record.get("ssl_fingerprint"),
    ]


def upsert_records(records):
    if not records:
        return

    statements = []

    for record in records:
        statements.append({
            "sql": UPSERT_SQL,
            "params": build_params(record)
        })

    d1_batch(statements)


def get_current_cursor():
    result = d1_query(GET_OLDEST_DATE_SQL)

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
