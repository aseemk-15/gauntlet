"""Env + model configuration. Reads .env (never committed) for the API key."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ATTACKER_MODEL = os.environ.get("GAUNTLET_ATTACKER_MODEL", "claude-haiku-4-5-20251001")
JUDGE_MODEL = os.environ.get("GAUNTLET_JUDGE_MODEL", "claude-opus-4-8")
ATTACKER_MAX_TOKENS = 1200
JUDGE_MAX_TOKENS = 4000

# $/MTok (input, output) for the real cost meter. Cached-read input billed at 0.1x.
PRICES = {
    "claude-haiku-4-5-20251001": (1.00, 5.00),
    "claude-opus-4-8": (5.00, 25.00),
}


def load_env() -> None:
    envfile = ROOT / ".env"
    if envfile.exists():
        for line in envfile.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())


def api_key() -> str:
    load_env()
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise SystemExit("ANTHROPIC_API_KEY not set (put it in .env)")
    return key
