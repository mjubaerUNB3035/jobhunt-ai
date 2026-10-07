"""Score everything, sort best-first, save.

rank() is the core loop: every job gets scored by the active provider,
results come back sorted. They land in data/matches.json so `top` and
`cover-letter` don't have to re-run the AI.
"""
from __future__ import annotations

import json
from pathlib import Path

from .ai.base import AIProvider
from .models import Job, MatchResult
from .sources.base import JobSource


def rank(jobs: list[Job], resume_text: str, provider: AIProvider) -> list[MatchResult]:
    """Score every job, best first. One bad job never kills the run."""
    results = []
    for i, job in enumerate(jobs, 1):
        print(f"  scoring {i}/{len(jobs)}: {job.title} @ {job.company} ...")
        try:
            results.append(provider.score(job, resume_text))
        except Exception as exc:
            print(f"  [warn] skipping {job.id}: {exc}")
    results.sort(key=lambda r: r.score, reverse=True)
    return results


def save_matches(results: list[MatchResult], path: Path) -> None:
    """Write ranked results to JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps([r.to_dict() for r in results], indent=2), encoding="utf-8"
    )
    print(f"saved {len(results)} matches -> {path}")


def load_matches(path: Path) -> list[MatchResult]:
    """Read back what save_matches wrote."""
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found — run `python -m jobhunt_ai.cli match` first."
        )
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [MatchResult.from_dict(item) for item in raw]


def fetch_jobs(source: JobSource, query: str, limit: int) -> list[Job]:
    """Tiny helper so the CLI's fetch stays readable."""
    return source.fetch(query=query, limit=limit)
