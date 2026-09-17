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


def load_verdicts(path):
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_verdicts(path, verdicts):
    path.write_text(json.dumps(verdicts, ensure_ascii=False, indent=2), encoding="utf-8")


# same question + same answer text = same verdict, so we only ask when the answer changes
def verdict_key(item, answer):
    return f"{item.id}|{answer}"


def pages_found(item, hits):
    titles = {h.chunk.page_title for h in hits}
    return [p for p in item.pages if p in titles]
