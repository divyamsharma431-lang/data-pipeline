"""
Unit tests. These test transform() logic against mocked API responses,
so they run instantly and don't depend on any network access -- important
since CI shouldn't fail because a free API had a bad day.
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import db  # noqa: E402
from src.connectors.air_quality import AirQualityConnector  # noqa: E402
from src.connectors.habits import HabitsConnector  # noqa: E402
from src.connectors.sports import SportsConnector  # noqa: E402
from src.connectors.weather import WeatherConnector  # noqa: E402


def test_weather_transform_produces_expected_rows():
    connector = WeatherConnector(cities=[{"name": "TestCity", "lat": 0, "lon": 0}])
    raw = {
        "TestCity": {
            "current": {
                "temperature_2m": 21.5,
                "relative_humidity_2m": 60,
                "wind_speed_10m": 12.3,
            },
            "current_units": {"temperature_2m": "°C"},
        }
    }
    rows = connector.transform(raw)

    assert len(rows) == 3
    metrics = {r["metric"] for r in rows}
    assert metrics == {"temperature", "humidity", "wind_speed"}
    assert all(r["source"] == "weather" for r in rows)
    assert all(r["label"] == "TestCity" for r in rows)


def test_weather_transform_skips_missing_metrics():
    connector = WeatherConnector(cities=[{"name": "TestCity", "lat": 0, "lon": 0}])
    raw = {"TestCity": {"current": {"temperature_2m": 21.5}, "current_units": {}}}
    rows = connector.transform(raw)

    assert len(rows) == 1
    assert rows[0]["metric"] == "temperature"


def test_air_quality_transform():
    connector = AirQualityConnector(locations=[{"name": "TestCity", "lat": 0, "lon": 0}])
    raw = {"TestCity": {"current": {"pm2_5": 8.1, "pm10": 15.4, "us_aqi": 32}}}
    rows = connector.transform(raw)

    assert len(rows) == 3
    values = {r["metric"]: r["value"] for r in rows}
    assert values["us_aqi"] == 32.0


def test_habits_transform_counts_event_types():
    connector = HabitsConnector(username="testuser")
    raw = {
        "events": [
            {"type": "PushEvent", "payload": {"commits": [{}, {}]}},
            {"type": "PushEvent", "payload": {"commits": [{}]}},
            {"type": "PullRequestEvent", "payload": {}},
            {"type": "IssuesEvent", "payload": {}},
            {"type": "WatchEvent", "payload": {}},  # should be ignored
        ]
    }
    rows = connector.transform(raw)
    values = {r["metric"]: r["value"] for r in rows}

    assert values["pushes"] == 2.0
    assert values["commits"] == 3.0
    assert values["pull_requests"] == 1.0
    assert values["issues"] == 1.0


def test_sports_fetch_returns_events_for_each_team():
    teams = [
        {"name": "Arsenal", "team_id": "133604"},
        {"name": "Manchester United", "team_id": "133612"},
        {"name": "Liverpool", "team_id": "133602"},
        {"name": "Chelsea", "team_id": "133610"},
    ]
    responses = [
        {"results": [{"intHomeScore": "2", "intAwayScore": "1"}]},
        {"results": [{"intHomeScore": "0", "intAwayScore": "1"}]},
        {"results": [{"intHomeScore": "0", "intAwayScore": "0"}]},
        {"results": [{"intHomeScore": "2", "intAwayScore": "2"}]},
    ]
    mock_responses = []
    for payload in responses:
        response = MagicMock()
        response.json.return_value = payload
        response.raise_for_status.return_value = None
        mock_responses.append(response)

    with patch("src.connectors.sports.requests.get", side_effect=mock_responses):
        raw = SportsConnector(teams).fetch()

    assert set(raw) == {team["name"] for team in teams}
    assert len(SportsConnector(teams).transform(raw)) == 4


def test_weather_fetch_calls_api_with_expected_params():
    connector = WeatherConnector(cities=[{"name": "TestCity", "lat": 1.23, "lon": 4.56}])
    mock_response = MagicMock()
    mock_response.json.return_value = {"current": {}}
    mock_response.raise_for_status.return_value = None

    with patch("src.connectors.weather.requests.get", return_value=mock_response) as mock_get:
        connector.fetch()
        _, kwargs = mock_get.call_args
        assert kwargs["params"]["latitude"] == 1.23
        assert kwargs["params"]["longitude"] == 4.56


def test_db_insert_and_query_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "test.db")
        db.init_db(db_path)

        rows = [
            {
                "source": "weather",
                "timestamp": "2026-01-01T00:00:00+00:00",
                "metric": "temperature",
                "value": 20.0,
                "label": "TestCity",
                "metadata": {},
            }
        ]
        inserted = db.insert_rows(db_path, rows)
        assert inserted == 1

        # Re-inserting the same row should be ignored (unique constraint)
        inserted_again = db.insert_rows(db_path, rows)
        assert inserted_again == 0

        results = db.query_source(db_path, "weather")
        assert len(results) == 1
        assert results[0]["value"] == 20.0

        assert db.distinct_sources(db_path) == ["weather"]


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
