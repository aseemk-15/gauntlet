"""Anthropic client helpers: cached-prefix calls + strict-JSON extraction."""
import json
import re

import anthropic

from .config import api_key

_client = None


def client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=api_key(), max_retries=3)
    return _client


def cached_system(role_text: str, chart_text: str) -> list:
    """Identical system prefix across all attackers → one cache write, 29 cache reads."""
    return [
        {"type": "text", "text": role_text},
        {"type": "text", "text": chart_text, "cache_control": {"type": "ephemeral"}},
    ]


def extract_json(text: str):
    """Parse the first JSON object in a response; raises ValueError if none."""
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        raise ValueError(f"no JSON object in response: {text[:200]!r}")
    return json.loads(m.group(0))
