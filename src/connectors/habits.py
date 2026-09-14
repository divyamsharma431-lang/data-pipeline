"""
Personal habits connector -- GitHub public events API

No API key required for public data (rate-limited to 60 requests/hour
unauthenticated -- fine for a once-a-day pipeline, but keep the tracked
list small, e.g. 5 or fewer usernames). Tracks daily commit-related
activity for one or more configured GitHub usernames.
"""

import requests

from .base import BaseConnector


class HabitsConnector(BaseConnector):
    source_name = "habits"

    BASE_URL = "https://api.github.com/users/{username}/events/public"

    def __init__(self, usernames):
        if isinstance(usernames, str):
            usernames = [usernames]
        self.usernames = usernames

    def fetch(self) -> dict:
        results = {}
        for username in self.usernames:
            resp = requests.get(
                self.BASE_URL.format(username=username),
                headers={
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "data-pipeline-portfolio-project",
                },
                timeout=15,
            )
            resp.raise_for_status()
            results[username] = resp.json()
        return results

    def transform(self, raw: dict) -> list[dict]:
        ts = self.now_iso()
        rows = []

        for username, events in raw.items():
            push_count = sum(1 for e in events if e.get("type") == "PushEvent")
            pr_count = sum(1 for e in events if e.get("type") == "PullRequestEvent")
            issue_count = sum(1 for e in events if e.get("type") == "IssuesEvent")
            commit_count = sum(
                len(e.get("payload", {}).get("commits", []))
                for e in events
                if e.get("type") == "PushEvent"
            )

            rows.append({"source": self.source_name, "timestamp": ts, "metric": "pushes", "value": float(push_count), "label": username, "metadata": {}})
            rows.append({"source": self.source_name, "timestamp": ts, "metric": "commits", "value": float(commit_count), "label": username, "metadata": {}})
            rows.append({"source": self.source_name, "timestamp": ts, "metric": "pull_requests", "value": float(pr_count), "label": username, "metadata": {}})
            rows.append({"source": self.source_name, "timestamp": ts, "metric": "issues", "value": float(issue_count), "label": username, "metadata": {}})

        return rows
