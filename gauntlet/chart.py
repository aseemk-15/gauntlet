"""Chart loading. Strips HTML authoring comments so agents never see fixture metadata."""
import re
from dataclasses import dataclass, field
from pathlib import Path

COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)


@dataclass
class Chart:
    path: str
    text: str  # comment-stripped — the ONLY text agents ever see
    sections: dict = field(default_factory=dict)  # header -> body

    @property
    def title(self) -> str:
        first = self.text.strip().splitlines()[0]
        return first.lstrip("# ").strip()

    def summary(self) -> str:
        lines = [self.title]
        for header, body in self.sections.items():
            n = len(body.strip().splitlines())
            lines.append(f"  {header}  ({n} lines)")
        return "\n".join(lines)

    def contains_verbatim(self, quote: str) -> bool:
        """Whitespace-tolerant verbatim check used by the judge's evidence test."""
        norm = re.sub(r"\s+", " ", quote).strip().lower()
        hay = re.sub(r"\s+", " ", self.text).lower()
        return norm in hay


def load_chart(path: str | Path) -> Chart:
    raw = Path(path).read_text()
    text = COMMENT_RE.sub("", raw)
    sections = {}
    current, buf = None, []
    for line in text.splitlines():
        if line.startswith("## "):
            if current:
                sections[current] = "\n".join(buf)
            current, buf = line[3:].strip(), []
        elif current:
            buf.append(line)
    if current:
        sections[current] = "\n".join(buf)
    return Chart(path=str(path), text=text, sections=sections)
