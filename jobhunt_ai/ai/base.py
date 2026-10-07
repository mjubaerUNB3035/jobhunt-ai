"""The contract every AI backend follows."""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import Job, MatchResult


class AIProvider(ABC):
    """Scores jobs against a resume and drafts cover letters."""

    name: str = "base"  # subclasses override; the CLI uses this

    @abstractmethod
    def score(self, job: Job, resume_text: str) -> MatchResult:
        """Rate the fit 0-100."""
        raise NotImplementedError

    @abstractmethod
    def cover_letter(self, job: Job, resume_text: str) -> str:
        """Draft a cover letter for this job."""
        raise NotImplementedError
