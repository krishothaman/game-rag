# Level 1 — Naive RAG: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ask a Sekiro lore question in the terminal and get an answer written only from retrieved wiki chunks, with quoted evidence and a debug view of the 5 chunks that were found.

**Architecture:** Four new parts from the spec: the **Chunker** (clean pages → fixed-size word chunks with labels), the **Embedder** (text → 1024 numbers with `qwen3-embedding:0.6b` through Ollama), the **Library** (ChromaDB folder on disk, "nearest 5" search), and the **Answerer** (fenced prompt → `qwen3.5:4b` through Ollama, one reply, quote-first). New commands: `index`, `ask`, `chat`.

**Tech Stack:** Python 3.12 (uv), `ollama` (Python client, 0.6.x), `chromadb` (1.5.x), Ollama app with `qwen3.5:4b` and `qwen3-embedding:0.6b`. All free and open source.

**Spec:** `docs/superpowers/specs/2026-09-12-sekiro-lore-master-design.md` (sections 3, 4.3, 4.4, 4.5, 6 Level 1)

## Global Constraints

- **Zero cost (spec 1.1):** only free open-source packages and free open models. No API keys, no accounts, no paid services.
- **Who does what (owner's choice "I code, you drive"):** the agent writes code and runs the quick red/green test checks while coding. The **owner runs everything with real effects**: `uv add`, Ollama commands, `index`, `ask`, `chat`, and the full test suite at the end of each task. Steps marked **🎮 Owner** are theirs.
- **Git:** the agent stages files with `git add`; the owner commits and pushes. The agent never runs `git commit` or `git push`.
- **Code style:** must not look AI-generated. Few comments, short, casual, lowercase, only where something isn't obvious. No docstrings. No spec references in code.
- **Models:** chat `qwen3.5:4b` with thinking off (`think=False`); embeddings `qwen3-embedding:0.6b`. Questions are embedded with the instruction prefix `Instruct: ...\nQuery: `; documents are embedded as plain text (from the model card).
- **Closed-book fence (spec 3.2):** no tools, a fixed system prompt, one reply per question, quote-first answers, the exact fallback line `My library doesn't cover that.`
- **Naive chunking on purpose (spec 4.4 Level 1):** about 300 words with about 50 words of overlap, ignoring headings. Better chunking is Level 3.
- **Top 5 chunks per question (spec 4.5).** The relevance cut-off is Level 4, not now.
- **Privacy:** ChromaDB's anonymous usage reporting is turned off.
- Run every command from `C:\projects\RAGMODEL`.

## File Structure

```
src/game_rag/config.py      + models, chunk sizes, library folder, question prefix
src/game_rag/chunker.py     Chunk dataclass, page_type(), chunk_page(), chunk_all()
src/game_rag/embedder.py    Embedder: embed_documents() in batches, embed_query() with the prefix
src/game_rag/library.py     Hit dataclass, Library: rebuild(), search(), count()
src/game_rag/answerer.py    SYSTEM_PROMPT, build_prompt(), cited_numbers(), Answerer.answer()
src/game_rag/cli.py         + index / ask / chat commands, friendly Ollama errors
tests/test_chunker.py
tests/test_embedder.py
tests/test_library.py
tests/test_answerer.py
tests/test_rag_cli.py
data/library/               ChromaDB files (NOT committed, rebuild with `index`)
docs/level-1-notes.md       before-RAG vs after-RAG answers and observations
```

---

## Before Task 1 (🎮 Owner): Ollama and models

- [ ] Install Ollama from `ollama.com/download/windows` (or `winget install Ollama.Ollama`), then open a new terminal.
- [ ] Run `ollama --version`. Expected: a version number.
- [ ] Run `ollama pull qwen3.5:4b` (3.4 GB) and `ollama pull qwen3-embedding:0.6b` (639 MB).
- [ ] Run `ollama list`. Expected: both models listed.
- [ ] Run `ollama run qwen3.5:4b`, ask `In Sekiro, what is Dragonrot and how is it cured? Who is the Sculptor really?`, and save the answer. This is the **before-RAG** baseline for Task 6. Type `/bye` to exit.

---

### Task 1: Settings, packages, and the Chunker

*Why:* RAG searches small pieces, not whole pages. This task cuts every clean page into ~300-word chunks that overlap by ~50 words, and labels each chunk with where it came from.

**Files:**
- Modify: `src/game_rag/config.py` (append Level 1 settings), `.gitignore`, `pyproject.toml` + `uv.lock` (by `uv add`)
- Create: `src/game_rag/chunker.py`, `tests/test_chunker.py`

**Interfaces:**
- Consumes: `titles.file_stem`, clean page JSON dicts (`title`, `url`, `categories`, `sections: [{heading, level, text}]`).
- Produces:
  - `@dataclass Chunk(id: str, text: str, page_title: str, section: str, url: str, page_type: str, game: str = config.GAME)`
  - `page_type(categories: list[str]) -> str`: one of `ending`, `character`, `location`, `item`, `lore`
  - `chunk_page(page: dict, size=config.CHUNK_WORDS, overlap=config.CHUNK_OVERLAP) -> list[Chunk]`
  - `chunk_all(clean_dir: Path) -> list[Chunk]`
  - config: `GAME`, `CHAT_MODEL`, `EMBED_MODEL`, `QUERY_INSTRUCTION`, `CHUNK_WORDS`, `CHUNK_OVERLAP`, `TOP_K`, `LIBRARY_DIR`, `COLLECTION`

- [ ] **Step 1 (🎮 Owner): add the packages**

Run: `uv add ollama chromadb`
Expected: finishes without errors; `pyproject.toml` lists `ollama` and `chromadb`.

- [ ] **Step 2: append to `src/game_rag/config.py`**

```python

# level 1 rag settings
GAME = "Sekiro"
CHAT_MODEL = "qwen3.5:4b"
EMBED_MODEL = "qwen3-embedding:0.6b"
# qwen3-embedding wants questions to come with a little instruction in front, documents go in plain
QUERY_INSTRUCTION = "Instruct: Given a question about Sekiro lore, retrieve wiki passages that answer it\nQuery: "
CHUNK_WORDS = 300
CHUNK_OVERLAP = 50
TOP_K = 5
LIBRARY_DIR = PROJECT_ROOT / "data" / "library"
COLLECTION = "sekiro"
```

- [ ] **Step 3: append to `.gitignore`**

```gitignore

# chromadb files, rebuild with `uv run python -m game_rag index`
data/library/
```

- [ ] **Step 4: write the failing tests `tests/test_chunker.py`**

```python
import json

from game_rag.chunker import Chunk, chunk_all, chunk_page, page_type
from game_rag.titles import file_stem, page_url


def make_page(title, sections, categories=("Characters",)):
    return {
        "title": title,
        "url": page_url(title),
        "categories": list(categories),
        "sections": [{"heading": h, "level": 2, "text": t} for h, t in sections],
    }


def numbered(n, start=0):
    return " ".join(f"w{i}" for i in range(start, start + n))


def test_long_page_is_cut_into_overlapping_chunks():
    page = make_page("Owl", [("Description", numbered(24))])
    chunks = chunk_page(page, size=10, overlap=3)
    # starts at word 0, 7, 14. the third one already reaches the last word so it stops there
    assert [c.text for c in chunks] == [numbered(10, 0), numbered(10, 7), numbered(10, 14)]


def test_neighbouring_chunks_share_the_overlap():
    page = make_page("Owl", [("Description", numbered(24))])
    first, second = chunk_page(page, size=10, overlap=3)[:2]
    assert first.text.split()[-3:] == second.text.split()[:3]


def test_short_page_is_one_chunk():
    page = make_page("Dying Monk", [("Description", "A monk who is dying.")])
    assert [c.text for c in chunk_page(page, size=10, overlap=3)] == ["A monk who is dying."]


def test_chunk_remembers_the_section_it_starts_in():
    # description is words 0-4, location is 5-19. chunks start at 0, 7, 14
    page = make_page("Owl", [("Description", numbered(5)), ("Location", numbered(15, 5))])
    chunks = chunk_page(page, size=10, overlap=3)
    assert [c.section for c in chunks] == ["Description", "Location", "Location"]


def test_chunk_labels_and_ids():
    page = make_page("Emma/Dialogue", [("Introduction", numbered(12))], categories=["Dialogues"])
    chunks = chunk_page(page, size=10, overlap=3)
    assert chunks[0] == Chunk(
        id=f"{file_stem('Emma/Dialogue')}-0",
        text=numbered(10),
        page_title="Emma/Dialogue",
        section="Introduction",
        url=page_url("Emma/Dialogue"),
        page_type="character",
        game="Sekiro",
    )
    assert chunks[1].id == f"{file_stem('Emma/Dialogue')}-1"


def test_page_type_picks_the_most_specific_category():
    assert page_type(["Endings"]) == "ending"
    assert page_type(["Bosses", "Enemies", "Characters"]) == "character"
    assert page_type(["Key Items", "Items"]) == "item"
    assert page_type(["Locations"]) == "location"
    assert page_type(["Lore"]) == "lore"
    assert page_type(["Something Else"]) == "lore"


def test_chunk_all_reads_every_clean_page(tmp_path):
    for title in ["Owl", "Emma"]:
        page = make_page(title, [("Description", numbered(5))])
        (tmp_path / f"{file_stem(title)}.json").write_text(json.dumps(page), encoding="utf-8")
    chunks = chunk_all(tmp_path)
    assert sorted(c.page_title for c in chunks) == ["Emma", "Owl"]
```

- [ ] **Step 5: run the tests and check they fail**

Run: `uv run pytest tests/test_chunker.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'game_rag.chunker'`

- [ ] **Step 6: create `src/game_rag/chunker.py`**

```python
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
```

- [ ] **Step 7: run the tests and check they pass**

Run: `uv run pytest tests/test_chunker.py -q`
Expected: `7 passed`

- [ ] **Step 8 (🎮 Owner): run the full suite**

Run: `uv run pytest`
Expected: `48 passed`

- [ ] **Step 9: stage (agent), then commit (🎮 Owner)**

Agent runs: `git add pyproject.toml uv.lock .gitignore src/game_rag/config.py src/game_rag/chunker.py tests/test_chunker.py`
Owner runs: `git commit -m "chunker + level 1 settings"` and `git push`

---

### Task 2: Embedder

*Why:* turns text into points on the meaning map. Questions get a short instruction in front (the model was trained that way); wiki chunks go in as plain text. Chunks are sent in batches so indexing is fast.

**Files:**
- Create: `src/game_rag/embedder.py`, `tests/test_embedder.py`

**Interfaces:**
- Consumes: `config.EMBED_MODEL`, `config.QUERY_INSTRUCTION`; an Ollama client with `.embed(model=..., input=...)` returning an object with `.embeddings` (list of lists of floats).
- Produces:
  - `Embedder(client=None, model=config.EMBED_MODEL, batch_size=32)`
  - `Embedder.embed_documents(texts: list[str]) -> list[list[float]]`
  - `Embedder.embed_query(question: str) -> list[float]`

- [ ] **Step 1: write the failing tests `tests/test_embedder.py`**

```python
from types import SimpleNamespace

from game_rag import config
from game_rag.embedder import Embedder


# pretends to be ollama, the "embedding" is just [length of text, 1.0]
class FakeOllama:
    def __init__(self):
        self.calls = []

    def embed(self, model, input):
        self.calls.append((model, input))
        texts = input if isinstance(input, list) else [input]
        return SimpleNamespace(embeddings=[[float(len(t)), 1.0] for t in texts])


def test_documents_are_sent_in_batches():
    fake = FakeOllama()
    vectors = Embedder(client=fake, batch_size=32).embed_documents([f"text {i}" for i in range(70)])
    assert len(vectors) == 70
    assert [len(batch) for _, batch in fake.calls] == [32, 32, 6]


def test_documents_go_in_plain_with_the_embedding_model():
    fake = FakeOllama()
    Embedder(client=fake).embed_documents(["Dragonrot spreads."])
    assert fake.calls == [(config.EMBED_MODEL, ["Dragonrot spreads."])]


def test_questions_get_the_instruction_in_front():
    fake = FakeOllama()
    vector = Embedder(client=fake).embed_query("What is Dragonrot?")
    sent = config.QUERY_INSTRUCTION + "What is Dragonrot?"
    assert fake.calls == [(config.EMBED_MODEL, sent)]
    assert vector == [float(len(sent)), 1.0]
```

- [ ] **Step 2: run the tests and check they fail**

Run: `uv run pytest tests/test_embedder.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'game_rag.embedder'`

- [ ] **Step 3: create `src/game_rag/embedder.py`**

```python
import ollama

from game_rag import config


class Embedder:
    def __init__(self, client=None, model=config.EMBED_MODEL, batch_size=32):
        self.client = client if client is not None else ollama.Client()
        self.model = model
        self.batch_size = batch_size

    def embed_documents(self, texts):
        vectors = []
        # send a bunch at once, way faster than one by one
        for i in range(0, len(texts), self.batch_size):
            response = self.client.embed(model=self.model, input=texts[i:i + self.batch_size])
            vectors += [list(v) for v in response.embeddings]
        return vectors

    def embed_query(self, question):
        response = self.client.embed(model=self.model, input=config.QUERY_INSTRUCTION + question)
        return list(response.embeddings[0])
```

- [ ] **Step 4: run the tests and check they pass**

Run: `uv run pytest tests/test_embedder.py -q`
Expected: `3 passed`

- [ ] **Step 5 (🎮 Owner): run the full suite**

Run: `uv run pytest`
Expected: `51 passed`

- [ ] **Step 6: stage (agent), then commit (🎮 Owner)**

Agent runs: `git add src/game_rag/embedder.py tests/test_embedder.py`
Owner runs: `git commit -m "embedder with query prefix and batching"` and `git push`

---

### Task 3: Library (ChromaDB)

*Why:* stores every chunk with its vector and labels in a folder on disk, and answers "which 5 chunks are closest to this question?"

**Files:**
- Create: `src/game_rag/library.py`, `tests/test_library.py`

**Interfaces:**
- Consumes: `Chunk` (Task 1), an embedder with `embed_documents(texts)` and `embed_query(question)` (Task 2), `config.LIBRARY_DIR`, `config.COLLECTION`, `config.TOP_K`.
- Produces:
  - `@dataclass Hit(chunk: Chunk, distance: float)`, with `Hit.similarity` property = `1 - distance`
  - `Library(embedder, path=config.LIBRARY_DIR, name=config.COLLECTION)`
  - `Library.rebuild(chunks: list[Chunk], log=print) -> None`: replaces everything in the collection
  - `Library.search(question: str, k=config.TOP_K) -> list[Hit]`: closest first; `[]` if empty
  - `Library.count() -> int`

- [ ] **Step 1: write the failing tests `tests/test_library.py`**

```python
from game_rag.chunker import Chunk
from game_rag.library import Library

VOCAB = ["dragonrot", "owl", "emma", "sword"]


# fake embedder: counts how often each vocab word shows up, good enough to test search order
class FakeEmbedder:
    def vector(self, text):
        words = text.lower().replace("?", "").replace(".", "").split()
        return [words.count(v) + 0.01 for v in VOCAB]

    def embed_documents(self, texts):
        return [self.vector(t) for t in texts]

    def embed_query(self, question):
        return self.vector(question)


def chunk(i, text, title):
    return Chunk(id=f"c{i}", text=text, page_title=title, section="Overview",
                 url=f"https://example.com/{i}", page_type="lore")


CHUNKS = [
    chunk(0, "Dragonrot spreads when Wolf dies. Dragonrot makes people cough.", "Rot Essence"),
    chunk(1, "Owl is the foster father of Wolf. Owl is a great shinobi.", "Owl"),
    chunk(2, "Emma is a doctor who helps Wolf.", "Emma"),
]


def test_search_returns_closest_chunk_first(tmp_path):
    library = Library(FakeEmbedder(), path=tmp_path)
    library.rebuild(CHUNKS, log=lambda m: None)
    hits = library.search("what is dragonrot?", k=2)
    assert hits[0].chunk.page_title == "Rot Essence"
    assert len(hits) == 2


def test_labels_survive_the_round_trip(tmp_path):
    library = Library(FakeEmbedder(), path=tmp_path)
    library.rebuild(CHUNKS, log=lambda m: None)
    hit = library.search("owl", k=1)[0]
    assert hit.chunk == CHUNKS[1]
    assert 0.0 < hit.similarity <= 1.0


def test_rebuild_replaces_old_chunks(tmp_path):
    library = Library(FakeEmbedder(), path=tmp_path)
    library.rebuild(CHUNKS, log=lambda m: None)
    library.rebuild(CHUNKS[:1], log=lambda m: None)
    assert library.count() == 1


def test_empty_library_finds_nothing(tmp_path):
    library = Library(FakeEmbedder(), path=tmp_path)
    assert library.count() == 0
    assert library.search("anything") == []
```

- [ ] **Step 2: run the tests and check they fail**

Run: `uv run pytest tests/test_library.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'game_rag.library'`

- [ ] **Step 3: create `src/game_rag/library.py`**

```python
from dataclasses import asdict, dataclass

import chromadb
from chromadb.config import Settings

from game_rag import config
from game_rag.chunker import Chunk


@dataclass
class Hit:
    chunk: Chunk
    distance: float

    @property
    def similarity(self):
        # cosine distance is 0 for identical, so flip it to get "how similar"
        return 1 - self.distance


class Library:
    def __init__(self, embedder, path=config.LIBRARY_DIR, name=config.COLLECTION):
        self.embedder = embedder
        # anonymized_telemetry off so chroma doesnt phone home
        self.client = chromadb.PersistentClient(path=str(path), settings=Settings(anonymized_telemetry=False))
        self.collection = self.client.get_or_create_collection(
            name=name, metadata={"hnsw:space": "cosine"}, embedding_function=None,
        )

    def count(self):
        return self.collection.count()

    def rebuild(self, chunks, log=print):
        # wipe whatever was in there from last time
        old_ids = self.collection.get(include=[])["ids"]
        if old_ids:
            self.collection.delete(ids=old_ids)

        batch = 100
        for i in range(0, len(chunks), batch):
            part = chunks[i:i + batch]
            self.collection.add(
                ids=[c.id for c in part],
                documents=[c.text for c in part],
                embeddings=self.embedder.embed_documents([c.text for c in part]),
                metadatas=[{k: v for k, v in asdict(c).items() if k not in ("id", "text")} for c in part],
            )
            log(f"  embedded {min(i + batch, len(chunks))}/{len(chunks)} chunks")

    def search(self, question, k=config.TOP_K):
        total = self.count()
        if total == 0:
            return []
        result = self.collection.query(
            query_embeddings=[self.embedder.embed_query(question)],
            n_results=min(k, total),
            include=["documents", "metadatas", "distances"],
        )
        hits = []
        for chunk_id, text, meta, distance in zip(
            result["ids"][0], result["documents"][0], result["metadatas"][0], result["distances"][0]
        ):
            hits.append(Hit(chunk=Chunk(id=chunk_id, text=text, **meta), distance=distance))
        return hits
```

- [ ] **Step 4: run the tests and check they pass**

Run: `uv run pytest tests/test_library.py -q`
Expected: `4 passed`. If ChromaDB rejects `embedding_function=None`, remove that argument (we always pass our own embeddings, so its default embedder is never used) and re-run.

- [ ] **Step 5 (🎮 Owner): run the full suite**

Run: `uv run pytest`
Expected: `55 passed`

- [ ] **Step 6: stage (agent), then commit (🎮 Owner)**

Agent runs: `git add src/game_rag/library.py tests/test_library.py`
Owner runs: `git commit -m "chromadb library with search"` and `git push`

---

### Task 4: Answerer (the closed-book fence)

*Why:* hands the question and the 5 chunks to the chat model with strict rules (only use these excerpts, quote every sentence, say "My library doesn't cover that." otherwise), and gets exactly one reply back.

**Files:**
- Create: `src/game_rag/answerer.py`, `tests/test_answerer.py`

**Interfaces:**
- Consumes: `Hit` (Task 3), `config.CHAT_MODEL`; an Ollama client with `.chat(model=..., messages=..., think=..., options=...)` returning an object with `.message.content`.
- Produces:
  - `SYSTEM_PROMPT: str` and `NOT_COVERED = "My library doesn't cover that."`
  - `build_prompt(question: str, hits: list[Hit]) -> str`: numbered excerpts `[1]`..`[n]` then the question
  - `cited_numbers(answer: str, how_many: int) -> list[int]`: excerpt numbers the answer cites, sorted, only 1..how_many
  - `Answerer(client=None, model=config.CHAT_MODEL)` with `.answer(question: str, hits: list[Hit]) -> str`

- [ ] **Step 1: write the failing tests `tests/test_answerer.py`**

```python
from types import SimpleNamespace

from game_rag import config
from game_rag.answerer import NOT_COVERED, SYSTEM_PROMPT, Answerer, build_prompt, cited_numbers
from game_rag.chunker import Chunk
from game_rag.library import Hit


def hit(i, title, section, text):
    return Hit(chunk=Chunk(id=f"c{i}", text=text, page_title=title, section=section,
                           url=f"https://example.com/{i}", page_type="lore"), distance=0.2)


HITS = [
    hit(0, "Rot Essence", "Overview", "Dragonrot is the name of the illness that has gripped Ashina."),
    hit(1, "Emma", "Description", "Emma is a doctor serving a certain master."),
]


class FakeOllama:
    def __init__(self, reply):
        self.reply = reply
        self.calls = []

    def chat(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(message=SimpleNamespace(content=self.reply))


def test_prompt_numbers_the_excerpts_and_ends_with_the_question():
    prompt = build_prompt("What is Dragonrot?", HITS)
    assert "[1] (Rot Essence > Overview)\nDragonrot is the name of the illness that has gripped Ashina." in prompt
    assert "[2] (Emma > Description)\nEmma is a doctor serving a certain master." in prompt
    assert prompt.rstrip().endswith("Question: What is Dragonrot?")


def test_system_prompt_has_the_fence_rules():
    assert "ONLY" in SYSTEM_PROMPT
    assert NOT_COVERED in SYSTEM_PROMPT
    assert "quote" in SYSTEM_PROMPT.lower()


def test_answer_makes_one_call_with_thinking_off():
    fake = FakeOllama('Dragonrot is an illness: "the illness that has gripped Ashina" [1]\n')
    answer = Answerer(client=fake).answer("What is Dragonrot?", HITS)
    assert answer == 'Dragonrot is an illness: "the illness that has gripped Ashina" [1]'
    assert len(fake.calls) == 1
    call = fake.calls[0]
    assert call["model"] == config.CHAT_MODEL
    assert call["think"] is False
    assert call["messages"][0] == {"role": "system", "content": SYSTEM_PROMPT}
    assert call["messages"][1]["content"] == build_prompt("What is Dragonrot?", HITS)
    assert "tools" not in call


def test_cited_numbers_finds_valid_excerpt_numbers():
    assert cited_numbers('a "x" [2] b "y" [1] c "z" [2]', how_many=2) == [1, 2]
    assert cited_numbers('made up "q" [7]', how_many=5) == []
    assert cited_numbers(NOT_COVERED, how_many=5) == []
```

- [ ] **Step 2: run the tests and check they fail**

Run: `uv run pytest tests/test_answerer.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'game_rag.answerer'`

- [ ] **Step 3: create `src/game_rag/answerer.py`**

```python
import re

import ollama

from game_rag import config

NOT_COVERED = "My library doesn't cover that."

SYSTEM_PROMPT = f"""You answer questions about the lore of the game Sekiro: Shadows Die Twice.

Rules:
- Use ONLY the numbered wiki excerpts in the user's message. Do not use anything you already know about Sekiro.
- Every sentence of your answer must contain an exact quote from an excerpt, copied word for word in double quotes, followed by the excerpt number in brackets. Example: Wolf serves Kuro: "Wolf is a shinobi sworn to protect Kuro" [2]
- If the excerpts don't contain the answer, reply with exactly this and nothing else: {NOT_COVERED}
- Keep it short, a few sentences at most."""


def build_prompt(question, hits):
    parts = ["Wiki excerpts:\n"]
    for i, h in enumerate(hits, start=1):
        parts.append(f"[{i}] ({h.chunk.page_title} > {h.chunk.section})\n{h.chunk.text}\n")
    parts.append(f"Question: {question}")
    return "\n".join(parts)


def cited_numbers(answer, how_many):
    found = {int(n) for n in re.findall(r"\[(\d+)\]", answer)}
    return sorted(n for n in found if 1 <= n <= how_many)


class Answerer:
    def __init__(self, client=None, model=config.CHAT_MODEL):
        self.client = client if client is not None else ollama.Client()
        self.model = model

    def answer(self, question, hits):
        # one call, no tools, thinking off, temperature 0 so the same question gives the same answer
        response = self.client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_prompt(question, hits)},
            ],
            think=False,
            options={"temperature": 0},
        )
        return response.message.content.strip()
```

- [ ] **Step 4: run the tests and check they pass**

Run: `uv run pytest tests/test_answerer.py -q`
Expected: `4 passed`

- [ ] **Step 5 (🎮 Owner): run the full suite**

Run: `uv run pytest`
Expected: `59 passed`

- [ ] **Step 6: stage (agent), then commit (🎮 Owner)**

Agent runs: `git add src/game_rag/answerer.py tests/test_answerer.py`
Owner runs: `git commit -m "answerer with the closed-book fence"` and `git push`

---

### Task 5: `index`, `ask`, and `chat` commands

*Why:* ties the parts together so you can build the library once and then ask questions, with debug mode showing the evidence.

**Files:**
- Modify: `src/game_rag/cli.py`
- Create: `tests/test_rag_cli.py`

**Interfaces:**
- Consumes: `chunk_all` (Task 1), `Embedder` (Task 2), `Library`, `Hit` (Task 3), `Answerer`, `cited_numbers` (Task 4).
- Produces:
  - commands: `index`, `ask "<question>" [--debug]`, `chat [--debug]`
  - `cli.make_library() -> Library` and `cli.make_answerer() -> Answerer` (tests swap these out)
  - `cli.answer_question(question, library, answerer, debug=False) -> int`

- [ ] **Step 1: write the failing tests `tests/test_rag_cli.py`**

```python
from game_rag import cli
from game_rag.chunker import Chunk
from game_rag.library import Hit


def hit(i, title, section, text):
    return Hit(chunk=Chunk(id=f"c{i}", text=text, page_title=title, section=section,
                           url=f"https://example.com/{title}", page_type="lore"), distance=0.25)


class FakeLibrary:
    def __init__(self, hits):
        self.hits = hits

    def count(self):
        return len(self.hits)

    def search(self, question, k=5):
        return self.hits


class FakeAnswerer:
    def __init__(self, reply=None, error=None):
        self.reply, self.error = reply, error

    def answer(self, question, hits):
        if self.error:
            raise self.error
        return self.reply


HITS = [
    hit(0, "Rot Essence", "Overview", "Dragonrot is the name of the illness that has gripped Ashina."),
    hit(1, "Emma", "Description", "Emma is a doctor."),
]


def test_ask_prints_the_answer_and_only_the_cited_sources(capsys):
    answerer = FakeAnswerer('An illness: "the illness that has gripped Ashina" [1]')
    assert cli.answer_question("What is Dragonrot?", FakeLibrary(HITS), answerer) == 0
    out = capsys.readouterr().out
    assert 'An illness: "the illness that has gripped Ashina" [1]' in out
    assert "[1] Rot Essence > Overview  https://example.com/Rot Essence" in out
    assert "Emma" not in out


def test_debug_mode_shows_every_retrieved_chunk(capsys):
    answerer = FakeAnswerer('An illness: "the illness that has gripped Ashina" [1]')
    cli.answer_question("What is Dragonrot?", FakeLibrary(HITS), answerer, debug=True)
    out = capsys.readouterr().out
    assert "similarity 0.75" in out
    assert "Emma is a doctor." in out


def test_ask_with_empty_library_says_to_run_index(monkeypatch, capsys):
    monkeypatch.setattr(cli, "make_library", lambda: FakeLibrary([]))
    monkeypatch.setattr(cli, "make_answerer", lambda: FakeAnswerer("unused"))
    assert cli.main(["ask", "What is Dragonrot?"]) == 1
    assert "index" in capsys.readouterr().out


def test_ollama_not_running_gets_a_friendly_message(monkeypatch, capsys):
    monkeypatch.setattr(cli, "make_library", lambda: FakeLibrary(HITS))
    monkeypatch.setattr(cli, "make_answerer", lambda: FakeAnswerer(error=ConnectionError("nope")))
    assert cli.main(["ask", "What is Dragonrot?"]) == 1
    assert "Ollama" in capsys.readouterr().out
```

- [ ] **Step 2: run the tests and check they fail**

Run: `uv run pytest tests/test_rag_cli.py -q`
Expected: FAIL with `AttributeError: module 'game_rag.cli' has no attribute 'answer_question'`

- [ ] **Step 3: update `src/game_rag/cli.py`**

Add these imports at the top (keep the existing ones):

```python
import time

import ollama

from game_rag.answerer import Answerer, cited_numbers
from game_rag.chunker import chunk_all
from game_rag.embedder import Embedder
from game_rag.library import Library
```

In `main()`, add the new subcommands after the `show` parser:

```python
    commands.add_parser("index", help="chunk + embed the clean pages into the library")
    ask = commands.add_parser("ask", help="ask one question")
    ask.add_argument("question")
    ask.add_argument("--debug", action="store_true", help="show the chunks that were found")
    chat = commands.add_parser("chat", help="keep asking questions until you type exit")
    chat.add_argument("--debug", action="store_true", help="show the chunks that were found")
```

Replace the command dispatch at the end of `main()` with:

```python
    try:
        if args.command == "collect":
            return run_collect()
        if args.command == "clean":
            return run_clean()
        if args.command == "stats":
            return run_stats()
        if args.command == "index":
            return run_index()
        if args.command == "ask":
            return run_ask(args.question, args.debug)
        if args.command == "chat":
            return run_chat(args.debug)
        return run_show(args.title)
    except ConnectionError:
        print("Can't reach Ollama. Open the Ollama app (or run `ollama serve`) and try again.")
        return 1
    except ollama.ResponseError as e:
        print(f"Ollama said: {e.error}")
        if e.status_code == 404:
            print(f"Missing a model? Run: ollama pull {config.CHAT_MODEL}  and  ollama pull {config.EMBED_MODEL}")
        return 1
```

Add these functions below `run_show`:

```python
def make_library():
    return Library(Embedder())


def make_answerer():
    return Answerer()


def run_index():
    chunks = chunk_all(config.CLEAN_DIR)
    if not chunks:
        print("No clean pages. Run `uv run python -m game_rag clean` first.")
        return 1
    print(f"Cut {len(chunks)} chunks from the clean pages. Embedding them now...")
    started = time.time()
    make_library().rebuild(chunks)
    print(f"Library ready in {time.time() - started:.0f}s at {config.LIBRARY_DIR}")
    return 0


def run_ask(question, debug):
    library = make_library()
    if library.count() == 0:
        print("The library is empty. Run `uv run python -m game_rag index` first.")
        return 1
    return answer_question(question, library, make_answerer(), debug)


def run_chat(debug):
    library = make_library()
    if library.count() == 0:
        print("The library is empty. Run `uv run python -m game_rag index` first.")
        return 1
    answerer = make_answerer()
    print("Ask about Sekiro lore. Type exit to quit.\n")
    while True:
        try:
            question = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if question.lower() in ("", "exit", "quit"):
            return 0
        answer_question(question, library, answerer, debug)
        print()


def answer_question(question, library, answerer, debug=False):
    hits = library.search(question)
    if debug:
        print("--- chunks found ---")
        for i, h in enumerate(hits, start=1):
            print(f"[{i}] similarity {h.similarity:.2f}  {h.chunk.page_title} > {h.chunk.section}")
            print(f"    {h.chunk.text[:300]}{'...' if len(h.chunk.text) > 300 else ''}")
        print("--------------------\n")

    answer = answerer.answer(question, hits)
    print(answer)

    # only list the sources the answer actually pointed at
    cited = cited_numbers(answer, len(hits))
    if cited:
        print("\nSources:")
        for n in cited:
            c = hits[n - 1].chunk
            print(f"  [{n}] {c.page_title} > {c.section}  {c.url}")
    return 0
```

- [ ] **Step 4: run the tests and check they pass**

Run: `uv run pytest tests/test_rag_cli.py -q`
Expected: `4 passed`

- [ ] **Step 5 (🎮 Owner): run the full suite**

Run: `uv run pytest`
Expected: `63 passed`

- [ ] **Step 6: stage (agent), then commit (🎮 Owner)**

Agent runs: `git add src/game_rag/cli.py tests/test_rag_cli.py`
Owner runs: `git commit -m "index, ask and chat commands"` and `git push`

---

### Task 6 (🎮 Owner drives): build the library and ask real questions

*Why:* spec Level 1 "done when": *"What is Dragonrot?"* returns an answer with quoted evidence, and debug mode shows the 5 chunks.

**Files:**
- Create: `docs/level-1-notes.md`

- [ ] **Step 1 (🎮 Owner): make sure Ollama is running**

Run: `ollama list`
Expected: `qwen3.5:4b` and `qwen3-embedding:0.6b` listed. If it says it can't connect, open the Ollama app.

- [ ] **Step 2 (🎮 Owner): build the library**

Run: `uv run python -m game_rag index`
Expected: `Cut N chunks...` (N around 600–700), progress lines, then `Library ready in ...s`.

- [ ] **Step 3 (🎮 Owner): the Level 1 check**

Run: `uv run python -m game_rag ask "What is Dragonrot?" --debug`
Expected: 5 chunks with similarity scores, then an answer with `"quotes" [n]`, then `Sources:`. If Ollama complains about thinking, or the answer starts with thinking text, tell the agent: the `think=False` line in `answerer.py` needs adjusting for Qwen3.5.

- [ ] **Step 4 (🎮 Owner): ask the before-RAG question again**

Run: `uv run python -m game_rag ask "In Sekiro, what is Dragonrot and how is it cured? Who is the Sculptor really?" --debug`
Compare with the before-RAG answer you saved. What changed? What's still wrong?

- [ ] **Step 5 (🎮 Owner): try the chat and a trick question**

Run: `uv run python -m game_rag chat --debug`
Ask 4–5 of your own questions, including one about a character who isn't in Sekiro (for example `Who is Ranni?`). Type `exit` to quit.

- [ ] **Step 6: write `docs/level-1-notes.md` together**

The agent writes it from what you report, using this layout:

```markdown
# Level 1 notes

## Library
- Chunks: (number from `index`)
- Time to build: (seconds from `index`)

## Before RAG vs after RAG
- Question: In Sekiro, what is Dragonrot and how is it cured? Who is the Sculptor really?
- Before (qwen3.5:4b alone): (what it said, what was wrong)
- After (Level 1 RAG): (what it said, what changed)

## Questions I tried
| Question | Right chunks found? | Answer right? | Quoted properly? |
|---|---|---|---|

## What I noticed
1.
2.
3.

## Questions for Level 2
-
```

- [ ] **Step 7: stage (agent), then commit (🎮 Owner)**

Agent runs: `git add docs/level-1-notes.md`
Owner runs: `git commit -m "level 1 done: first working rag"` and `git push`

**Level 1 is done** when `ask "What is Dragonrot?" --debug` shows 5 chunks and an answer with quoted evidence, and the notes are written.
