"""Live source: Arbeitnow's free job board API. No key needed.

GET https://www.arbeitnow.com/api/job-board-api returns public JSON.

The REST pattern, every time:
  1. requests.get(url, timeout=...)  — always set a timeout
  2. raise_for_status()              — HTTP errors become exceptions
  3. .json()                         — parse the body
  4. map their field names onto our Job dataclass
  5. try/except everything — a dead API must not crash the app
"""
from __future__ import annotations

import requests

from ..models import Job
from .base import JobSource

API_URL = "https://www.arbeitnow.com/api/job-board-api"


class ArbeitnowSource(JobSource):
    name = "arbeitnow"

    def fetch(self, query: str = "", limit: int = 100) -> list[Job]:
        try:
            response = requests.get(API_URL, timeout=15)
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            print(f"[warn] arbeitnow API unreachable: {exc}")
            return []
        except ValueError as exc:
            print(f"[warn] arbeitnow returned bad JSON: {exc}")
            return []

        jobs: list[Job] = []
        for item in payload.get("data", []):
            try:
                jobs.append(self._to_job(item))
            except (KeyError, TypeError) as exc:
                print(f"[warn] skipping malformed arbeitnow job: {exc}")
        if query:
            q = query.lower()
            jobs = [
                j for j in jobs
                if q in j.title.lower() or q in j.company.lower()
                or any(q in s.lower() for s in j.skills)
            ]
        return jobs[:limit]

    @staticmethod
    def _to_job(item: dict) -> Job:
        """Translate one Arbeitnow JSON object into a Job."""
        slug = str(item.get("slug", "unknown"))
        tags = [str(t) for t in item.get("tags", []) if t]
        location = str(item.get("location", "") or "")
        if item.get("remote"):
            location = (location + " (Remote)").strip()
        return Job(
            id=f"arbeitnow-{slug}",
            title=str(item.get("title", "Untitled")),
            company=str(item.get("company_name", "Unknown")),
            location=location,
            url=str(item.get("url", "")),
            # Their tags ("python", "react") double as a skill list.
            skills=tags,
            source="arbeitnow",
        )
