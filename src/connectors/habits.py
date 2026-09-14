"""
Personal habits connector -- GitHub public events API

No API key required for public data (rate-limited to 60 requests/hour
unshared -- fine for a once-a-day pipeline). Tracks daily commit-related
activity for a configured GitHub username. Swap in the Spotify API here
later if you'd rather track listening habits (that one does need OAuth).
"""

import requests

from .base import BaseConnector


class HabitsConnector(BaseConnector):
    source_name = "habits"

    BASE_URL = "https://api.github.com/users/{username}/events/public"

    def __init__(self, username: str):
        self.username = username

    def fetch(self) -> dict:
        resp = requests.get(
            self.BASE_URL.format(username=self.username),
            headers={
                "Accept": "application/vnd.github+json",
                # GitHub's API rejects requests with no User-Agent (403)
                "User-Agent": "data-pipeline-portfolio-project",
            },
            timeout=15,
        )
        resp.raise_for_status()
        return {"events": resp.json()}

    def transform(self, raw: dict) -> list[dict]:
        ts = self.now_iso()
        events = raw.get("events", [])

        push_count = sum(1 for e in events if e.get("type") == "PushEvent")
        pr_count = sum(1 for e in events if e.get("type") == "PullRequestEvent")
        issue_count = sum(1 for e in events if e.get("type") == "IssuesEvent")
        commit_count = sum(
            len(e.get("payload", {}).get("commits", []))
            for e in events
            if e.get("type") == "PushEvent"
        )

        return [
            {
                "source": self.source_name,
                "timestamp": ts,
                "metric": "pushes",
                "value": float(push_count),
                "label": self.username,
                "metadata": {},
            },
            {
                "source": self.source_name,
                "timestamp": ts,
                "metric": "commits",
                "value": float(commit_count),
                "label": self.username,
                "metadata": {},
            },
            {
                "source": self.source_name,
                "timestamp": ts,
                "metric": "pull_requests",
                "value": float(pr_count),
                "label": self.username,
                "metadata": {},
            },
            {
                "source": self.source_name,
                "timestamp": ts,
                "metric": "issues",
                "value": float(issue_count),
                "label": self.username,
                "metadata": {},
            },
        ]
