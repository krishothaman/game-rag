import json
from dataclasses import dataclass

from game_rag import config
from game_rag.titles import file_stem

# first match wins, so the specific categories go before the generic ones
PAGE_TYPES = [
    ("Endings", "ending"),
    ("Characters", "character"), ("Bosses", "character"), ("Mini-Bosses", "character"),
    ("Dialogue", "character"), ("Dialogues", "character"),
    ("Locations", "location"),
    ("Key Items", "item"), ("Prosthetic Tools", "item"), ("Memories", "item"), ("Items", "item"),
    ("Lore", "lore"), ("Chapters", "lore"),
]


@dataclass
class Chunk:
    id: str
    text: str
    page_title: str
    section: str
    url: str
    page_type: str
    game: str = config.GAME

    @property
    def embed_text(self):
        return f"{self.page_title} > {self.section}\n{self.text}"


def page_type(categories):
    for category, kind in PAGE_TYPES:
        if category in categories:
            return kind
    return "lore"


def windows(words, size, overlap):
    start = 0
    while True:
        yield words[start:start + size]
        if start + size >= len(words):
            return
        start += size - overlap


def chunk_page(page, size=config.CHUNK_WORDS, overlap=config.CHUNK_OVERLAP):
    chunks = []
    kind = page_type(page["categories"])

    def add(words, heading):
        chunks.append(Chunk(
            id=f"{file_stem(page['title'])}-{len(chunks)}",
            text=" ".join(words),
            page_title=page["title"],
            section=heading,
            url=page["url"],
            page_type=kind,
        ))

    # pack whole sections into a chunk, only split a section when it's too big by itself
    packed, heading = [], None
    for section in page["sections"]:
        words = section["text"].split()
        if not words:
            continue
        if packed and len(packed) + len(words) > size:
            add(packed, heading)
            packed = []
        if len(words) > size:
            for part in windows(words, size, overlap):
                add(part, section["heading"])
            continue
        if not packed:
            heading = section["heading"]
        packed += words
    if packed:
        add(packed, heading)
    return chunks


def chunk_all(clean_dir):
    chunks = []
    for path in sorted(clean_dir.glob("*.json")):
        chunks += chunk_page(json.loads(path.read_text(encoding="utf-8")))
    return chunks
