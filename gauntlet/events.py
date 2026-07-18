"""Real event stream. The CLI trace and the mission-log web view both render this.

Every number shown anywhere (elapsed, cost) comes from here — measured, never simulated.
"""
import json
import threading
import time
from pathlib import Path

from .config import PRICES, ROOT


class Run:
    def __init__(self, tag: str):
        self.t0 = time.monotonic()
        stamp = time.strftime("%Y%m%d-%H%M%S")
        self.dir = ROOT / "runs" / f"{stamp}-{tag}"
        self.dir.mkdir(parents=True, exist_ok=True)
        self._f = open(self.dir / "events.jsonl", "a")
        self._lock = threading.Lock()
        self.cost = 0.0
        self.calls = 0

    @property
    def elapsed(self) -> float:
        return time.monotonic() - self.t0

    def emit(self, type_: str, quiet: bool = False, **data):
        evt = {"t": round(self.elapsed, 2), "type": type_, **data}
        with self._lock:
            self._f.write(json.dumps(evt) + "\n")
            self._f.flush()
            if not quiet:
                brief = {k: v for k, v in data.items() if isinstance(v, (str, int, float))}
                print(f"[{evt['t']:7.2f}s] {type_:<18} "
                      + " ".join(f"{k}={v}" for k, v in brief.items()), flush=True)

    def add_usage(self, model: str, usage) -> None:
        inp, out = PRICES[model]
        cost = (
            getattr(usage, "input_tokens", 0) * inp
            + (getattr(usage, "cache_creation_input_tokens", 0) or 0) * inp * 1.25
            + (getattr(usage, "cache_read_input_tokens", 0) or 0) * inp * 0.10
            + getattr(usage, "output_tokens", 0) * out
        ) / 1_000_000
        with self._lock:
            self.cost += cost
            self.calls += 1

    def meter(self) -> str:
        return f"{self.elapsed:.1f}s · ${self.cost:.2f} · {self.calls} calls"
