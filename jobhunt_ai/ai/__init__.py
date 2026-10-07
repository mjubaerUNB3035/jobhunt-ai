"""The swappable "brains".

Every provider does two things:
    score(job, resume_text)        -> MatchResult (0-100 fit)
    cover_letter(job, resume_text) -> str (a draft)

The CLI picks one by name, so going from the offline rules engine to a
real LLM is a one-word change (--ai ollama).

    rules   - offline keyword overlap. the default; no network, no key.
    ollama  - local LLM at localhost:11434.
    openai  - OpenAI's chat API. needs OPENAI_API_KEY.
"""
from .base import AIProvider
from .ollama import OllamaProvider
from .openai_provider import OpenAIProvider
from .rules import RulesProvider

__all__ = ["AIProvider", "OllamaProvider", "OpenAIProvider", "RulesProvider"]


def get_provider(name: str, settings) -> AIProvider:
    """Build the named provider from Settings."""
    name = name.lower()
    if name == "rules":
        return RulesProvider()
    if name == "ollama":
        return OllamaProvider(url=settings.ollama_url, model=settings.ollama_model)
    if name == "openai":
        return OpenAIProvider(api_key=settings.openai_api_key, model=settings.openai_model)
    raise ValueError(f"Unknown AI provider {name!r}; expected rules|ollama|openai.")
