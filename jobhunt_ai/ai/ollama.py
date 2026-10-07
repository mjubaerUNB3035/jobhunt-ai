"""Local LLM backend via Ollama's REST API. No cloud, no key.

One-time setup:
    1. Install Ollama: https://ollama.com/download
    2. ollama pull llama3.1
    3. It serves on http://localhost:11434 by default.

We POST a prompt to /api/generate asking for ONLY a JSON object, then
parse it into a MatchResult. If Ollama is down or the model rambles,
we return a MatchResult explaining the problem instead of crashing.

Same prompt -> JSON -> dataclass pattern as the OpenAI backend —
only the HTTP bits differ.
"""
from __future__ import annotations

import json
import re

import requests

from ..models import Job, MatchResult
from .base import AIProvider

SCORE_PROMPT = """You are a job-matching assistant. Score how well the candidate's resume fits the job posting.

JOB TITLE: {title}
COMPANY: {company}
REQUIRED SKILLS: {skills}

RESUME:
{resume}

Reply with ONLY a JSON object (no markdown, no commentary) with these keys:
- "score": number 0-100, higher means better fit
- "matched_skills": list of required skills clearly evidenced in the resume
- "missing_skills": list of required skills not evidenced in the resume
- "reasoning": one or two sentences explaining the score
"""

COVER_PROMPT = """You are a career assistant. Write a concise, professional cover letter (under 250 words) for the candidate below, applying to this job. Use only facts from the resume; do not invent experience. Plain text, no markdown headers.

JOB TITLE: {title}
COMPANY: {company}
LOCATION: {location}
REQUIRED SKILLS: {skills}

RESUME:
{resume}
"""


def _extract_json(text: str) -> dict:
    """Pull the JSON object out of model output.

    Models love wrapping things in ``` fences or adding chatter around
    the JSON, so we strip fences and grab the outermost braces.
    """
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object found in model output")
    return json.loads(cleaned[start:end + 1])


class OllamaProvider(AIProvider):
    name = "ollama"

    def __init__(self, url: str = "http://localhost:11434", model: str = "llama3.1"):
        self.url = url.rstrip("/")
        self.model = model

    def _generate(self, prompt: str) -> str:
        # First token can take a while on a cold model — be patient.
        response = requests.post(
            f"{self.url}/api/generate",
            json={"model": self.model, "prompt": prompt, "stream": False},
            timeout=120,
        )
        response.raise_for_status()
        return response.json().get("response", "")

    def _unavailable(self, job: Job, detail: str) -> MatchResult:
        return MatchResult(
            job=job, score=0.0, matched_skills=[], missing_skills=list(job.skills),
            reasoning=(
                "Ollama provider could not score this job: " + detail +
                " Fix: install Ollama (https://ollama.com/download), run "
                f"'ollama pull {self.model}', and make sure it serves at {self.url}."
            ),
        )

    def score(self, job: Job, resume_text: str) -> MatchResult:
        try:
            raw = self._generate(SCORE_PROMPT.format(
                title=job.title, company=job.company,
                skills=", ".join(job.skills), resume=resume_text[:4000],
            ))
            data = _extract_json(raw)
        except requests.RequestException as exc:
            return self._unavailable(job, f"{exc}.")
        except (ValueError, json.JSONDecodeError) as exc:
            return self._unavailable(job, f"could not parse model output ({exc}).")
        return MatchResult(
            job=job,
            score=float(max(0, min(100, data.get("score", 0)))),
            matched_skills=[str(s) for s in data.get("matched_skills", [])],
            missing_skills=[str(s) for s in data.get("missing_skills", [])],
            reasoning=str(data.get("reasoning", "")),
        )

    def cover_letter(self, job: Job, resume_text: str) -> str:
        try:
            return self._generate(COVER_PROMPT.format(
                title=job.title, company=job.company, location=job.location,
                skills=", ".join(job.skills), resume=resume_text[:4000],
            )).strip()
        except requests.RequestException as exc:
            return (f"[Ollama unavailable: {exc}. Start Ollama and pull "
                    f"'{self.model}' to generate cover letters locally.]")
