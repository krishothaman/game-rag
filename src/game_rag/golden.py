import json
from dataclasses import dataclass


@dataclass
class GoldenQuestion:
    id: int
    question: str
    facts: list
    pages: list
    not_covered: bool = False


def load_golden(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    return [GoldenQuestion(**json.loads(line)) for line in lines if line.strip()]


def pages_found(item, hits):
    titles = {h.chunk.page_title for h in hits}
    return [p for p in item.pages if p in titles]
