"""
Central configuration. Edit this file to add cities, tickers, teams, or
change the GitHub username being tracked -- no other file needs to change.

To disable a source entirely, remove it from ENABLED_CONNECTORS.
"""

import os

DB_PATH = os.environ.get("PIPELINE_DB_PATH", "data/pipeline.db")

WEATHER_CITIES = [
    {"name": "London", "lat": 51.5074, "lon": -0.1278},
    {"name": "New York", "lat": 40.7128, "lon": -74.0060},
    {"name": "Delhi", "lat": 28.6139, "lon": 77.2090},
]

AIR_QUALITY_LOCATIONS = WEATHER_CITIES  # reuse the same cities by default

STOCK_TICKERS = ["AAPL", "MSFT", "BTC-USD"]

SPORTS_TEAMS = [
    # Find team IDs via https://www.thesportsdb.com/api/v1/json/3/searchteams.php?t=Arsenal
    {"name": "Arsenal", "team_id": "133604"},
    {"name": "Manchester United", "team_id": "133612"},
    {"name": "Liverpool", "team_id": "133602"},
    {"name": "Chelsea", "team_id": "133610"},
]

GITHUB_USERNAME = os.environ.get("GITHUB_HABITS_USERNAME", "sahil7879")

# Which connectors run on each pipeline execution. Comment one out to pause it.
ENABLED_CONNECTORS = [
    "weather",
    "stocks",
    "sports",
    "air_quality",
    "habits",
]
