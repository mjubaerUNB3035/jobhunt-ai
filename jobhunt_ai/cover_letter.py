"""Cover letters — a thin wrapper so the CLI never cares *how*.

Template for rules, LLM for the rest. Same call either way.
"""
from __future__ import annotations

from pathlib import Path

from .ai.base import AIProvider
from .models import Job


def generate(job: Job, resume_text: str, provider: AIProvider) -> str:
    """Draft a cover letter for this job."""
    return provider.cover_letter(job, resume_text)


def save_letter(letter: str, path: Path) -> None:
    """Write it to disk (for `cover-letter --out file.txt`)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(letter, encoding="utf-8")
    print(f"saved cover letter -> {path}")
