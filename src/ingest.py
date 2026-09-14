"""
Main ingestion entrypoint. This is the script GitHub Actions runs on a
schedule. It loops over every enabled connector, fetches + transforms its
data, and writes the results to the shared database -- one connector
failing doesn't stop the others from running.

Usage:
    python -m src.ingest
"""

import logging
import sys
import time

from src import config, db
from src.connectors import (
    AirQualityConnector,
    HabitsConnector,
    SportsConnector,
    StocksConnector,
    WeatherConnector,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
logger = logging.getLogger("ingest")

# Maps the names in config.ENABLED_CONNECTORS to a factory that builds
# the connector instance. Add a new source by adding one line here.
CONNECTOR_FACTORIES = {
    "weather": lambda: WeatherConnector(config.WEATHER_CITIES),
    "stocks": lambda: StocksConnector(config.STOCK_TICKERS),
    "sports": lambda: SportsConnector(config.SPORTS_TEAMS),
    "air_quality": lambda: AirQualityConnector(config.AIR_QUALITY_LOCATIONS),
    "habits": lambda: HabitsConnector(config.GITHUB_USERNAME),
}


def run_connector(name: str, retries: int = 2, backoff_seconds: float = 3.0) -> list[dict]:
    factory = CONNECTOR_FACTORIES.get(name)
    if factory is None:
        logger.warning("No connector registered for %r, skipping", name)
        return []

    connector = factory()
    last_error = None
    for attempt in range(1, retries + 2):
        try:
            rows = connector.run()
            logger.info("%s: fetched %d rows", name, len(rows))
            return rows
        except Exception as exc:  # noqa: BLE001 -- log and retry, don't crash the pipeline
            last_error = exc
            logger.warning("%s: attempt %d failed (%s)", name, attempt, exc)
            if attempt <= retries:
                time.sleep(backoff_seconds * attempt)

    logger.error("%s: giving up after %d attempts (%s)", name, retries + 1, last_error)
    return []


def main() -> int:
    db.init_db(config.DB_PATH)

    total_inserted = 0
    total_failed_sources = 0

    for name in config.ENABLED_CONNECTORS:
        rows = run_connector(name)
        if not rows:
            total_failed_sources += 1
            continue
        inserted = db.insert_rows(config.DB_PATH, rows)
        total_inserted += inserted
        logger.info("%s: inserted %d new rows (duplicates skipped)", name, inserted)

    logger.info(
        "Done. %d new rows inserted across %d sources (%d sources returned nothing).",
        total_inserted,
        len(config.ENABLED_CONNECTORS),
        total_failed_sources,
    )

    # Non-zero exit if every single source failed -- lets GitHub Actions
    # flag a genuinely broken run without failing on one flaky API.
    return 1 if total_failed_sources == len(config.ENABLED_CONNECTORS) else 0


if __name__ == "__main__":
    sys.exit(main())
