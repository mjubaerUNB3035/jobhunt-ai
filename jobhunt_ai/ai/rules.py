"""The offline AI — no network, no key, fully deterministic.

How scoring works:
  1. Normalize each required skill: lowercase, drop filler words,
     expand aliases ("k8s" -> "kubernetes").
  2. Tokenize the resume the same way.
  3. Each skill earns partial credit = skill tokens found / skill tokens.
     >= 50% counts as "matched".
  4. Score = 100 * total credit / number of skills.

Example: job wants [Python, Docker, Kubernetes], resume has Python + Docker
-> 1.0 + 1.0 + 0.0 -> 66.7.

Deliberately simple — "AI matching" as plain string math. Good enough to
be useful, transparent enough to learn from. Plug in an LLM when you want
nuance.
"""
from __future__ import annotations

import re

from ..models import Job, MatchResult
from .base import AIProvider

# Filler words with no skill meaning. Without these, "experience with"
# would match half the dictionary.
STOPWORDS = {
    "and", "or", "the", "with", "for", "in", "of", "to", "a", "an", "on",
    "including", "etc", "such", "as", "using", "use", "strong", "good",
    "excellent", "plus", "per", "via",
}

# Shorthand -> canonical form, so "CI/CD" and "cicd" count as the same skill.
ALIASES = {
    "js": "javascript",
    "ts": "typescript",
    "k8s": "kubernetes",
    "cicd": "cicd",
    "ci/cd": "cicd",
    "ci": "cicd",
    "cd": "cicd",
    "ml": "machinelearning",
    "ai": "artificialintelligence",
    "db": "database",
    "postgres": "postgresql",
    "gh": "github",
}


def _tokens(text: str) -> list[str]:
    """Normalize text into comparable tokens."""
    words = re.findall(r"[a-z0-9#+]+", text.lower())
    out = []
    for w in words:
        w = ALIASES.get(w, w)
        if w not in STOPWORDS and len(w) > 1:
            out.append(w)
    return out


def _skill_credit(skill: str, resume_tokens: set[str], resume_text: str) -> float:
    """What fraction of this skill's tokens show up in the resume (0.0-1.0)."""
    tokens = _tokens(skill)
    if not tokens:
        return 0.0
    # Cheap win: the literal phrase appears verbatim, e.g. "Spring Boot".
    if skill.lower() in resume_text:
        return 1.0
    hits = sum(1 for t in tokens if t in resume_tokens)
    return hits / len(tokens)


class RulesProvider(AIProvider):
    name = "rules"

    def score(self, job: Job, resume_text: str) -> MatchResult:
        resume_tokens = set(_tokens(resume_text))
        lowered = resume_text.lower()

        matched, missing = [], []
        credits = []
        for skill in job.skills:
            credit = _skill_credit(skill, resume_tokens, lowered)
            credits.append(credit)
            (matched if credit >= 0.5 else missing).append(skill)

        score = round(100 * sum(credits) / len(credits), 1) if credits else 0.0
        reasoning = (
            f"Rules-based match: {len(matched)} of {len(job.skills)} required "
            f"skills found in the resume (score {score}/100). "
            + (f"Strongest overlap: {', '.join(matched[:5])}. " if matched else "")
            + (f"Gaps to address: {', '.join(missing[:5])}." if missing else "No gaps found.")
        )
        return MatchResult(
            job=job, score=score,
            matched_skills=matched, missing_skills=missing,
            reasoning=reasoning,
        )

    def cover_letter(self, job: Job, resume_text: str) -> str:
        result = self.score(job, resume_text)
        # First line of resume.txt is the name — true for mine, keep in mind.
        name = resume_text.strip().splitlines()[0].strip()
        strengths = ", ".join(result.matched_skills[:6]) or "software development"
        gaps = ", ".join(result.missing_skills[:3])
        letter = f"""Dear Hiring Manager,

I am excited to apply for the {job.title} position at {job.company} ({job.location}). As a software developer with hands-on experience across backend systems, data pipelines, and cloud tooling, I believe I am a strong fit for this role.

My background aligns well with your requirements, including {strengths}. In my recent roles I have built REST APIs, automated data workflows with Python and SQL, and shipped containerized services with CI/CD practices — experience directly relevant to this position.
"""
        if gaps:
            letter += f"\nI am also actively expanding my skills in {gaps}, and I learn new stacks quickly on the job.\n"
        letter += f"""
Thank you for your consideration. I would welcome the opportunity to discuss how I can contribute to {job.company}.

Sincerely,
{name}
"""
        return letter
