import os

def __init__(self):
    """Initialize database connection."""
    self.connection_string = config.CLOUDFLARE_D1_CONNECTION

    base_dir = os.path.dirname(os.path.abspath(__file__))
    raw_db_path = config.DATABASE_PATH

    if os.path.isabs(raw_db_path):
        self.db_path = raw_db_path
    else:
        self.db_path = os.path.abspath(os.path.join(base_dir, raw_db_path))

    os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    self._initialize_schema()

    logger.info(f"Database initialized | Path: {self.db_path}")