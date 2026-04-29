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
