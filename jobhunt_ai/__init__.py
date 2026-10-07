"""Job Hunt AI Assistant.

Matches my resume against job postings and drafts cover letters.
The AI backend is swappable — start with the offline one, plug in
an LLM later.

Quick start (no API keys needed):
    pip install -r requirements.txt
    python -m jobhunt_ai.cli fetch --source local
    python -m jobhunt_ai.cli match
    python -m jobhunt_ai.cli top --n 5
"""

__version__ = "1.0.0"
