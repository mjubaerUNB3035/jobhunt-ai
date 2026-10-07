"""Where postings come from.

Each source is a small class behind the JobSource interface
(sources/base.py). The CLI picks one by name (--source local ...),
so new sources never touch the matching or AI code.
"""
from .arbeitnow import ArbeitnowSource
from .base import JobSource
from .local_file import LocalFileSource

__all__ = ["ArbeitnowSource", "JobSource", "LocalFileSource"]
