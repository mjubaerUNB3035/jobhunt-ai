"""Settings — every knob in one place.

Everything comes from env vars (or a .env file, see .env.example).
No secrets hardcoded, ever. The rest of the code never touches
os.environ directly, which also makes this easy to test — just
build a Settings by hand.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


def project_root() -> Path:
    """Project root, resolved from this file — so the CLI works from anywhere."""
    return Path(__file__).resolve().parent.parent


@dataclass
class Settings:
    ai_provider: str = "rules"  # "rules" (offline default), "ollama", "openai"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    data_dir: Path = field(default_factory=lambda: project_root() / "data")

    @classmethod
    def load(cls) -> "Settings":
        """Build Settings from env (and .env if it exists)."""
        # load_dotenv is a no-op when there's no .env, so zero setup still works.
        load_dotenv(project_root() / ".env")
        provider = os.getenv("JOBHUNT_AI_PROVIDER", "rules").strip().lower()
        if provider not in {"rules", "ollama", "openai"}:
            raise ValueError(
                f"Unknown JOBHUNT_AI_PROVIDER={provider!r}; "
                "expected 'rules', 'ollama' or 'openai'."
            )
        return cls(
            ai_provider=provider,
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            ollama_url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
            ollama_model=os.getenv("OLLAMA_MODEL", "llama3.1"),
        )
