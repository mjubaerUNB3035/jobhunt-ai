"""Tests. Run:  python -m unittest discover -s tests -v

All offline — the rules provider needs no network, the local source reads
the seed JSON, and the model round-trips are pure Python.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jobhunt_ai.ai.rules import RulesProvider
from jobhunt_ai.matcher import rank
from jobhunt_ai.models import Job, MatchResult
from jobhunt_ai.sources.local_file import LocalFileSource

RESUME = """Jane Doe
Software Developer skilled in Python, Java, SQL, REST APIs, Git and Docker.
Built data pipelines on AWS with CI/CD via GitHub Actions.
"""

PYTHON_JOB = Job(
    id="test-01", title="Python Developer", company="Acme",
    location="Fredericton, NB", url="https://example.com/1",
    skills=["Python", "REST APIs", "Docker", "Kubernetes"], source="test",
)
JAVA_JOB = Job(
    id="test-02", title="Java Developer", company="Acme",
    location="Fredericton, NB", url="https://example.com/2",
    skills=["Java", "Spring Boot", "SQL"], source="test",
)


class TestRulesProvider(unittest.TestCase):
    def setUp(self):
        self.provider = RulesProvider()

    def test_full_match_scores_100(self):
        job = Job(id="t", title="T", company="C", location="L", url="u",
                  skills=["Python", "Git"])
        result = self.provider.score(job, RESUME)
        self.assertEqual(result.score, 100.0)
        self.assertEqual(set(result.matched_skills), {"Python", "Git"})
        self.assertEqual(result.missing_skills, [])

    def test_partial_match(self):
        result = self.provider.score(PYTHON_JOB, RESUME)
        self.assertGreater(result.score, 50)
        self.assertLess(result.score, 100)
        self.assertIn("Python", result.matched_skills)
        self.assertIn("Kubernetes", result.missing_skills)

    def test_no_match_scores_zero(self):
        job = Job(id="t", title="T", company="C", location="L", url="u",
                  skills=["COBOL", "Fortran"])
        result = self.provider.score(job, RESUME)
        self.assertEqual(result.score, 0.0)

    def test_aliases(self):
        # "CI/CD" should line up via the alias table.
        job = Job(id="t", title="T", company="C", location="L", url="u",
                  skills=["CI/CD"])
        result = self.provider.score(job, RESUME)
        self.assertEqual(result.score, 100.0)

    def test_cover_letter_mentions_job_and_skills(self):
        letter = self.provider.cover_letter(PYTHON_JOB, RESUME)
        self.assertIn("Python Developer", letter)
        self.assertIn("Acme", letter)
        self.assertIn("Python", letter)


class TestRank(unittest.TestCase):
    def test_rank_sorts_best_first(self):
        results = rank([PYTHON_JOB, JAVA_JOB], RESUME, RulesProvider())
        self.assertEqual(len(results), 2)
        self.assertGreaterEqual(results[0].score, results[1].score)


class TestLocalFileSource(unittest.TestCase):
    def test_seed_file_loads(self):
        jobs = LocalFileSource().fetch()
        # Seed file = the real NB postings; just sanity-check it's populated.
        self.assertGreaterEqual(len(jobs), 12)
        for job in jobs:
            self.assertTrue(job.id and job.title and job.company)

    def test_query_filters(self):
        jobs = LocalFileSource().fetch(query="python")
        self.assertGreater(len(jobs), 0)
        for job in jobs:
            blob = (job.title + job.company + " ".join(job.skills)).lower()
            self.assertIn("python", blob)

    def test_cache_file_is_picked_up(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            cached = Job(id="cache-1", title="Cached", company="C",
                         location="L", url="u", skills=["Go"], source="cache")
            (d / "jobs_cache.json").write_text(
                '[{"id": "cache-1", "title": "Cached", "company": "C", '
                '"location": "L", "url": "u", "skills": ["Go"], '
                '"source": "cache"}]', encoding="utf-8")
            jobs = LocalFileSource(data_dir=d).fetch()
            self.assertEqual([j.id for j in jobs], ["cache-1"])


class TestModelsRoundTrip(unittest.TestCase):
    def test_job_round_trip(self):
        job = Job.from_dict(PYTHON_JOB.to_dict())
        self.assertEqual(job, PYTHON_JOB)

    def test_match_result_round_trip(self):
        result = RulesProvider().score(PYTHON_JOB, RESUME)
        restored = MatchResult.from_dict(result.to_dict())
        self.assertEqual(restored.job, result.job)
        self.assertEqual(restored.score, result.score)
        self.assertEqual(restored.matched_skills, result.matched_skills)
        self.assertEqual(restored.missing_skills, result.missing_skills)
        self.assertEqual(restored.reasoning, result.reasoning)


if __name__ == "__main__":
    unittest.main()
