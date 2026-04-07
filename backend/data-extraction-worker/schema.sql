DROP TABLE IF EXISTS phishing_points;
CREATE TABLE phishing_points (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lat REAL,
    lon REAL,
    intensity REAL,
    name TEXT,
    threat_level TEXT,
    company TEXT,
    country TEXT,
    isp TEXT
);
