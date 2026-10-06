"""Application configuration derived from the project location."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATIC_ROOT = PROJECT_ROOT
DATA_ROOT = PROJECT_ROOT / "data"
DATABASE_PATH = DATA_ROOT / "civicflow.sqlite3"
SESSION_COOKIE = "civicflow_session"
SESSION_TTL_SECONDS = 60 * 60 * 24 * 14
MAX_REQUEST_BYTES = 4 * 1024 * 1024

