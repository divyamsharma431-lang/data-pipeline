"""
Air quality connector -- Open-Meteo Air Quality API

No API key required. Pulls PM2.5, PM10, and US AQI for each configured
location. Same provider family as the weather connector, different endpoint.
"""

import requests

from .base import BaseConnector


class AirQualityConnector(BaseConnector):
    source_name = "air_quality"

    BASE_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

    def __init__(self, locations: list[dict]):
        """
        locations: list of {"name": str, "lat": float, "lon": float}
        """
        self.locations = locations

    def fetch(self) -> dict:
        results = {}
        for loc in self.locations:
            resp = requests.get(
                self.BASE_URL,
                params={
                    "latitude": loc["lat"],
                    "longitude": loc["lon"],
                    "current": "pm2_5,pm10,us_aqi",
                },
                timeout=15,
            )
            resp.raise_for_status()
            results[loc["name"]] = resp.json()
        return results

    def transform(self, raw: dict) -> list[dict]:
        rows = []
        ts = self.now_iso()
        for loc_name, payload in raw.items():
            current = payload.get("current", {})
            for metric, key in [
                ("pm2_5", "pm2_5"),
                ("pm10", "pm10"),
                ("us_aqi", "us_aqi"),
            ]:
                if key in current and current[key] is not None:
                    rows.append({
                        "source": self.source_name,
                        "timestamp": ts,
                        "metric": metric,
                        "value": float(current[key]),
                        "label": loc_name,
                        "metadata": {},
                    })
        return rows
