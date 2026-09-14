"""
Sports connector -- TheSportsDB (https://www.thesportsdb.com)

Uses the free public "3" test API key, no signup required. Pulls the most
recent completed events for each configured team.
"""

import logging
import time

import requests

from .base import BaseConnector

logger = logging.getLogger(__name__)


class SportsConnector(BaseConnector):
    source_name = "sports"

    BASE_URL = "https://www.thesportsdb.com/api/v1/json/3/eventslast.php"

    def __init__(self, team_ids: list[dict]):
        """
        team_ids: list of {"name": str, "team_id": str}
        Look up team IDs via TheSportsDB's searchteams.php endpoint.
        """
        self.team_ids = team_ids

    def fetch(self) -> dict:
        results = {}
        for team in self.team_ids:
            for attempt in range(3):
                try:
                    resp = requests.get(
                        self.BASE_URL,
                        params={"id": team["team_id"]},
                        timeout=15,
                    )
                    resp.raise_for_status()
                    payload = resp.json()
                    if "results" not in payload:
                        raise ValueError(
                            f"TheSportsDB returned no results field for {team['name']}"
                        )
                    results[team["name"]] = payload
                    break
                except (requests.RequestException, ValueError):
                    if attempt == 2:
                        logger.warning(
                            "Unable to fetch sports events for %s", team["name"]
                        )
                        break
                    time.sleep(attempt + 1)
        return results

    def transform(self, raw: dict) -> list[dict]:
        rows = []
        ts = self.now_iso()
        for team_name, payload in raw.items():
            events = payload.get("results") or []
            for event in events[:5]:
                home_score = event.get("intHomeScore")
                away_score = event.get("intAwayScore")
                if home_score is None or away_score is None:
                    continue
                rows.append({
                    "source": self.source_name,
                    "timestamp": ts,
                    "metric": "score_margin",
                    "value": float(int(home_score) - int(away_score)),
                    "label": f"{team_name}: {event.get('strEvent', 'unknown')}",
                    "metadata": {
                        "date": event.get("dateEvent"),
                        "home_score": home_score,
                        "away_score": away_score,
                    },
                })
        return rows
