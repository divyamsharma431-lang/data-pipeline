# Multi-source data pipeline

An automated pipeline that pulls data from five different public APIs on a
daily schedule, stores everything in one SQLite database, and serves it
through a Streamlit dashboard where you pick which source to view.

No API keys or signups required — every connector uses a free, open
endpoint (Open-Meteo, yfinance, TheSportsDB, GitHub's public events API).

## Data sources

| Source | Metric examples | Provider |
|---|---|---|
| Weather | temperature, humidity, wind speed | [Open-Meteo](https://open-meteo.com) |
| Stocks / crypto | last price, day high/low | [yfinance](https://github.com/ranaroussi/yfinance) |
| Sports | recent score margins | [TheSportsDB](https://www.thesportsdb.com) |
| Air quality | PM2.5, PM10, US AQI | [Open-Meteo Air Quality](https://open-meteo.com/en/docs/air-quality-api) |
| GitHub habits | commits, pushes, PRs, issues | [GitHub public events API](https://docs.github.com/en/rest/activity/events) |

## Architecture

```
GitHub Actions (daily cron)
        │
        ▼
 Ingestion layer  ──▶  one connector class per source (plugin pattern)
        │
        ▼
 SQLite database  ──▶  single "readings" table, rows tagged by source
        │
        ▼
 Streamlit dashboard  ──▶  sidebar dropdown selects which source to view
```

Every connector implements the same interface (`fetch()` + `transform()`
from `src/connectors/base.py`), so adding a sixth data source means writing
one new file — nothing else in the pipeline changes.

## Project structure

```
data-pipeline/
├── .github/workflows/daily_fetch.yml   # scheduled ingestion via GitHub Actions
├── src/
│   ├── connectors/                     # one file per data source
│   ├── ingest.py                       # loops over connectors, writes to db
│   ├── db.py                           # SQLite schema + insert/query helpers
│   └── config.py                       # cities, tickers, teams, GitHub username
├── dashboard/app.py                    # Streamlit UI with source selector
├── tests/test_connectors.py            # unit tests, mocked API responses
├── data/pipeline.db                    # created on first run
└── requirements.txt
```

## Setup

```bash
git clone <your-repo-url>
cd data-pipeline
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Running it

Fetch data once:
```bash
python -m src.ingest
```

Launch the dashboard:
```bash
streamlit run dashboard/app.py
```

Run the tests:
```bash
pytest tests/ -v
```

## Automating it

The included GitHub Actions workflow (`.github/workflows/daily_fetch.yml`)
runs `src/ingest.py` every day at 08:00 UTC and commits the updated
database back to the repo. Enable it by pushing this repo to GitHub —
no secrets or configuration needed since none of the APIs require keys.
Trigger a manual run any time from the Actions tab.

To deploy the dashboard so it's publicly viewable, push to GitHub and
connect the repo on [Streamlit Community Cloud](https://streamlit.io/cloud)
(free), pointing at `dashboard/app.py`.

## Customizing

Edit `src/config.py` to change:
- which cities/tickers/teams are tracked
- which GitHub username's activity is pulled
- which connectors are enabled (comment one out in `ENABLED_CONNECTORS`
  to pause it without deleting code)

## Design notes

- **Long-format schema**: one `readings` table with `source`, `metric`,
  `value` columns rather than a separate table per source. This is the
  same tidy-data pattern used in real analytics systems, and it's what
  lets the dashboard filter with a single query regardless of source.
- **Idempotent inserts**: a unique constraint on `(source, timestamp,
  metric, label)` means re-running ingestion never creates duplicate rows.
- **Partial failure tolerance**: if one API is down, the others still run
  and get written to the database — the pipeline only reports failure if
  every source fails.
