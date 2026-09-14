"""
Base connector interface.

Every data source (weather, stocks, sports, air quality, habits) implements
this same contract. The ingestion layer only ever calls fetch() and
transform() -- it never needs to know what's inside a specific connector.
This is what lets you add a 6th data source later by writing one new file
instead of touching the pipeline.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone


class BaseConnector(ABC):
    # Short machine-readable name, stored in the "source" column of the DB.
    # e.g. "weather", "stocks", "sports", "air_quality", "habits"
    source_name: str = "base"

    @abstractmethod
    def fetch(self) -> dict:
        """
        Call the external API and return the raw JSON response.
        Raise an exception on failure -- the ingestion layer handles retries
        and logging, connectors should stay dumb and just talk to the API.
        """
        raise NotImplementedError

    @abstractmethod
    def transform(self, raw: dict) -> list[dict]:
        """
        Turn the raw API response into a list of flat rows matching the
        pipeline's long-format schema:

            {
                "source": str,        # e.g. "weather"
                "timestamp": str,     # ISO 8601 UTC
                "metric": str,        # e.g. "temperature", "price", "commits"
                "value": float,       # the numeric value
                "label": str,         # human-readable context, e.g. ticker/city
                "metadata": dict,     # anything else worth keeping, as JSON
            }
        """
        raise NotImplementedError

    def run(self) -> list[dict]:
        """Fetch + transform in one call. This is what ingest.py invokes."""
        raw = self.fetch()
        return self.transform(raw)

    @staticmethod
    def now_iso() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")
