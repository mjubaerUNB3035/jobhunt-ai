"""OpenAI backend — same JSON contract as Ollama, different HTTP.

Setup:
    1. Get a key at https://platform.openai.com/api-keys
    2. Copy .env.example to .env and set OPENAI_API_KEY there.
       .gitignore already excludes .env — never commit the real key.

No key -> loud error up front, not a cryptic 401 later.
"""
from __future__ import annotations

import requests

from ..models import Job, MatchResult
from .base import AIProvider
from .ollama import COVER_PROMPT, SCORE_PROMPT, _extract_json

API_URL = "https://api.openai.com/v1/chat/completions"


class OpenAIProvider(AIProvider):
    name = "openai"

    def __init__(self, api_key: str = "", model: str = "gpt-4o-mini"):
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY is not set. Copy .env.example to .env and "
                "paste your key there (or use --ai rules / --ai ollama, "
                "which need no key)."
            )
        self.api_key = api_key
        self.model = model

    def _chat(self, prompt: str) -> str:
        # Bearer token = how the API knows it's you. HTTPS only, never logged.
        response = requests.post(
            API_URL,
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system",
                     "content": "You are a precise job-matching assistant. "
                                "Always reply with only the requested output."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,  # low = steadier scores run to run
            },
            timeout=60,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    def score(self, job: Job, resume_text: str) -> MatchResult:
        raw = self._chat(SCORE_PROMPT.format(
            title=job.title, company=job.company,
            skills=", ".join(job.skills), resume=resume_text[:4000],
        ))
        data = _extract_json(raw)  # loud error if the model rambles instead
        return MatchResult(
            job=job,
            score=float(max(0, min(100, data.get("score", 0)))),
            matched_skills=[str(s) for s in data.get("matched_skills", [])],
            missing_skills=[str(s) for s in data.get("missing_skills", [])],
            reasoning=str(data.get("reasoning", "")),
        )

    def cover_letter(self, job: Job, resume_text: str) -> str:
        return self._chat(COVER_PROMPT.format(
            title=job.title, company=job.company, location=job.location,
            skills=", ".join(job.skills), resume=resume_text[:4000],
        )).strip()
