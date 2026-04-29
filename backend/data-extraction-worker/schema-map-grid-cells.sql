-- Aggregated map cells (refresh via DELETE + INSERT…SELECT from phishing_links).
-- Apply once per environment, e.g.:
--   npx wrangler d1 execute phishnstatsdb --file=./schema-map-grid-cells.sql
--   npx wrangler d1 execute phishnstatsdb --remote --file=./schema-map-grid-cells.sql

CREATE TABLE IF NOT EXISTS map_grid_cells (
  lat_bucket REAL NOT NULL,
  lon_bucket REAL NOT NULL,
  point_count INTEGER NOT NULL,
  centroid_lat REAL NOT NULL,
  centroid_lon REAL NOT NULL,
  max_date TEXT,
  avg_score REAL,
  PRIMARY KEY (lat_bucket, lon_bucket)
);
