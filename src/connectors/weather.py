"""
Weather connector -- Open-Meteo (https://open-meteo.com)

No API key required. Free for non-commercial use, no signup.
Pulls current temperature, humidity, and wind speed for each configured city.
"""

import requests

from .base import BaseConnector


class WeatherConnector(BaseConnector):
    source_name = "weather"

    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    def __init__(self, cities: list[dict]):
        """
        cities: list of {"name": str, "lat": float, "lon": float}
        """
        self.cities = cities

    def fetch(self) -> dict:
        results = {}
        for city in self.cities:
            resp = requests.get(
                self.BASE_URL,
                params={
                    "latitude": city["lat"],
                    "longitude": city["lon"],
                    "current": "temperature_2m,relative_humidity_2m,wind_speed_10m",
                },
                timeout=15,
            )
            resp.raise_for_status()
            results[city["name"]] = resp.json()
        return results

    def transform(self, raw: dict) -> list[dict]:
        rows = []
        ts = self.now_iso()
        for city_name, payload in raw.items():
            current = payload.get("current", {})
            for metric, key in [
                ("temperature", "temperature_2m"),
                ("humidity", "relative_humidity_2m"),
                ("wind_speed", "wind_speed_10m"),
            ]:
                if key in current:
                    rows.append({
                        "source": self.source_name,
                        "timestamp": ts,
                        "metric": metric,
                        "value": float(current[key]),
                        "label": city_name,
                        "metadata": {"units": payload.get("current_units", {}).get(key)},
                    })
        return rows
