#!/bin/sh
set -eu

python - <<'PY'
import os
import sys
import time

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

database_url = os.environ["DATABASE_URL"]
attempts = int(os.getenv("DB_STARTUP_ATTEMPTS", "30"))
delay = float(os.getenv("DB_STARTUP_DELAY_SECONDS", "2"))
engine = create_engine(database_url, pool_pre_ping=True)

for attempt in range(1, attempts + 1):
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        print("Database connection ready", flush=True)
        break
    except SQLAlchemyError as exc:
        if attempt == attempts:
            print(f"Database unavailable after {attempts} attempts: {exc}", file=sys.stderr)
            raise
        print(f"Waiting for database ({attempt}/{attempts})", flush=True)
        time.sleep(delay)
PY

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
    alembic upgrade head
fi

if [ "${SEED_DEMO_DATA:-false}" = "true" ]; then
    python -m app.seed
fi

exec "$@"
