"""The shapes everything else talks in.

Job = one posting from any source. MatchResult = how well it fits my resume.
Plain dataclasses with to_dict/from_dict so results can be saved as JSON
and reloaded without re-running the AI. New source or new AI backend?
Just produce these two shapes and you're done.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class Job:
    id: str                      # stable id, e.g. "nb-01"
    title: str                   # e.g. "Software Developer"
    company: str                 # e.g. "VeroSource"
    location: str                # e.g. "Fredericton, NB"
    url: str                     # link to the posting
    skills: list[str] = field(default_factory=list)
    source: str = ""             # "local", "arbeitnow", ...

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Job":
        # Ignore unknown keys so old saved files still load if fields change.
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class MatchResult:
    job: Job
    score: float                       # 0-100, higher = better fit
    matched_skills: list[str] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)
    reasoning: str = ""                # why, in plain words

    def to_dict(self) -> dict:
        return {
            "job": self.job.to_dict(),
            "score": self.score,
            "matched_skills": self.matched_skills,
            "missing_skills": self.missing_skills,
            "reasoning": self.reasoning,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MatchResult":
        return cls(
            job=Job.from_dict(data["job"]),
            score=float(data.get("score", 0.0)),
            matched_skills=list(data.get("matched_skills", [])),
            missing_skills=list(data.get("missing_skills", [])),
            reasoning=str(data.get("reasoning", "")),
        )
