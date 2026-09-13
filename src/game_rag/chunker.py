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


def page_type(categories):
    for category, kind in PAGE_TYPES:
        if category in categories:
            return kind
    return "lore"


def chunk_page(page, size=config.CHUNK_WORDS, overlap=config.CHUNK_OVERLAP):
    # naive on purpose: glue all the sections together and cut every `size` words
    words, heading_of_word = [], []
    for section in page["sections"]:
        section_words = section["text"].split()
        words += section_words
        heading_of_word += [section["heading"]] * len(section_words)

    chunks = []
    start = 0
    kind = page_type(page["categories"])
    while start < len(words):
        chunks.append(Chunk(
            id=f"{file_stem(page['title'])}-{len(chunks)}",
            text=" ".join(words[start:start + size]),
            page_title=page["title"],
            section=heading_of_word[start],
            url=page["url"],
            page_type=kind,
        ))
        if start + size >= len(words):
            break
        # step back a bit so the next chunk repeats the last few words of this one
        start += size - overlap
    return chunks


def chunk_all(clean_dir):
    chunks = []
    for path in sorted(clean_dir.glob("*.json")):
        chunks += chunk_page(json.loads(path.read_text(encoding="utf-8")))
    return chunks
