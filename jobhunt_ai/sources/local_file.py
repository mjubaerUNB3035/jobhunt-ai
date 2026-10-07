"""Offline source: the curated NB postings + cached live results.

Reads data/jobs_nb.json and data/jobs_cache.json (the `fetch` command
writes fresh results there). The whole app runs with zero network.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..config import project_root
from ..models import Job
from .base import JobSource


class LocalFileSource(JobSource):
    name = "local"

    def __init__(self, data_dir: Path | None = None):
        # Tests point this at a temp dir, so the param stays.
        self.data_dir = data_dir or (project_root() / "data")

    def _load_file(self, path: Path) -> list[Job]:
        if not path.exists():
            return []
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            print(f"[warn] could not read {path.name}: {exc}")
            return []
        jobs = []
        for item in raw:
            try:
                jobs.append(Job.from_dict(item))
            except (TypeError, KeyError) as exc:
                print(f"[warn] skipping malformed job in {path.name}: {exc}")
        return jobs

    def fetch(self, query: str = "", limit: int = 100) -> list[Job]:
        jobs = self._load_file(self.data_dir / "jobs_nb.json")
        # Live results cached by `fetch` get appended, so one `match` sees all.
        jobs += self._load_file(self.data_dir / "jobs_cache.json")

        # De-dupe by id; first occurrence wins (seed beats cache).
        seen: set[str] = set()
        unique: list[Job] = []
        for job in jobs:
            if job.id not in seen:
                seen.add(job.id)
                unique.append(job)

        if query:
            q = query.lower()
            unique = [
                j for j in unique
                if q in j.title.lower() or q in j.company.lower()
                or any(q in s.lower() for s in j.skills)
            ]
        return unique[:limit]
