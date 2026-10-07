"""The JobSource interface.

Anything that produces jobs — local file, REST API, scraper — subclasses
this and implements fetch(). The rest of the app only talks to the
interface, so adding a source is a ~30 line file, not a rewrite.
(The fancy name for this is the Strategy pattern.)
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import Job


class JobSource(ABC):
    """Anything that can produce a list of Job objects."""

    name: str = "base"  # subclasses override; the CLI uses this

    @abstractmethod
    def fetch(self, query: str = "", limit: int = 100) -> list[Job]:
        """Up to `limit` jobs, optionally filtered by `query`.

        `query` matches against title, company and skills. Empty = everything.
        Never blow up on network/format trouble — warn and return whatever
        you salvaged (possibly []).
        """
        raise NotImplementedError
