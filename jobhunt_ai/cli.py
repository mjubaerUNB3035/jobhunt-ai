"""The command line. Run from the project root:

    python -m jobhunt_ai.cli fetch --source local
    python -m jobhunt_ai.cli match --ai rules
    python -m jobhunt_ai.cli top --n 5
    python -m jobhunt_ai.cli cover-letter --index 0 --out letter.txt

fetch:        pull jobs (caches live results to data/jobs_cache.json)
match:        score them vs data/resume.txt -> data/matches.json
top:          pretty table of the best matches
cover-letter: draft a letter for one ranked job
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

from . import cover_letter as cover_letter_mod
from .ai import get_provider
from .config import Settings, project_root
from .matcher import fetch_jobs, load_matches, rank, save_matches
from .sources import ArbeitnowSource, LocalFileSource

console = Console()


def _source(name: str, settings: Settings):
    if name == "local":
        return LocalFileSource(settings.data_dir)
    if name == "arbeitnow":
        return ArbeitnowSource()
    raise ValueError(f"unknown source {name!r}; expected local|arbeitnow.")


def _provider(name: str | None, settings: Settings):
    # Explicit --ai wins; otherwise fall back to JOBHUNT_AI_PROVIDER from .env.
    return get_provider(name or settings.ai_provider, settings)


def cmd_fetch(args, settings: Settings) -> int:
    source = _source(args.source, settings)
    jobs = fetch_jobs(source, query=args.query or "", limit=args.limit)
    print(f"fetched {len(jobs)} jobs from '{args.source}'")
    for job in jobs[:10]:
        print(f"  - {job.title} @ {job.company} ({job.location})")
    if len(jobs) > 10:
        print(f"  ... and {len(jobs) - 10} more")
    # Stash live results so `match --source local` sees them too.
    if args.source != "local" and jobs:
        cache = settings.data_dir / "jobs_cache.json"
        cache.write_text(
            json.dumps([j.to_dict() for j in jobs], indent=2), encoding="utf-8"
        )
        print(f"cached -> {cache}")
    return 0


def cmd_match(args, settings: Settings) -> int:
    source = _source(args.source, settings)
    jobs = fetch_jobs(source, query=args.query or "", limit=args.limit)
    if not jobs:
        print("no jobs found — try `fetch` first or a different --query.")
        return 1
    resume_path = settings.data_dir / "resume.txt"
    if not resume_path.exists():
        print(f"resume not found at {resume_path}")
        return 1
    resume_text = resume_path.read_text(encoding="utf-8")
    try:
        provider = _provider(args.ai, settings)
    except ValueError as exc:
        print(f"error: {exc}")
        return 1
    print(f"scoring {len(jobs)} jobs with AI provider '{provider.name}' ...")
    try:
        results = rank(jobs, resume_text, provider)
    except Exception as exc:
        print(f"error while scoring: {exc}")
        return 1
    save_matches(results, settings.data_dir / "matches.json")
    best = results[0]
    print(f"best match: {best.job.title} @ {best.job.company} — {best.score}/100")
    return 0


def cmd_top(args, settings: Settings) -> int:
    try:
        results = load_matches(settings.data_dir / "matches.json")
    except FileNotFoundError as exc:
        print(exc)
        return 1
    table = Table(title=f"Top {args.n} job matches")
    table.add_column("#", justify="right")
    table.add_column("Score", justify="right")
    table.add_column("Title")
    table.add_column("Company")
    table.add_column("Location")
    table.add_column("Matched skills")
    for i, r in enumerate(results[: args.n]):
        table.add_row(
            str(i),
            f"{r.score:.1f}",
            r.job.title,
            r.job.company,
            r.job.location,
            ", ".join(r.matched_skills[:4]) or "—",
        )
    console.print(table)
    print("Use `cover-letter --index N` to draft a letter for one of these.")
    return 0


def cmd_cover_letter(args, settings: Settings) -> int:
    try:
        results = load_matches(settings.data_dir / "matches.json")
    except FileNotFoundError as exc:
        print(exc)
        return 1
    if not 0 <= args.index < len(results):
        print(f"--index must be between 0 and {len(results) - 1}")
        return 1
    resume_text = (settings.data_dir / "resume.txt").read_text(encoding="utf-8")
    try:
        provider = _provider(args.ai, settings)
    except ValueError as exc:
        print(f"error: {exc}")
        return 1
    result = results[args.index]
    print(f"drafting cover letter for: {result.job.title} @ {result.job.company}\n")
    letter = cover_letter_mod.generate(result.job, resume_text, provider)
    print(letter)
    if args.out:
        cover_letter_mod.save_letter(letter, Path(args.out))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m jobhunt_ai.cli",
        description="Job Hunt AI Assistant — match your resume to job postings.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    f = sub.add_parser("fetch", help="pull jobs from a source")
    f.add_argument("--source", choices=["local", "arbeitnow"], default="local")
    f.add_argument("--query", default="", help="filter text, e.g. 'python'")
    f.add_argument("--limit", type=int, default=100)
    f.set_defaults(func=cmd_fetch)

    m = sub.add_parser("match", help="score jobs against your resume")
    m.add_argument("--source", choices=["local", "arbeitnow"], default="local")
    m.add_argument("--ai", choices=["rules", "ollama", "openai"], default=None,
                   help="AI backend (default: JOBHUNT_AI_PROVIDER from .env)")
    m.add_argument("--query", default="")
    m.add_argument("--limit", type=int, default=100)
    m.set_defaults(func=cmd_match)

    t = sub.add_parser("top", help="show best matches in a table")
    t.add_argument("--n", type=int, default=5)
    t.set_defaults(func=cmd_top)

    c = sub.add_parser("cover-letter", help="draft a cover letter")
    c.add_argument("--index", type=int, required=True,
                   help="row number from the `top` table")
    c.add_argument("--ai", choices=["rules", "ollama", "openai"], default=None)
    c.add_argument("--out", default="", help="optional file to save the letter")
    c.set_defaults(func=cmd_cover_letter)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        settings = Settings.load()
    except ValueError as exc:
        print(f"configuration error: {exc}")
        return 1
    # Also works if you run cli.py directly instead of as -m.
    sys.path.insert(0, str(project_root()))
    return args.func(args, settings)


if __name__ == "__main__":
    raise SystemExit(main())
