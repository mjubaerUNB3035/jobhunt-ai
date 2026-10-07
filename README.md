# Job Hunt AI Assistant

I built this to help with my own job hunt: it **pulls job postings from a
REST API**, **scores them against my resume** with a swappable AI backend,
and **drafts cover letters** — all from the command line. It runs with
**zero API keys**: the default AI is an offline rules engine, and you can
switch to a local LLM (Ollama) or OpenAI later without touching any other
code.

It's also my learning project for backend + AI work, so every module is
small and covers one idea — REST clients, abstract base classes,
dataclasses, config from env vars, and prompt → JSON → object AI
integration.

## What it does

```
python -m jobhunt_ai.cli fetch --source local      # load job postings
python -m jobhunt_ai.cli match                     # score them vs your resume
python -m jobhunt_ai.cli top --n 5                 # pretty table of best fits
python -m jobhunt_ai.cli cover-letter --index 0    # draft a cover letter
```

- **Sources** (`jobhunt_ai/sources/`): `local` reads the curated New Brunswick
  IT postings in `data/jobs_nb.json` (29 real postings); `arbeitnow` pulls live
  jobs from the free Arbeitnow REST API (no key needed).
- **AI backends** (`jobhunt_ai/ai/`): `rules` (offline keyword/skill-overlap
  scoring — the default), `ollama` (local LLM via REST), `openai` (OpenAI chat
  API via REST).
- **Output**: ranked matches saved to `data/matches.json`, cover letters
  printed or saved to a file.

## Opening in Visual Studio (not VS Code)

1. Open **Visual Studio Installer** → Modify → check the **"Python
   development"** workload → install.
2. In Visual Studio: **File → Open → Project/Solution** → select
   `jobhunt-ai.pyproj`. (Alternative: **File → Open → Folder** on the
   `jobhunt-ai` folder — the `.pyproj` just gives nicer project structure.)
3. Create a virtual environment: right-click **Python Environments** in
   Solution Explorer → **Add Environment…** → **Virtual Environment**.
4. With the venv active, open the **Developer PowerShell** (or Package
   Manager Console) and run:
   ```powershell
   pip install -r requirements.txt
   ```
5. Run a command: right-click `jobhunt_ai/cli.py` → **Start with Debugging**
   (or run `python -m jobhunt_ai.cli ...` from the terminal with the project
   root as working directory).

## Try it now (no keys, no setup beyond pip)

```bash
pip install -r requirements.txt

# 1. Load the 29 seeded NB postings
python -m jobhunt_ai.cli fetch --source local

# 2. Score them against data/resume.txt (offline rules AI)
python -m jobhunt_ai.cli match

# 3. See the best fits
python -m jobhunt_ai.cli top --n 5

# 4. Draft a cover letter for the #0 match, save it to a file
python -m jobhunt_ai.cli cover-letter --index 0 --out letter.txt

# 5. Try the LIVE source (needs internet, still no key)
python -m jobhunt_ai.cli fetch --source arbeitnow --query python --limit 20
python -m jobhunt_ai.cli match --source arbeitnow --query python --limit 20
python -m jobhunt_ai.cli top --n 5

# 6. Run the tests
python -m unittest discover -s tests -v
```

## Switching the AI backend

**Ollama (free, local, private):**
1. Install from https://ollama.com/download and pull a model: `ollama pull llama3.1`
2. Copy `.env.example` → `.env` and set `JOBHUNT_AI_PROVIDER=ollama`
3. `python -m jobhunt_ai.cli match --ai ollama`

**OpenAI (cloud, needs a key):**
1. Get a key at https://platform.openai.com/api-keys
2. Copy `.env.example` → `.env`, set `JOBHUNT_AI_PROVIDER=openai` and paste
   your key into `OPENAI_API_KEY` (`.env` is git-ignored — never commit it)
3. `python -m jobhunt_ai.cli match --ai openai`

You can also pass `--ai` per command to compare backends on the same jobs.

## Project tour

| File | Idea it teaches |
|---|---|
| `jobhunt_ai/models.py` | `@dataclass` data contracts (`Job`, `MatchResult`) + JSON round-trip |
| `jobhunt_ai/config.py` | One `Settings` dataclass; env vars via `python-dotenv`; no secrets in code |
| `jobhunt_ai/sources/base.py` | Abstract base class = the interface every source honors |
| `jobhunt_ai/sources/local_file.py` | Reading JSON files, filtering, de-duplication |
| `jobhunt_ai/sources/arbeitnow.py` | REST integration: `requests.get` + timeout + `raise_for_status` + field mapping + graceful errors |
| `jobhunt_ai/ai/base.py` | Second ABC: `score()` + `cover_letter()` contract |
| `jobhunt_ai/ai/rules.py` | Offline "AI": normalization, aliases, token overlap, weighted 0–100 score, template letters |
| `jobhunt_ai/ai/ollama.py` | Local LLM over REST; prompt → JSON → dataclass; graceful fallback when Ollama is down |
| `jobhunt_ai/ai/openai_provider.py` | Same JSON contract against OpenAI's chat API; Bearer auth; fail-fast on missing key |
| `jobhunt_ai/matcher.py` | Orchestration: rank, sort, save/load JSON |
| `jobhunt_ai/cover_letter.py` | Thin helper — the CLI never knows *how* a letter is written |
| `jobhunt_ai/cli.py` | `argparse` subcommands; `rich` tables |
| `tests/test_matcher.py` | `unittest` without network: scoring, source loading, model round-trips |

## Extending it (3 steps each)

**Add a new job source** (e.g. a Remotive or Adzuna API):
1. Create `jobhunt_ai/sources/remotive.py` with `class RemotiveSource(JobSource)`
   implementing `fetch(query, limit)` that returns `list[Job]`.
2. Export it in `jobhunt_ai/sources/__init__.py`.
3. Wire it into `cli.py`: add the name to the `--source` choices and `_source()`.

**Add a new AI provider** (e.g. Anthropic, Gemini):
1. Create `jobhunt_ai/ai/anthropic.py` with `class AnthropicProvider(AIProvider)`
   implementing `score()` and `cover_letter()`.
2. Export it and add it to `get_provider()` in `jobhunt_ai/ai/__init__.py`.
3. Add the name to the `--ai` choices in `cli.py`.

## Notes

- `data/resume.txt` and `data/jobs_nb.json` are seed data so it runs
  immediately. `data/jobs_cache.json` (live fetch cache) and
  `data/matches.json` (scoring results) are generated and git-ignored.
- `data/resume.txt` has my personal details in it — if you fork this,
  swap in your own resume or keep the repo private.
- Scores from `rules` are transparent keyword math, not magic. Great for
  learning how matching works; an LLM backend reasons more like a human
  would. Try both and compare.
